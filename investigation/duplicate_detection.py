import re
from difflib import SequenceMatcher
from database.models import Document, DocumentField

def _tok(t): return re.sub(r"\s+", " ", t.lower()).strip()

def similarity(a, b):
    """Blend of OCR-text similarity (0.5), field overlap (0.35) and metadata (0.15)."""
    ta, tb = _tok(a.full_text or ""), _tok(b.full_text or "")
    text = SequenceMatcher(None, ta[:4000], tb[:4000]).ratio() if ta and tb else 0.0
    fa = {f.name: f.value.strip().lower() for f in DocumentField.query.filter_by(doc_id=a.id)}
    fb = {f.name: f.value.strip().lower() for f in DocumentField.query.filter_by(doc_id=b.id)}
    keys = set(fa) | set(fb)
    fld = sum(1 for k in keys if fa.get(k) == fb.get(k)) / len(keys) if keys else 0.0
    meta = 1.0 if a.sha256 == b.sha256 else (0.5 if a.doc_type == b.doc_type and a.size and b.size and abs(a.size - b.size) / max(a.size, b.size) < 0.05 else 0.0)
    return round(0.5 * text + 0.35 * fld + 0.15 * meta, 3) if a.sha256 != b.sha256 else 1.0

def find(doc, threshold=0.9):
    out = []
    for o in Document.query.filter(Document.id != doc.id, Document.status.like("Processed%")):
        s = similarity(doc, o)
        if s >= threshold:
            out.append(dict(related_doc_id=o.id, similarity=s, exact=(o.sha256 == doc.sha256)))
    return out
