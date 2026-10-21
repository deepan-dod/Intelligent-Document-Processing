from conftest import upload, login

def test_auth_required(app):
    c = app.test_client()
    assert c.get("/api/documents").status_code == 401
    assert c.get("/health").status_code == 200

def test_bad_login(app):
    assert app.test_client().post("/login", data={"username": "inv", "password": "wrong"}).status_code == 200
    assert app.test_client().get("/api/documents").status_code == 401

def test_rbac(app, loaded, pdfs):
    aud = login(app, "aud"); rev = login(app, "rev")
    assert aud.get("/api/documents").status_code == 200
    assert upload(aud, pdfs["invoice.pdf"]).status_code == 403
    inv = aud.get("/api/investigations").json[0]["id"]
    assert aud.post(f"/api/investigations/{inv}/decision", json={"action": "approve"}).status_code == 403
    assert rev.post(f"/api/investigations/{inv}/decision", json={"action": "escalate", "reason": "x"}).status_code == 200
    assert rev.post(f"/api/investigations/{inv}/decision", json={"action": "correct", "field_id": 1, "value": "1"}).status_code == 403
    assert aud.post("/api/users", json={}).status_code == 403

def test_upload_validation(client, tmp_path):
    bad = tmp_path / "evil.pdf"; bad.write_bytes(b"MZ\x90\x00 not a pdf")
    assert upload(client, bad).status_code == 400
    exe = tmp_path / "a.exe"; exe.write_bytes(b"%PDF-1.4"); assert upload(client, exe).status_code == 400
    assert client.post("/api/documents/upload").status_code == 400

def test_web_pages(client, loaded):
    for u in ["/", "/documents", "/investigations", "/entities", "/copilot", "/upload", f"/documents/{loaded['invoice.pdf']}"]:
        assert client.get(u).status_code == 200, u
    inv = client.get("/api/investigations").json[0]["id"]
    assert client.get(f"/investigations/{inv}").status_code == 200
