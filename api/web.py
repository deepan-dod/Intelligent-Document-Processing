import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, abort, current_app
from flask_login import login_required, current_user
from database.models import (db, Document, DocumentPage, Investigation, DocumentField,
                             Evidence, Entity, OcrLine, Decision, Feedback, AuditLog,
                             ModelVersion, ModelPrediction)
from auth.permissions import require, can
from review import workflow
from copilot.query_engine import search

web = Blueprint("web", __name__)

@web.app_context_processor
def ctx(): return dict(can=can)

@web.route("/")
@require("read")
def dashboard(): return render_template("dashboard.html")

@web.route("/login")
def login(): return redirect(url_for("auth.login", next=request.args.get("next", "")))

@web.route("/documents")
@require("read")
def documents():
    q = request.args.get("q")
    type_filter = request.args.get("type")
    status_filter = request.args.get("status")
    query = Document.query
    if type_filter:
        query = query.filter_by(doc_type=type_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)
    if q:
        docs = search(q)
    else:
        docs = query.order_by(Document.id.desc()).all()
    # Distinct types for filter tabs
    types = [r[0] for r in db.session.query(Document.doc_type).distinct() if r[0]]
    return render_template("documents.html", docs=docs, q=q or "", current_type=type_filter, current_status=status_filter, types=types)

@web.route("/documents/<int:i>")
@require("read")
def document(i):
    d = db.get_or_404(Document, i)
    pages = DocumentPage.query.filter_by(doc_id=i).order_by(DocumentPage.number).all()
    lines = OcrLine.query.filter_by(doc_id=i).order_by(OcrLine.page, OcrLine.id).all()
    audit_history = AuditLog.query.filter_by(doc_id=i).order_by(AuditLog.id.desc()).limit(20).all()
    return render_template("document.html", d=d, fields=DocumentField.query.filter_by(doc_id=i).all(),
                           evidence=Evidence.query.filter_by(doc_id=i).all(), inv=Investigation.query.filter_by(doc_id=i).first(),
                           pages=pages, lines=lines, audit_history=audit_history, low=0.75)

@web.route("/documents/<int:i>/file")
@require("read")
def document_file(i):
    d = db.get_or_404(Document, i)
    if not d.stored_path or not os.path.exists(d.stored_path):
        flash("Original document file not found on disk")
        return redirect(url_for("web.document", i=i))
    as_attachment = request.args.get("download") == "1"
    return send_file(d.stored_path, mimetype=d.mime or "application/octet-stream", as_attachment=as_attachment, download_name=d.filename)

@web.route("/documents/<int:i>/pages/<int:num>")
@require("read")
def document_page(i, num):
    p = DocumentPage.query.filter_by(doc_id=i, number=num).first_or_404()
    if not p.processed_path or not os.path.exists(p.processed_path):
        abort(404)
    return send_file(p.processed_path, mimetype="image/png")

@web.route("/documents/<int:i>/reprocess", methods=["POST"])
@require("upload")
def reprocess_document(i):
    import pipeline
    d = db.get_or_404(Document, i)
    try:
        pipeline.process_document(d.id)
        flash(f"{d.filename} reprocessed successfully")
    except Exception as e:
        flash(f"Error reprocessing document: {e}")
    return redirect(url_for("web.document", i=i))

@web.route("/investigations")
@require("read")
def investigations():
    prio_filter = request.args.get("priority")
    status_filter = request.args.get("status")
    q = Investigation.query
    if prio_filter: q = q.filter_by(priority=prio_filter)
    if status_filter: q = q.filter_by(status=status_filter)
    items = q.order_by(Investigation.score.desc()).all()
    return render_template("investigations.html", items=items, current_priority=prio_filter, current_status=status_filter)

