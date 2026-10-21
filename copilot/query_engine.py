from database.models import Document, Evidence, Investigation
from copilot.evidence_retriever import retrieve

def search(q):
    """Intelligent search: intent-based retrieval, then fallback to ID / full-text LIKE."""
    r = retrieve(q)
    ids = list(r["docs"])
    if not ids:
        ql = q.lower().strip()
        like = f"%{ql}%"
        ids = [d.id for d in Document.query.filter(Document.full_text.ilike(like) | Document.filename.ilike(like) | Document.doc_type.ilike(like))]
    return Document.query.filter(Document.id.in_(ids)).all() if ids else []
