import re

ORG_SUFFIX = r"(?:Pvt\.?\s*Ltd\.?|Private Limited|Limited|Ltd\.?|Inc\.?|LLC|LLP|Corp\.?|Technologies|Industries|Solutions|Enterprises)"
ORG_RE = re.compile(r"\b((?:[A-Z][\w&\.]*\s){1,4}" + ORG_SUFFIX + r"(?:\s*Pvt\.?\s*Ltd\.?)?)")
PERSON_RE = re.compile(r"\b(?:Mr|Ms|Mrs|Dr)\.?\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)")
FIELD_ENTITY = {"organization": "organization", "supplier": "organization", "vendor": "organization",
                "issuing_organization": "organization", "parties": "organization", "holder": "person", "name": "person",
                "location": "location", "address": "location"}
ID_TYPES = {"contract_id": "contract_id", "po_number": "document_id", "delivery_number": "document_id",
            "certificate_id": "certificate_id", "invoice_number": "document_id"}

def extract_entities(fields, text):
    """Returns [{mention, etype, role, confidence}] from labelled fields plus free-text patterns."""
    out, seen = [], set()
    def add(m, t, role, conf):
        m = m.strip(" .,;")
        if len(m) > 2 and (m.lower(), t) not in seen:
            seen.add((m.lower(), t)); out.append(dict(mention=m, etype=t, role=role, confidence=conf))
    for f in fields:
        if f["name"] in FIELD_ENTITY:
            vals = re.split(r"\s+(?:and|&)\s+|;", f["value"]) if f["name"] == "parties" else [f["value"]]
            for v in vals:
                add(v, FIELD_ENTITY[f["name"]], f["name"], f["confidence"])
        elif f["name"] in ID_TYPES:
            add(f["value"], ID_TYPES[f["name"]], f["name"], f["confidence"])
    for m in ORG_RE.findall(text):
        add(m, "organization", "mention", 0.7)
    for m in PERSON_RE.findall(text):
        add(m, "person", "mention", 0.7)
    return out
