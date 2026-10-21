from conftest import upload, login
from documents.classifier import classify
from entities.resolver import similarity, normalize
from understanding.field_extractor import extract_fields, parse_date, parse_num
from investigation.risk_engine import compute
from preprocessing import quality
from investigation import integrity_analysis
from audit import audit_log
import numpy as np, cv2

def test_classification_and_fields(client, loaded):
    docs = {d["filename"]: d for d in client.get("/api/documents").json}
    assert docs["invoice.pdf"]["type"] == "invoice" and docs["contract.pdf"]["type"] == "contract"
    assert docs["certificate.pdf"]["type"] == "certificate"
    f = {x["name"]: x for x in client.get(f"/api/documents/{loaded['invoice.pdf']}/fields").json}
    assert f["quantity"]["value"] == "12" and f["quantity"]["bbox"] and f["quantity"]["confidence"] > 0.9

def test_field_extraction_helpers():
    lines = [dict(page=1, text="Quantity: 10", confidence=0.9, bbox=[0, 0, 1, 1]), dict(page=1, text="Expiry Date: 99-99-9999", confidence=0.9, bbox=[0, 0, 1, 1])]
    f = {x["name"]: x for x in extract_fields("certificate", lines)}
    assert f["expiry_date"]["confidence"] < 0.6
    assert parse_num("Rs 1,200.50") == 1200.5 and parse_date("08-10-2026").year == 2026

def test_entity_resolution():
    assert similarity("ABC Technologies Pvt Ltd", "A.B.C Technologies") >= 0.8
    assert similarity("ABC Technologies Pvt Ltd", "Zenith Supplies") < 0.5
    assert normalize("ABC Tech Pvt. Ltd.") == "abc tech"

def test_cross_document_conflict_and_graph(client, loaded):
    ev = client.get(f"/api/documents/{loaded['invoice.pdf']}/evidence").json
    q = [e for e in ev if e["kind"] == "conflict" and e["field"] == "quantity"]
    assert q and q[0]["detail"]["expected"] in ("10",) and q[0]["detail"]["found"] == "12"
    rel = client.get(f"/api/documents/{loaded['invoice.pdf']}/relationships").json
    assert any(r["relationship"] == "references" for r in rel["relationships"])
    assert any(r["relationship"] == "contradicts" for r in rel["relationships"])
    ents = client.get("/api/entities").json
    abc = [e for e in ents if "ABC" in e["canonical_name"]][0]
    assert any("A.B.C" in a for a in abc["aliases"])

def test_certificate_contract_conflict(client, loaded):
    ev = client.get(f"/api/documents/{loaded['certificate.pdf']}/evidence").json
    assert any(e["kind"] == "conflict" and e["field"] == "expiry_date" for e in ev)

def test_risk_and_investigation(client, loaded):
    inv = client.get(f"/api/documents/{loaded['invoice.pdf']}/investigation").json
    assert inv and inv["score"] >= 30 and inv["reasons"] and any(f["factor"] == "conflict" for f in inv["factors"])
    risk = client.get(f"/api/documents/{loaded['invoice.pdf']}/risk").json
    assert risk["score"] == inv["score"]

def test_duplicate_detection(client, loaded, pdfs):
    r = upload(client, pdfs["invoice.pdf"], "invoice_copy.pdf")
    ev = client.get(f"/api/documents/{r.json['documents'][0]['id']}/evidence").json
    assert any(e["kind"] == "duplicate" and "human verification" in e["title"] for e in ev)

def test_anomaly_detection(client, tmp_path):
    from documents.samples import make_pdf
    for i in range(7):
        p = tmp_path / f"po{i}.pdf"
        make_pdf(str(p), ["PURCHASE ORDER", f"PO Number: PO-{i}", "Supplier: Zenith Supplies Pvt Ltd", "Items: Bolts", f"Quantity: {10 + i}", "Unit Price: 5"]); upload(client, p)
    p = tmp_path / "big.pdf"
    make_pdf(str(p), ["PURCHASE ORDER", "PO Number: PO-99", "Supplier: Zenith Supplies Pvt Ltd", "Items: Bolts", "Quantity: 250", "Unit Price: 5"])
    r = upload(client, p)
    ev = client.get(f"/api/documents/{r.json['documents'][0]['id']}/evidence").json
    assert any(e["kind"] == "anomaly" and "quantity" in e["title"] for e in ev)

