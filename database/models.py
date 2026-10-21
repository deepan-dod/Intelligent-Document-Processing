from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import event

db = SQLAlchemy()
now = datetime.utcnow

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="investigator")  # admin|investigator|reviewer|auditor
    active = db.Column(db.Boolean, default=True)

class Document(db.Model):
    __tablename__ = "documents"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    stored_path = db.Column(db.String(500))
    sha256 = db.Column(db.String(64), index=True)
    mime = db.Column(db.String(80))
    size = db.Column(db.Integer)
    uploader = db.Column(db.String(80))
    uploaded_at = db.Column(db.DateTime, default=now)
    doc_type = db.Column(db.String(40), default="other")
    type_confidence = db.Column(db.Float, default=0)
    type_model = db.Column(db.String(40))
    classified_at = db.Column(db.DateTime)
    needs_type_review = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(40), default="Uploaded")
    quality = db.Column(db.JSON)
    meta = db.Column(db.JSON)
    full_text = db.Column(db.Text, default="")
    page_count = db.Column(db.Integer, default=0)
    ocr_engine = db.Column(db.String(30))
    error = db.Column(db.Text)
    @property
    def code(self): return f"DOC-{self.id}"

class DocumentPage(db.Model):
    __tablename__ = "document_pages"
    id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.Integer, db.ForeignKey("documents.id"), index=True)
    number = db.Column(db.Integer)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    processed_path = db.Column(db.String(500))

class OcrLine(db.Model):
    __tablename__ = "document_text"
    id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.Integer, db.ForeignKey("documents.id"), index=True)
    page = db.Column(db.Integer)
    text = db.Column(db.Text)
    confidence = db.Column(db.Float)
    bbox = db.Column(db.JSON)  # [x1,y1,x2,y2] in rendered-page pixels

class DocumentField(db.Model):
    __tablename__ = "document_fields"
    id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.Integer, db.ForeignKey("documents.id"), index=True)
    name = db.Column(db.String(60))
    value = db.Column(db.Text)
    confidence = db.Column(db.Float)
    page = db.Column(db.Integer)
    bbox = db.Column(db.JSON)
    corrected = db.Column(db.Boolean, default=False)

class Entity(db.Model):
    __tablename__ = "entities"
    id = db.Column(db.Integer, primary_key=True)
    canonical_name = db.Column(db.String(255))
    etype = db.Column(db.String(30))
    aliases = db.relationship("EntityAlias", backref="entity", cascade="all, delete-orphan")
    @property
    def code(self): return f"ENT-{self.id}"

class EntityAlias(db.Model):
    __tablename__ = "entity_aliases"
    id = db.Column(db.Integer, primary_key=True)
    entity_id = db.Column(db.Integer, db.ForeignKey("entities.id"), index=True)
    alias = db.Column(db.String(255))
    match_score = db.Column(db.Float)

class DocumentEntity(db.Model):
    __tablename__ = "document_entities"
    id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.Integer, db.ForeignKey("documents.id"), index=True)
    entity_id = db.Column(db.Integer, db.ForeignKey("entities.id"), nullable=True)
    mention = db.Column(db.String(255))
    etype = db.Column(db.String(30))
    role = db.Column(db.String(40))
    confidence = db.Column(db.Float)
    match_score = db.Column(db.Float)

class Relationship(db.Model):
    __tablename__ = "relationships"
    id = db.Column(db.Integer, primary_key=True)
    src_type = db.Column(db.String(20))   # document | entity
    src_id = db.Column(db.Integer, index=True)
    rel = db.Column(db.String(30))
    dst_type = db.Column(db.String(20))
    dst_id = db.Column(db.Integer, index=True)
    confidence = db.Column(db.Float, default=1.0)
    note = db.Column(db.Text)

class Evidence(db.Model):
    """Unified findings table: kind = conflict|duplicate|anomaly|integrity|entity|ocr|quality|classification."""
    __tablename__ = "evidence"
    id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.Integer, db.ForeignKey("documents.id"), index=True)
    kind = db.Column(db.String(20), index=True)
    title = db.Column(db.String(300))
    detail = db.Column(db.JSON)
    score = db.Column(db.Float, default=0)
    related_doc_id = db.Column(db.Integer, nullable=True)
    field_name = db.Column(db.String(60))
    created_at = db.Column(db.DateTime, default=now)

class Investigation(db.Model):
    __tablename__ = "investigations"
    id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.Integer, db.ForeignKey("documents.id"), index=True)
    score = db.Column(db.Integer, default=0)
    priority = db.Column(db.String(10))
    factors = db.Column(db.JSON)
    status = db.Column(db.String(30), default="New")
    assignee = db.Column(db.String(80))
    escalated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)
    doc = db.relationship("Document")
    reasons = db.relationship("InvestigationReason", backref="investigation", cascade="all, delete-orphan")
    @property
    def code(self): return f"INV-{self.id}"

class InvestigationReason(db.Model):
    __tablename__ = "investigation_reasons"
    id = db.Column(db.Integer, primary_key=True)
    investigation_id = db.Column(db.Integer, db.ForeignKey("investigations.id"), index=True)
    text = db.Column(db.String(300))
    evidence_id = db.Column(db.Integer)
    points = db.Column(db.Integer)

class Decision(db.Model):
    __tablename__ = "investigation_decisions"
    id = db.Column(db.Integer, primary_key=True)
    investigation_id = db.Column(db.Integer, db.ForeignKey("investigations.id"), index=True)
    user = db.Column(db.String(80))
    action = db.Column(db.String(30))
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=now)

class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    ts = db.Column(db.DateTime, default=now)
    user = db.Column(db.String(80))
    action = db.Column(db.String(80))
    doc_id = db.Column(db.Integer, index=True)
    investigation_id = db.Column(db.Integer, index=True)
    field_name = db.Column(db.String(60))
    previous_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    reason = db.Column(db.Text)
    source = db.Column(db.String(30))  # system | human | api
    prev_hash = db.Column(db.String(64))
    hash = db.Column(db.String(64))

@event.listens_for(AuditLog, "before_update")
@event.listens_for(AuditLog, "before_delete")
def _immutable(*_):
    raise PermissionError("Audit log is immutable")

class ModelVersion(db.Model):
    __tablename__ = "model_versions"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60))
    version = db.Column(db.String(30))
    metrics = db.Column(db.JSON)
    path = db.Column(db.String(300))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=now)

class ModelPrediction(db.Model):
    __tablename__ = "model_predictions"
    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(60))
    version = db.Column(db.String(30))
    doc_id = db.Column(db.Integer, index=True)
    prediction = db.Column(db.String(100))
    confidence = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=now)

class Feedback(db.Model):
    __tablename__ = "feedback"
    id = db.Column(db.Integer, primary_key=True)
    investigation_id = db.Column(db.Integer, index=True)
    doc_id = db.Column(db.Integer, index=True)
    task = db.Column(db.String(30))        # duplicate | classification | anomaly | entity | conflict
    ai_prediction = db.Column(db.String(100))
    human_label = db.Column(db.String(100))
    reason = db.Column(db.Text)
    user = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=now)