@web.route("/investigations/<int:i>", methods=["GET", "POST"])
@require("read")
def investigation(i):
    inv = db.get_or_404(Investigation, i)
    if request.method == "POST":
        if not can("decide"): return "forbidden", 403
        action = request.form.get("action")
        task = request.form.get("task")
        if task:
            # Human feedback form for AI retraining
            ai_pred = request.form.get("ai_prediction", "")
            h_label = request.form.get("human_label", "")
            r = request.form.get("reason", "")
            if ai_pred and h_label:
                workflow.add_feedback(inv, current_user.username, task, ai_pred, h_label, r)
                flash("AI feedback recorded successfully for model improvement.")
            return redirect(url_for("web.investigation", i=i))
        try:
            workflow.decide(inv, current_user.username, action, request.form.get("reason", ""),
                            request.form.get("field_id", type=int), request.form.get("value"))
            flash(f"Decision recorded: {action.replace('_', ' ').title()}")
        except ValueError as e:
            flash(str(e))
        return redirect(url_for("web.investigation", i=i))

    if can("decide"): workflow.open_case(inv, current_user.username)
    d = inv.doc
    evidence_list = Evidence.query.filter_by(doc_id=d.id).all()
    decisions = Decision.query.filter_by(investigation_id=inv.id).order_by(Decision.created_at.desc()).all()
    feedbacks = Feedback.query.filter_by(investigation_id=inv.id).order_by(Feedback.created_at.desc()).all()
    pages = DocumentPage.query.filter_by(doc_id=d.id).order_by(DocumentPage.number).all()
    return render_template("investigation.html", inv=inv, d=d,
                           fields=DocumentField.query.filter_by(doc_id=d.id).all(),
                           evidence={e.id: e for e in evidence_list}, evidence_list=evidence_list,
                           low=0.75, lines=OcrLine.query.filter_by(doc_id=d.id).all(),
                           decisions=decisions, feedbacks=feedbacks, pages=pages)

@web.route("/entities")
@require("read")
def entities(): return render_template("entities.html", items=Entity.query.all())

@web.route("/copilot")
@require("read")
def copilot(): return render_template("copilot.html")

@web.route("/audit")
@require("read")
def audit_view():
    from audit import audit_log as audit_engine
    intact, first_bad = audit_engine.verify_chain()
    q = AuditLog.query
    doc_filter = request.args.get("doc_id", type=int)
    action_filter = request.args.get("action")
    user_filter = request.args.get("user")
    if doc_filter: q = q.filter_by(doc_id=doc_filter)
    if action_filter: q = q.filter_by(action=action_filter)
    if user_filter: q = q.filter_by(user=user_filter)
    logs = q.order_by(AuditLog.id.desc()).limit(200).all()
    return render_template("audit.html", logs=logs, intact=intact, first_bad=first_bad,
                           doc_filter=doc_filter, action_filter=action_filter, user_filter=user_filter)

@web.route("/models", methods=["GET", "POST"])
@require("read")
def models_view():
    from ml import training
    if request.method == "POST":
        if not can("manage"):
            flash("Admin permission required to retrain models")
            return redirect(url_for("web.models_view"))
        mv = training.train_classifier(current_app.config["MODEL_DIR"])
        flash(f"Document classifier retrained! Version: {mv.version} — Accuracy: {mv.metrics.get('accuracy', 0):.1%}")
        return redirect(url_for("web.models_view"))
    models = ModelVersion.query.order_by(ModelVersion.id.desc()).all()
    monitoring = training.monitoring()
    feedbacks = Feedback.query.order_by(Feedback.id.desc()).limit(50).all()
    predictions = ModelPrediction.query.order_by(ModelPrediction.id.desc()).limit(20).all()
    return render_template("models.html", models=models, monitoring=monitoring, feedbacks=feedbacks, predictions=predictions)

@web.route("/demo-data", methods=["POST"])
@require("upload")
def demo_data():
    from documents.samples import load_demo
    try:
        msg = load_demo()
        flash("Demo scenario loaded successfully: 5 documents processed across purchase orders, deliveries, invoices, contracts & certificates.")
    except Exception as e:
        flash(f"Error loading demo data: {e}")
    return redirect(url_for("web.dashboard"))

@web.route("/upload", methods=["GET", "POST"])
@require("upload")
def upload():
    if request.method == "POST":
        from documents.upload import save_upload, UploadError
        import pipeline
        files = request.files.getlist("files")
        if not files or all(not f.filename for f in files):
            flash("No files selected for upload")
            return redirect(url_for("web.upload"))
        count = 0
        for f in files:
            if not f.filename: continue
            try:
                d = save_upload(f, current_user.username)
                pipeline.process_document(d.id)
                d = db.session.get(Document, d.id)
                flash(f"'{f.filename}': {d.status} ({d.doc_type})")
                count += 1
            except UploadError as e:
                flash(f"'{f.filename}': {e}")
        if count > 0:
            return redirect(url_for("web.documents"))
    return render_template("upload.html")
