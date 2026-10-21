import hashlib, os, uuid
from flask import current_app
from werkzeug.utils import secure_filename
from database.models import db, Document
from audit import audit_log as audit

MAGIC = {b"%PDF": "application/pdf", b"\xff\xd8\xff": "image/jpeg", b"\x89PNG": "image/png"}

class UploadError(ValueError): pass

def sniff(head):
    return next((m for k, m in MAGIC.items() if head.startswith(k)), None)

def save_upload(file, user):
    """Validate extension + magic bytes + size; store original under a random name (never overwritten)."""
    cfg = current_app.config
    name = secure_filename(file.filename or "")
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in cfg["ALLOWED_EXT"]:
        raise UploadError(f"'{name}': unsupported extension")
    data = file.read()
    if not data or len(data) > cfg["MAX_CONTENT_LENGTH"]:
        raise UploadError(f"'{name}': empty or too large")
    mime = sniff(data[:8])
    if mime not in cfg["ALLOWED_MIME"] or (ext == "pdf") != (mime == "application/pdf"):
        raise UploadError(f"'{name}': content does not match its extension")
    folder = os.path.join(cfg["UPLOAD_FOLDER"], "originals"); os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{uuid.uuid4().hex}.{ext}")
    with open(path, "wb") as fh: fh.write(data)
    os.chmod(path, 0o440)
    doc = Document(filename=name, stored_path=path, sha256=hashlib.sha256(data).hexdigest(), mime=mime,
                   size=len(data), uploader=user, status="Queued")
    db.session.add(doc); db.session.commit()
    audit.log("document_uploaded", user=user, doc_id=doc.id, new=name, source="human")
    return doc
