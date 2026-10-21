import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from app import create_app
from config import TestConfig
from database.models import db
from auth.security import create_user
from documents.samples import SCENARIO, make_pdf

class Cfg(TestConfig):
    MODEL_DIR = tempfile.mkdtemp()
    UPLOAD_FOLDER = tempfile.mkdtemp()

@pytest.fixture()
def app():
    a = create_app(Cfg)
    with a.app_context():  # context closed before requests so Flask-Login doesn't cache users across clients
        for n, r in [("inv", "investigator"), ("rev", "reviewer"), ("aud", "auditor")]:
            create_user(n, "password123", r)
    yield a
    with a.app_context():
        db.session.remove(); db.drop_all()

def login(app, user="inv", pw="password123"):
    c = app.test_client(); c.post("/login", data={"username": user, "password": pw}); return c

@pytest.fixture()
def client(app): return login(app)

@pytest.fixture()
def pdfs(tmp_path):
    out = {}
    for name, lines in SCENARIO.items():
        p = tmp_path / name; make_pdf(str(p), lines); out[name] = p
    return out

def upload(client, path, name=None):
    with open(path, "rb") as fh:
        return client.post("/api/documents/upload", data={"files": (fh, name or os.path.basename(path))}, content_type="multipart/form-data")

@pytest.fixture()
def loaded(client, pdfs):
    ids = {}
    for name in ["contract.pdf", "purchase_order.pdf", "delivery.pdf", "invoice.pdf", "certificate.pdf"]:
        r = upload(client, pdfs[name]); assert r.status_code == 201, r.json
        ids[name] = r.json["documents"][0]["id"]
    return ids
