from database.models import DocumentField
from understanding.field_extractor import parse_num, parse_date

SHARED = ["quantity", "unit_price", "total", "delivery_date"]

def _fields(doc_id):
    return {f.name: f for f in DocumentField.query.filter_by(doc_id=doc_id)}

def _same(name, a, b):
    if name.endswith("date"):
        da, db_ = parse_date(a), parse_date(b)
        return da == db_ if da and db_ else a.strip() == b.strip()
    na, nb = parse_num(a), parse_num(b)
    return na == nb if na is not None and nb is not None else a.strip().lower() == b.strip().lower()

def check(doc, related):
    """Compare this document with related docs. Returns list of conflict dicts."""
    mine, out = _fields(doc.id), []
    for o in related:
        theirs = _fields(o.id)
        for name in SHARED:
            if name in mine and name in theirs and not _same(name, mine[name].value, theirs[name].value):
                out.append(dict(field=name, expected=theirs[name].value, found=mine[name].value,
                                sources=[o.code, doc.code], related_doc_id=o.id, kind="value"))
        # certificate expiry vs contract end date (contract-term conflict)
        pair = {doc.doc_type: mine, o.doc_type: theirs}
        if {"certificate", "contract"} <= set(pair):
            exp, end = parse_date(pair["certificate"].get("expiry_date").value) if "expiry_date" in pair["certificate"] else None, \
                       parse_date(pair["contract"].get("end_date").value) if "end_date" in pair["contract"] else None
            if exp and end and exp < end and not any(c["field"] == "expiry_date" and c["related_doc_id"] == o.id for c in out):
                out.append(dict(field="expiry_date", expected=f"valid through contract end {end:%d-%m-%Y}", found=f"{exp:%d-%m-%Y}",
                                sources=[o.code, doc.code], related_doc_id=o.id, kind="expiry"))
    return out
