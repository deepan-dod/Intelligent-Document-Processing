import os
from flask import Blueprint, jsonify, request, current_app, Response, send_file
from flask_login import current_user
from database.models import (db, Document, DocumentPage, DocumentField, DocumentEntity, Entity, Relationship, Evidence, Investigation,
                             ModelVersion, AuditLog, OcrLine, User)
from auth.permissions import require
from audit import audit_log as audit
from documents.upload import save_upload, UploadError
from review import workflow
from copilot.assistant import answer
from copilot.query_engine import search
from relationships.evidence_graph import build_graph
from investigation.decision_engine import explain
from reports import export
from ml import training
import pipeline

api = Blueprint("api", __name__, url_prefix="/api")

def doc_dict(d):
    return dict(id=d.id, code=d.code, filename=d.filename, type=d.doc_type, type_confidence=d.type_confidence, status=d.status,
                quality=d.quality, uploader=d.uploader, uploaded_at=d.uploaded_at.isoformat(), pages=d.page_count, ocr_engine=d.ocr_engine,
                needs_type_review=d.needs_type_review, error=d.error)

def inv_dict(i):
    return dict(id=i.id, code=i.code, document=f"DOC-{i.doc_id}", doc_id=i.doc_id, priority=i.priority, score=i.score, status=i.status,
                assignee=i.assignee, factors=i.factors, escalated=i.escalated, created_at=i.created_at.isoformat(),
                reasons=[dict(text=r.text, evidence_id=r.evidence_id, points=r.points) for r in i.reasons])

def _doc(i): return db.get_or_404(Document, i)

@api.post("/documents/upload")
@require("upload")
def upload():
    files = request.files.getlist("files") or request.files.getlist("file")
    if not files: return jsonify(error="no files supplied (field 'files')"), 400
    out, errors = [], []
    for f in files:
        try:
            d = save_upload(f, current_user.username)
            pipeline.process_document(d.id)
            d = db.session.get(Document, d.id)
            item = doc_dict(d)
            if d.quality and d.quality["overall"] < current_app.config["MIN_QUALITY"]:
                item["warning"] = "Low document quality — OCR results may be unreliable; consider re-uploading a clearer scan."
            inv = Investigation.query.filter_by(doc_id=d.id).first()
            item["investigation"] = inv_dict(inv) if inv else None
            out.append(item)
        except UploadError as e:
            errors.append(str(e))
    return jsonify(documents=out, errors=errors), (201 if out else 400)

@api.get("/documents")
@require("read")
def documents():
    q = Document.query
    if request.args.get("type"): q = q.filter_by(doc_type=request.args["type"])
    if request.args.get("status"): q = q.filter_by(status=request.args["status"])
    if request.args.get("q"):
        return jsonify([doc_dict(d) for d in search(request.args["q"])])
    return jsonify([doc_dict(d) for d in q.order_by(Document.id.desc()).limit(500)])

@api.get("/documents/<int:i>")
@require("read")
def document(i):
    d = _doc(i); return jsonify({**doc_dict(d), "meta": d.meta, "text_lines": OcrLine.query.filter_by(doc_id=i).count()})

@api.get("/documents/<int:i>/file")
@require("read")
def doc_file(i):
    d = _doc(i)
    if not d.stored_path or not os.path.exists(d.stored_path):
        return jsonify(error="file not found"), 404
    as_attachment = request.args.get("download") == "1"
    return send_file(d.stored_path, mimetype=d.mime or "application/octet-stream", as_attachment=as_attachment, download_name=d.filename)

@api.get("/documents/<int:i>/pages/<int:num>")
@require("read")
def doc_page_img(i, num):
    d = _doc(i)
    p = DocumentPage.query.filter_by(doc_id=i, number=num).first()
    if not p or not p.processed_path or not os.path.exists(p.processed_path):
        return jsonify(error="page not found"), 404
    return send_file(p.processed_path, mimetype="image/png")

@api.get("/documents/<int:i>/fields")
@require("read")
def fields(i):
    _doc(i)
    return jsonify([dict(id=f.id, name=f.name, value=f.value, confidence=f.confidence, low_confidence=f.confidence < current_app.config["LOW_CONF"],
                         page=f.page, bbox=f.bbox, corrected=f.corrected) for f in DocumentField.query.filter_by(doc_id=i)])

