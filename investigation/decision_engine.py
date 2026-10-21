from database.models import db, Investigation, InvestigationReason, Evidence, Document
from investigation.risk_engine import compute

def upsert_investigation(doc, cfg):
    """Score the document, (re)build explainable reasons, create/refresh investigation if above threshold."""
    ev = Evidence.query.filter_by(doc_id=doc.id).all()
    score, prio, factors, pts = compute(ev, cfg["RISK_WEIGHTS"], cfg["RISK_BANDS"])
    inv = Investigation.query.filter_by(doc_id=doc.id).first()
    if not inv and (score >= cfg["INVESTIGATION_THRESHOLD"] or doc.needs_type_review):
        inv = Investigation(doc_id=doc.id, status="New"); db.session.add(inv); db.session.flush()
    if inv:
        inv.score, inv.priority, inv.factors = score, prio, factors
        for r in list(inv.reasons): db.session.delete(r)
        for e in sorted(ev, key=lambda e: -pts.get(e.id, 0)):
            if pts.get(e.id, 0) > 0:
                db.session.add(InvestigationReason(investigation_id=inv.id, text=e.title, evidence_id=e.id, points=pts[e.id]))
    db.session.flush()
    return inv, score, prio, factors

def explain(doc_id):
    inv = Investigation.query.filter_by(doc_id=doc_id).first()
    if not inv: return None
    return dict(investigation=inv.code, priority=inv.priority, score=inv.score, factors=inv.factors,
                reasons=[dict(text=r.text, evidence_id=r.evidence_id, points=r.points) for r in inv.reasons])
