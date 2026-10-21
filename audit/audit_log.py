import hashlib, json
from datetime import datetime
from database.models import db, AuditLog

def log(action, user="system", doc_id=None, investigation_id=None, field=None,
        previous=None, new=None, reason=None, source="system"):
    """Append a hash-chained audit record (tamper-evident; updates/deletes are blocked)."""
    last = AuditLog.query.order_by(AuditLog.id.desc()).first()
    prev = last.hash if last else "0" * 64
    rec = AuditLog(user=user, action=action, doc_id=doc_id, investigation_id=investigation_id,
                   ts=datetime.utcnow(), field_name=field, previous_value=None if previous is None else str(previous),
                   new_value=None if new is None else str(new), reason=reason, source=source, prev_hash=prev)
    rec.hash = _h(rec)  # hash computed before INSERT so the row is never updated
    db.session.add(rec)
    db.session.commit()
    return rec

def _h(r):
    payload = json.dumps([r.prev_hash, r.user, r.action, r.doc_id, r.investigation_id, r.field_name,
                          r.previous_value, r.new_value, r.reason, r.source, r.ts.isoformat()])
    return hashlib.sha256(payload.encode()).hexdigest()

def verify_chain():
    prev = "0" * 64
    for r in AuditLog.query.order_by(AuditLog.id):
        if r.prev_hash != prev or r.hash != _h(r):
            return False, r.id
        prev = r.hash
    return True, None

def history(doc_id=None, investigation_id=None):
    q = AuditLog.query
    if doc_id: q = q.filter_by(doc_id=doc_id)
    if investigation_id: q = q.filter_by(investigation_id=investigation_id)
    return q.order_by(AuditLog.id).all()

def to_dict(r):
    return {"id": r.id, "time": r.ts.isoformat(), "user": r.user, "action": r.action, "document": r.doc_id,
            "investigation": r.investigation_id, "field": r.field_name, "previous": r.previous_value,
            "new": r.new_value, "reason": r.reason, "source": r.source}
