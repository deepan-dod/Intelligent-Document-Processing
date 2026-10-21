from database.models import db, Document, Entity, Relationship, Evidence

def build_graph(doc_ids=None, center=None):
    """Nodes/edges (vis-network friendly). If center given, returns its 2-hop neighbourhood."""
    rels = Relationship.query.all()
    if center is not None:
        keep = {("document", center)}
        for _ in range(2):
            for r in rels:
                a, b = (r.src_type, r.src_id), (r.dst_type, r.dst_id)
                if a in keep or b in keep:
                    keep |= {a, b}
        rels = [r for r in rels if (r.src_type, r.src_id) in keep and (r.dst_type, r.dst_id) in keep]
        if not rels:
            keep = {("document", center)}
    nodes, edges = {}, []
    def node(t, i):
        k = f"{t[0]}{i}"
        if k not in nodes:
            if t == "document":
                d = db.session.get(Document, i)
                nodes[k] = dict(id=k, type="document", label=d.code if d else k, title=f"{d.filename} ({d.doc_type})" if d else "", doc_id=i)
            else:
                e = db.session.get(Entity, i)
                nodes[k] = dict(id=k, type="entity", label=e.canonical_name if e else k, title=e.code if e else "", entity_id=i)
        return k
    for r in rels:
        edges.append(dict(from_=node(r.src_type, r.src_id), to=node(r.dst_type, r.dst_id), label=r.rel, confidence=r.confidence))
    if center is not None:
        node("document", center)
        for e in Evidence.query.filter_by(doc_id=center).filter(Evidence.kind.in_(["conflict", "duplicate"])):
            if e.related_doc_id:
                edges.append(dict(from_=node("document", center), to=node("document", e.related_doc_id),
                                  label="contradicts" if e.kind == "conflict" else "matches", confidence=e.score))
    return dict(nodes=list(nodes.values()), edges=[{**e, "from": e.pop("from_")} for e in edges])
