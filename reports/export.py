import csv, io
from database.models import Document, DocumentField, Evidence, Investigation, Decision
from audit import audit_log as audit

def investigation_data(inv):
    d = inv.doc
    return dict(
        investigation=inv.code, document=d.code, filename=d.filename, type=d.doc_type, status=inv.status, priority=inv.priority, score=inv.score,
        factors=inv.factors, fields=[(f.name, f.value, f"{f.confidence:.0%}") for f in DocumentField.query.filter_by(doc_id=d.id)],
        evidence=[(e.kind, e.title) for e in Evidence.query.filter_by(doc_id=d.id)],
        decisions=[(x.created_at.isoformat(timespec="seconds"), x.user, x.action, x.reason or "") for x in Decision.query.filter_by(investigation_id=inv.id)],
        audit=[audit.to_dict(a) for a in audit.history(doc_id=d.id)])

def rows(data, kind):
    if kind == "evidence": return [("kind", "evidence")] + data["evidence"]
    if kind == "audit": return [("time", "user", "action", "field", "previous", "new", "reason", "source")] + [(a["time"], a["user"], a["action"], a["field"], a["previous"], a["new"], a["reason"], a["source"]) for a in data["audit"]]
    out = [("Investigation", data["investigation"]), ("Document", data["document"]), ("Priority", f"{data['priority']} ({data['score']}/100)"), ("Status", data["status"]), ()]
    out += [("FIELDS",)] + [("field", "value", "confidence")] + data["fields"] + [()]
    out += [("EVIDENCE",)] + data["evidence"] + [()] + [("FACTORS",)] + [(f["factor"], f"+{f['points']}") for f in data["factors"] or []] + [()]
    out += [("DECISIONS",)] + data["decisions"]
    return out

def to_csv(r):
    b = io.StringIO(); csv.writer(b).writerows(r); return b.getvalue().encode()

def to_xlsx(r):
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active
    for row in r: ws.append(list(row))
    b = io.BytesIO(); wb.save(b); return b.getvalue()

def to_pdf(r, title):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    b, st = io.BytesIO(), getSampleStyleSheet()
    cells = [[Paragraph(str(c)[:300], st["BodyText"]) for c in row] for row in r if row]
    w = max(len(c) for c in cells) if cells else 1
    SimpleDocTemplate(b, pagesize=A4).build([Paragraph(title, st["Title"]), Spacer(1, 12),
        Table([c + [""] * (w - len(c)) for c in cells], repeatRows=1)])
    return b.getvalue()
