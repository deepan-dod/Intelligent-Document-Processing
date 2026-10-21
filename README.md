# Intelligent Document Investigation & Decision System

Evidence-driven document investigation: **Document → OCR → Fields → Entities → Relationships → Evidence graph →
Consistency / Duplicate / Anomaly / Integrity → Explainable risk → Human decision → Audit → ML feedback.**
It produces *warning signals and investigation priorities* — never "fraud = true".

## Quick start
```bash
pip install -r requirements.txt
# optional primary OCR engine (large): pip install paddlepaddle paddleocr
export FLASK_APP=app:create_app
flask demo-data        # loads the PO / delivery / invoice / contract / certificate scenario
python app.py          # http://localhost:5000   login: admin / admin123
pytest -q              # 21 tests
```
Docker: `docker compose up --build` (Postgres + app + MLflow UI on :5001).

## Notes
* **OCR**: PaddleOCR is used when installed (`OCR_ENGINE=auto|paddle`); otherwise the PDF text layer is used
  (scanned images then need PaddleOCR). Every line keeps page, confidence and bounding box for field traceability.
* **Evidence**: all findings live in one `evidence` table (kind = conflict/duplicate/anomaly/integrity/entity/ocr/quality/classification).
* **Risk**: additive, weights/bands configurable in `config.py` (`RISK_WEIGHTS`, `RISK_BANDS`). Reasons link to evidence.
* **Audit**: hash-chained, insert-only (`GET /api/audit/verify`).
* **Copilot**: retrieves DB evidence first; if `ANTHROPIC_API_KEY` is set an LLM phrases the answer from *only* that evidence.
* **MLOps**: `flask train-models` (or `POST /api/models/train`) retrains from seed + human feedback, logs to MLflow, registers a version.
* **Roles**: admin, investigator, reviewer, auditor (RBAC in `auth/permissions.py`). Change the default admin password.
* Not included / next steps: CSRF tokens for the HTML forms, async worker queue, Alembic migrations, per-type field templates beyond key:value layouts.
