import re
from database.models import (db, Document, Evidence, Investigation, DocumentField, DocumentEntity, Entity, EntityAlias, AuditLog)

def doc_ref(q):
    m = re.search(r"\bDOC-?(\d+)\b", q, re.I)
    return int(m.group(1)) if m else None

def ev_dict(e):
    return dict(id=e.id, doc=f"DOC-{e.doc_id}", kind=e.kind, title=e.title, related=f"DOC-{e.related_doc_id}" if e.related_doc_id else None)

def retrieve(q):
    """Query understanding -> database retrieval. Returns {intent, facts[], refs[], docs[]}; facts are the ONLY source for answers."""
    ql, did = q.lower(), doc_ref(q)
    facts, refs, docs = [], [], []
    def kind_rows(kind, d=None):
        qs = Evidence.query.filter_by(kind=kind)
        if d: qs = qs.filter((Evidence.doc_id == d) | (Evidence.related_doc_id == d))
        return qs.all()
    if did and re.search(r"why|flag|reason|score|priority", ql):
        intent = "explain"; inv = Investigation.query.filter_by(doc_id=did).first()
        if inv:
            facts.append(f"DOC-{did} is in {inv.code}: priority {inv.priority}, score {inv.score}/100, status {inv.status}.")
            for r in sorted(inv.reasons, key=lambda r: -r.points):
                facts.append(f"Reason (+{r.points}): {r.text}"); refs.append(f"evidence:{r.evidence_id}")
        else:
            facts.append(f"DOC-{did} has no open investigation.")
    elif re.search(r"contradict|conflict", ql) and not re.search(r"entit", ql):
        intent = "conflicts"
        for e in kind_rows("conflict", did): facts.append(f"{e.title} [DOC-{e.doc_id}]"); refs.append(f"evidence:{e.id}"); docs += [e.doc_id, e.related_doc_id]
    elif "duplicate" in ql:
        intent = "duplicates"
        for e in kind_rows("duplicate", did): facts.append(f"{e.title} [DOC-{e.doc_id}]"); refs.append(f"evidence:{e.id}"); docs += [e.doc_id, e.related_doc_id]
    elif re.search(r"low.*(ocr|confidence)|confidence", ql):
        intent = "low_confidence"
        for f in DocumentField.query.filter(DocumentField.confidence < 0.75).order_by(DocumentField.confidence):
            if not did or f.doc_id == did:
                facts.append(f"DOC-{f.doc_id} field '{f.name}'='{f.value}' confidence {f.confidence:.0%}"); refs.append(f"field:{f.id}"); docs.append(f.doc_id)
    elif re.search(r"entit.*(conflict|differ|variant|alias)|conflicting information", ql):
        intent = "entity_conflicts"
        for e in Entity.query.all():
            if e.aliases: facts.append(f"{e.code} '{e.canonical_name}' also appears as: {', '.join(a.alias for a in e.aliases)}"); refs.append(f"entity:{e.id}")
    elif re.search(r"changed|history|audit|what happened", ql):
        intent = "audit"
        for r in AuditLog.query.filter(AuditLog.doc_id == did).order_by(AuditLog.id).all() if did else AuditLog.query.order_by(AuditLog.id.desc()).limit(15):
            facts.append(f"{r.ts:%Y-%m-%d %H:%M} {r.user}: {r.action}" + (f" ({r.field_name}: {r.previous_value} → {r.new_value})" if r.field_name else "")); refs.append(f"audit:{r.id}"); docs.append(r.doc_id)
    elif re.search(r"related to|about|documents (for|of)", ql):
        intent = "entity_docs"
        name = re.split(r"related to|about|documents (?:for|of)", ql, 1)[-1].strip(" ?.")
        for de in DocumentEntity.query.join(Entity, Entity.id == DocumentEntity.entity_id).filter(DocumentEntity.mention.ilike(f"%{name}%")):
            facts.append(f"DOC-{de.doc_id} mentions '{de.mention}' as {de.role} (entity ENT-{de.entity_id})"); refs.append(f"doc:{de.doc_id}"); docs.append(de.doc_id)
    elif "high" in ql and "priorit" in ql:
        intent = "priority"
        for i in Investigation.query.filter(Investigation.priority.in_(["High", "Critical"])).all():
            facts.append(f"{i.code} DOC-{i.doc_id}: {i.priority} ({i.score}/100), {i.status}"); docs.append(i.doc_id); refs.append(f"investigation:{i.id}")
    elif did:
        intent = "document"; d = db.session.get(Document, did)
        if d:
            facts.append(f"DOC-{d.id} '{d.filename}' type {d.doc_type} ({d.type_confidence:.0%}), status {d.status}")
            facts += [f"{f.name} = {f.value} ({f.confidence:.0%})" for f in DocumentField.query.filter_by(doc_id=did)]; docs.append(did)
    else:
        intent = "unknown"
    return dict(intent=intent, facts=facts, refs=refs, docs=[d for d in dict.fromkeys(docs) if d])
