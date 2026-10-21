import os
BASE = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///" + os.path.join(BASE, "idis.db"))
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(BASE, "uploads"))
    MODEL_DIR = os.path.join(BASE, "ml", "models")
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024
    ALLOWED_EXT = {"pdf", "jpg", "jpeg", "png"}
    ALLOWED_MIME = {"application/pdf", "image/jpeg", "image/png"}
    MIN_QUALITY = 0.45          # below -> user is warned
    LOW_CONF = 0.75             # field/OCR confidence considered "needs human verification"
    CLASSIFY_MIN_CONF = 0.60    # below -> human review of document type
    ENTITY_MATCH = 0.80         # alias merge threshold
    DUP_THRESHOLD = 0.90
    FREQ_LIMIT = 25             # docs per uploader per 24h before frequency anomaly
    INVESTIGATION_THRESHOLD = 30
    OCR_ENGINE = os.getenv("OCR_ENGINE", "auto")   # auto | paddle | textlayer
    # Configurable explainable risk weights (max points per factor)
    RISK_WEIGHTS = {"ocr": 10, "conflict": 25, "duplicate": 18, "entity": 12,
                    "integrity": 10, "anomaly": 9, "quality": 8, "classification": 6}
    RISK_BANDS = [(80, "Critical"), (60, "High"), (30, "Medium"), (0, "Low")]
    ADMIN_USER = os.getenv("ADMIN_USER", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    UPLOAD_FOLDER = "/tmp/idis_test_uploads"
    OCR_ENGINE = "textlayer"