@api.get("/documents/<int:i>/entities")
@require("read")
def doc_entities(i):
    _doc(i)
    return jsonify([dict(mention=e.mention, type=e.etype, role=e.role, entity_id=e.entity_id, match_score=e.match_score, confidence=e.confidence)
                    for e in DocumentEntity.query.filter_by(doc_id=i)])

def _rel(r): return dict(id=r.id, source=f"{r.src_type}:{r.src_id}", relationship=r.rel, target=f"{r.dst_type}:{r.dst_id}", confidence=r.confidence, note=r.note)

@api.get("/documents/<int:i>/relationships")
@require("read")
def doc_relationships(i):
    _doc(i)
    rs = Relationship.query.filter(((Relationship.src_type == "document") & (Relationship.src_id == i)) | ((Relationship.dst_type == "document") & (Relationship.dst_id == i))).all()
    return jsonify(relationships=[_rel(r) for r in rs], graph=build_graph(center=i))

@api.get("/documents/<int:i>/evidence")
@require("read")
def doc_evidence(i):
    _doc(i)
    return jsonify([dict(id=e.id, kind=e.kind, title=e.title, detail=e.detail, score=e.score, related_doc_id=e.related_doc_id, field=e.field_name)
                    for e in Evidence.query.filter(Evidence.doc_id == i)])

@api.get("/documents/<int:i>/investigation")
@require("read")
def doc_investigation(i):
    _doc(i); inv = Investigation.query.filter_by(doc_id=i).first()
    return jsonify(inv_dict(inv) if inv else None)

@api.get("/documents/<int:i>/risk")
@require("read")
def doc_risk(i):
    _doc(i); r = explain(i)
    return jsonify(r or dict(priority="Low", score=0, factors=[], reasons=[]))

@api.get("/documents/<int:i>/audit")
@require("read")
def doc_audit(i):
    _doc(i); return jsonify([audit.to_dict(a) for a in audit.history(doc_id=i)])

@api.get("/entities")
@require("read")
def entities():
    return jsonify([dict(id=e.id, code=e.code, canonical_name=e.canonical_name, type=e.etype, aliases=[a.alias for a in e.aliases]) for e in Entity.query.all()])

@api.get("/relationships")
@require("read")
def relationships():
    return jsonify([_rel(r) for r in Relationship.query.limit(1000)])

@api.get("/investigations")
@require("read")
def investigations():
    q = Investigation.query
    for k in ("status", "priority"):
        if request.args.get(k): q = q.filter_by(**{k: request.args[k]})
    return jsonify([inv_dict(i) for i in q.order_by(Investigation.score.desc())])

@api.post("/investigations/<int:i>/decision")
@require("decide")
def decision(i):
    inv = db.get_or_404(Investigation, i); b = request.get_json(silent=True) or {}
    if b.get("action") == "correct" and current_user.role not in ("admin", "investigator"):
        return jsonify(error="forbidden: only investigators may correct data"), 403
    try:
        workflow.decide(inv, current_user.username, b.get("action", ""), b.get("reason", ""), b.get("field_id"), b.get("value"))
    except ValueError as e:
        return jsonify(error=str(e)), 400
    return jsonify(inv_dict(db.session.get(Investigation, i)))

@api.post("/investigations/<int:i>/feedback")
@require("decide")
def feedback(i):
    inv = db.get_or_404(Investigation, i); b = request.get_json(silent=True) or {}
    if not all(b.get(k) for k in ("task", "ai_prediction", "human_label")):
        return jsonify(error="task, ai_prediction and human_label are required"), 400
    fb = workflow.add_feedback(inv, current_user.username, b["task"], b["ai_prediction"], b["human_label"], b.get("reason", ""))
    return jsonify(id=fb.id), 201

@api.get("/models")
@require("read")
def models():
    return jsonify(models=[dict(id=m.id, name=m.name, version=m.version, active=m.active, created_at=m.created_at.isoformat()) for m in ModelVersion.query],
                   monitoring=training.monitoring())

