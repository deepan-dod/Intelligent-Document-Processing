from database.models import db, Investigation, Decision, DocumentField, Feedback, Evidence
from audit import audit_log as audit
import pipeline

ACTIONS = {"approve": "Resolved", "reject": "Confirmed Issue", "dismiss": "Dismissed",
           "request_info": "Awaiting Information", "escalate": "Under Review", "correct": "Under Review"}
FEEDBACK_TASK = {"duplicate": "duplicate", "conflict": "conflict", "anomaly": "anomaly", "entity": "entity", "classification": "classification"}

def open_case(inv, user):
    if inv.status == "New":
        inv.status, inv.assignee = "Under Review", user
        db.session.commit()
        audit.log("investigation_opened", user=user, doc_id=inv.doc_id, investigation_id=inv.id, source="human")

def decide(inv, user, action, reason="", field_id=None, value=None):
    if action not in ACTIONS:
        raise ValueError(f"unknown action '{action}'")
    if action == "correct":
        f = db.session.get(DocumentField, field_id) if field_id else None
        if not f or f.doc_id != inv.doc_id or value is None:
            raise ValueError("correct requires field_id (of this document) and value")
        old = f.value
        f.value, f.confidence, f.corrected = str(value), 1.0, True
        db.session.commit()
        audit.log("field_corrected", user=user, doc_id=inv.doc_id, investigation_id=inv.id, field=f.name, previous=old, new=value, reason=reason, source="human")
        feedback_for_field(inv, f, old, value, user, reason)
    prev = inv.status
    inv.status = ACTIONS[action]
    inv.escalated = inv.escalated or action == "escalate"
    if action == "escalate": inv.assignee = None
    db.session.add(Decision(investigation_id=inv.id, user=user, action=action, reason=reason))
    db.session.commit()
    audit.log(f"decision_{action}", user=user, doc_id=inv.doc_id, investigation_id=inv.id, field="status", previous=prev, new=inv.status, reason=reason, source="human")
    if action == "correct":
        pipeline.analyze(inv.doc)  # re-score after correction
    return inv

def feedback_for_field(inv, f, old, new, user, reason):
    db.session.add(Feedback(investigation_id=inv.id, doc_id=inv.doc_id, task="field_extraction", ai_prediction=f"{f.name}={old}",
                            human_label=f"{f.name}={new}", reason=reason, user=user)); db.session.commit()

def add_feedback(inv, user, task, ai_prediction, human_label, reason=""):
    fb = Feedback(investigation_id=inv.id, doc_id=inv.doc_id, task=task, ai_prediction=ai_prediction, human_label=human_label, reason=reason, user=user)
    db.session.add(fb); db.session.commit()
    audit.log("feedback_recorded", user=user, doc_id=inv.doc_id, investigation_id=inv.id, previous=ai_prediction, new=human_label, reason=reason, source="human")
    return fb
