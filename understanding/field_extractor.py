import re
from datetime import datetime

FIELDS = {
 "contract": {"contract_id": ["contract id", "contract no", "contract number"], "parties": ["parties", "party"],
              "start_date": ["start date", "effective date"], "end_date": ["end date", "termination date", "expiry date"],
              "contract_value": ["contract value", "value"], "terms": ["terms"], "obligations": ["obligations"]},
 "purchase_order": {"po_number": ["po number", "po no", "purchase order number", "purchase order no"],
              "organization": ["organization", "buyer", "company"], "supplier": ["supplier", "vendor"],
              "order_date": ["order date", "date"], "items": ["items", "item"], "quantity": ["quantity", "qty"],
              "unit_price": ["unit price", "price"], "delivery_date": ["delivery date"],
              "contract_ref": ["contract ref", "contract reference"]},
 "delivery": {"delivery_number": ["delivery no", "delivery number", "delivery note no"],
              "po_ref": ["po ref", "po reference", "po number"], "supplier": ["supplier", "vendor"],
              "organization": ["consignee", "organization", "buyer"], "delivery_date": ["delivery date", "date"],
              "items": ["items", "item"], "quantity": ["quantity delivered", "quantity", "qty"]},
 "certificate": {"certificate_id": ["certificate id", "certificate no", "certificate number"],
              "holder": ["holder", "issued to", "name"], "issuing_organization": ["issuing organization", "issued by", "issuer"],
              "issue_date": ["issue date", "date of issue"], "expiry_date": ["expiry date", "valid until"],
              "certificate_type": ["certificate type", "type"], "contract_ref": ["contract ref", "contract reference"]},
 "invoice": {"invoice_number": ["invoice number", "invoice no"], "vendor": ["vendor", "supplier", "billed by"],
              "organization": ["bill to", "organization", "customer"], "date": ["invoice date", "date"],
              "items": ["items", "item"], "quantity": ["quantity", "qty"], "unit_price": ["unit price", "price"],
              "tax": ["tax", "gst"], "total": ["total", "total amount"], "po_ref": ["po ref", "po reference", "po number"]},
}
GENERIC = {"reference": ["reference", "ref", "reference number"], "date": ["date"], "organization": ["organization", "company"],
           "name": ["name", "applicant"], "amount": ["amount", "total"]}
ID_FIELDS = ["contract_id", "po_number", "delivery_number", "certificate_id", "invoice_number"]
REF_FIELDS = ["contract_ref", "po_ref"]
NUMERIC = {"quantity", "unit_price", "total", "tax", "contract_value", "amount"}
DATES = {"start_date", "end_date", "order_date", "delivery_date", "issue_date", "expiry_date", "date"}
DATE_FMTS = ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%d.%m.%Y"]

def parse_date(s):
    for f in DATE_FMTS:
        try: return datetime.strptime(s.strip(), f).date()
        except ValueError: pass
    return None

def parse_num(s):
    m = re.search(r"-?\d[\d,]*\.?\d*", str(s))
    return float(m.group(0).replace(",", "")) if m else None

def extract_fields(doc_type, lines):
    """lines: [{page,text,confidence,bbox}] -> [{name,value,confidence,page,bbox}] (traceable to source line)."""
    spec = {**GENERIC, **FIELDS.get(doc_type, {})}
    lookup = {}
    for fname, labels in spec.items():
        for lab in labels:
            lookup.setdefault(lab, fname)
    found = {}
    for ln in lines:
        if ":" not in ln["text"]:
            continue
        label, value = ln["text"].split(":", 1)
        fname = lookup.get(label.strip().lower())
        value = value.strip()
        if not fname or not value or fname in found:
            continue
        conf = ln["confidence"]
        if fname in DATES and parse_date(value) is None:
            conf *= 0.6
        if fname in NUMERIC and parse_num(value) is None:
            conf *= 0.6
        found[fname] = dict(name=fname, value=value, confidence=round(conf, 3), page=ln["page"], bbox=ln["bbox"])
    return list(found.values())