@api.get("/models/<int:i>/metrics")
@require("read")
def model_metrics(i):
    return jsonify(db.get_or_404(ModelVersion, i).metrics)

@api.post("/models/train")
@require("manage")
def train():
    mv = training.train_classifier(current_app.config["MODEL_DIR"]); return jsonify(id=mv.id, version=mv.version, metrics=mv.metrics), 201

@api.post("/copilot")
@require("read")
def copilot():
    q = (request.get_json(silent=True) or {}).get("question", "")
    if not q.strip(): return jsonify(error="question required"), 400
    return jsonify(answer(q, current_app.config["ANTHROPIC_MODEL"]))

@api.get("/search")
@require("read")
def search_api():
    return jsonify([doc_dict(d) for d in search(request.args.get("q", ""))])

@api.get("/audit/verify")
@require("read")
def verify():
    ok, bad = audit.verify_chain(); return jsonify(intact=ok, first_bad_record=bad)

@api.get("/dashboard")
@require("read")
def dashboard():
    from sqlalchemy import func
    by = lambda col, m=Document: dict(db.session.query(col, func.count()).group_by(col).all())
    kinds = dict(db.session.query(Evidence.kind, func.count()).group_by(Evidence.kind).all())
    confs = [f.confidence for f in DocumentField.query]
    bins = [0] * 5
    for c in confs: bins[min(4, int(c * 5))] += 1
    open_s = ("New", "Under Review", "Awaiting Information")
    return jsonify(documents=Document.query.count(), open_investigations=Investigation.query.filter(Investigation.status.in_(open_s)).count(),
        high_priority=Investigation.query.filter(Investigation.priority.in_(["High", "Critical"]), Investigation.status.in_(open_s)).count(),
        conflicts=kinds.get("conflict", 0), duplicates=kinds.get("duplicate", 0), anomalies=kinds.get("anomaly", 0), integrity=kinds.get("integrity", 0),
        low_ocr=DocumentField.query.filter(DocumentField.confidence < current_app.config["LOW_CONF"]).count(),
        resolved=Investigation.query.filter(Investigation.status.in_(["Resolved", "Dismissed", "Confirmed Issue"])).count(),
        by_type=by(Document.doc_type), by_priority=dict(db.session.query(Investigation.priority, func.count()).group_by(Investigation.priority).all()),
        by_evidence_kind=kinds, confidence_hist=bins, monitoring=training.monitoring())

@api.get("/reports/<kind>/<int:i>.<fmt>")
@require("read")
def report(kind, i, fmt):
    inv = db.get_or_404(Investigation, i)
    if kind not in ("investigation", "evidence", "audit") or fmt not in ("csv", "xlsx", "pdf"):
        return jsonify(error="kind: investigation|evidence|audit; fmt: csv|xlsx|pdf"), 400
    r = export.rows(export.investigation_data(inv), kind)
    mime = {"csv": "text/csv", "pdf": "application/pdf", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}[fmt]
    body = {"csv": lambda: export.to_csv(r), "xlsx": lambda: export.to_xlsx(r), "pdf": lambda: export.to_pdf(r, f"{kind.title()} Report {inv.code}")}[fmt]()
    audit.log(f"report_{kind}_exported", user=current_user.username, doc_id=inv.doc_id, investigation_id=inv.id, new=fmt, source="human")
    return Response(body, mimetype=mime, headers={"Content-Disposition": f"attachment; filename={kind}_{inv.code}.{fmt}"})

@api.post("/users")
@require("manage")
def create_user_api():
    from auth.security import create_user
    from auth.permissions import ROLES
    b = request.get_json(silent=True) or {}
    if b.get("role") not in ROLES or not b.get("username") or len(b.get("password", "")) < 8:
        return jsonify(error="username, role and password (8+ chars) required"), 400
    if User.query.filter_by(username=b["username"]).first(): return jsonify(error="exists"), 409
    u = create_user(b["username"], b["password"], b["role"])
    audit.log("user_created", user=current_user.username, new=f"{u.username}:{u.role}", source="human")
    return jsonify(id=u.id), 201