def test_integrity_warning_not_fraud(tmp_path):
    from documents.samples import make_pdf
    p = tmp_path / "x.pdf"; make_pdf(str(p), ["INVOICE"], producer="Adobe Photoshop")
    s = integrity_analysis.analyze(str(p), [], [])
    assert s["status"] == "Review Recommended" and "not proof" in s["note"]

def test_quality_scores():
    sharp = np.full((900, 700, 3), 255, np.uint8); cv2.putText(sharp, "Hello World", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 4)
    blur = cv2.GaussianBlur(sharp, (51, 51), 0)
    assert quality.analyze(sharp)["sharpness"] > quality.analyze(blur)["sharpness"]

def test_risk_bands():
    assert compute([], {}, [(80, "Critical"), (0, "Low")])[1] == "Low"

def test_decision_correction_feedback_audit(client, loaded):
    inv = client.get(f"/api/documents/{loaded['invoice.pdf']}/investigation").json
    fid = [f for f in client.get(f"/api/documents/{loaded['invoice.pdf']}/fields").json if f["name"] == "quantity"][0]["id"]
    r = client.post(f"/api/investigations/{inv['id']}/decision", json={"action": "correct", "field_id": fid, "value": "10", "reason": "OCR/typo"})
    assert r.status_code == 200
    ev = client.get(f"/api/documents/{loaded['invoice.pdf']}/evidence").json
    assert not any(e["kind"] == "conflict" and e["field"] == "quantity" for e in ev)  # re-analysis cleared it
    assert client.post(f"/api/investigations/{inv['id']}/decision", json={"action": "bogus"}).status_code == 400
    assert client.post(f"/api/investigations/{inv['id']}/feedback", json={"task": "duplicate", "ai_prediction": "Possible Duplicate", "human_label": "Not a Duplicate", "reason": "revised"}).status_code == 201
    log = client.get(f"/api/documents/{loaded['invoice.pdf']}/audit").json
    assert any(a["action"] == "field_corrected" and a["previous"] == "12" and a["new"] == "10" for a in log)
    assert client.get("/api/audit/verify").json["intact"] is True

def test_audit_immutable(app):
    import pytest
    from database.models import db, AuditLog
    with app.app_context():
        audit_log.log("x"); r = AuditLog.query.first(); r.action = "tamper"
        with pytest.raises(PermissionError): db.session.commit()
        db.session.rollback()

def test_copilot_grounded(client, loaded):
    d = loaded["invoice.pdf"]
    a = client.post("/api/copilot", json={"question": f"Why was DOC-{d} flagged?"}).json
    assert a["grounded"] and "quantity" in a["answer"].lower() and a["refs"]
    assert "couldn't find" in client.post("/api/copilot", json={"question": "tell me a joke"}).json["answer"]
    assert client.post("/api/copilot", json={"question": "which documents contradict " + f"DOC-{d}"}).json["evidence"]

def test_reports(client, loaded):
    inv = client.get(f"/api/documents/{loaded['invoice.pdf']}/investigation").json["id"]
    for fmt, magic in (("csv", b"Investigation"), ("xlsx", b"PK"), ("pdf", b"%PDF")):
        r = client.get(f"/api/reports/investigation/{inv}.{fmt}"); assert r.status_code == 200 and r.data.startswith(magic)

def test_dashboard_search_models(client, loaded):
    d = client.get("/api/dashboard").json
    assert d["documents"] == 5 and d["conflicts"] >= 2
    assert client.get("/api/search?q=possible duplicates").status_code == 200
    assert client.get("/api/search?q=CERT-19").json
    assert client.post("/api/models/train").status_code == 403  # investigator can't manage models
    assert client.get("/api/models").status_code == 200
