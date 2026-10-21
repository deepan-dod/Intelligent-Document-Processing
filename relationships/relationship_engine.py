from database.models import db, Document, DocumentField, DocumentEntity, Relationship
from understanding.field_extractor import ID_FIELDS, REF_FIELDS

def _add(src, sid, rel, dst, did, conf=1.0, note=None):
    if not Relationship.query.filter_by(src_type=src, src_id=sid, rel=rel, dst_type=dst, dst_id=did).first():
        db.session.add(Relationship(src_type=src, src_id=sid, rel=rel, dst_type=dst, dst_id=did, confidence=conf, note=note))

def detect(doc):
    """Create belongs_to / issued_by / references / related_to relationships. Returns related Document list."""
    related = {}
    for de in DocumentEntity.query.filter_by(doc_id=doc.id):
        if de.etype in ("organization", "person"):
            rel = "issued_by" if de.role in ("issuing_organization", "vendor", "supplier") else "belongs_to"
            _add("document", doc.id, rel, "entity", de.entity_id, de.match_score, de.mention)
    fields = {f.name: f.value for f in DocumentField.query.filter_by(doc_id=doc.id)}
    my_ids = {fields[k] for k in ID_FIELDS if k in fields}
    others = Document.query.filter(Document.id != doc.id, Document.status.like("Processed%")).all()
    for o in others:
        of = {f.name: f.value for f in DocumentField.query.filter_by(doc_id=o.id)}
        o_ids = {of[k] for k in ID_FIELDS if k in of}
        if any(fields.get(k) in o_ids for k in REF_FIELDS if fields.get(k)):
            _add("document", doc.id, "references", "document", o.id, 0.95); related[o.id] = o
        elif any(of.get(k) in my_ids for k in REF_FIELDS if of.get(k)):
            _add("document", o.id, "references", "document", doc.id, 0.95); related[o.id] = o
    # entity-sharing documents are related_to (weaker)
    ent_ids = [d.entity_id for d in DocumentEntity.query.filter_by(doc_id=doc.id) if d.etype == "organization"]
    if ent_ids:
        for de in DocumentEntity.query.filter(DocumentEntity.entity_id.in_(ent_ids), DocumentEntity.doc_id != doc.id):
            o = db.session.get(Document, de.doc_id)
            if o and o.id not in related and o.status.startswith("Processed"):
                _add("document", doc.id, "related_to", "document", o.id, 0.6, "shared entity"); related[o.id] = o
    # a certificate/doc supersedes? flag same type + same id as 'supersedes' candidate handled by duplicates
    db.session.flush()
    return list(related.values())
