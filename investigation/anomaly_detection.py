from datetime import datetime, timedelta
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from database.models import Document, DocumentField
from understanding.field_extractor import parse_num

def _vec(doc_id):
    d = {f.name: parse_num(f.value) for f in DocumentField.query.filter_by(doc_id=doc_id) if f.name in ("quantity", "total", "unit_price")}
    return d

def numeric_anomalies(doc):
    """Compare numeric features against history of the same document type (IF + LOF + OCSVM voting; robust z-score fallback)."""
    cur = _vec(doc.id)
    hist = [(o.id, _vec(o.id)) for o in Document.query.filter(Document.id != doc.id, Document.doc_type == doc.doc_type, Document.status.like("Processed%"))]
    out = []
    for feat, val in cur.items():
        if val is None: continue
        h = np.array([v[feat] for _, v in hist if v.get(feat) is not None], dtype=float)
        if len(h) < 5: continue
        if len(h) >= 12:
            sc = StandardScaler().fit(h.reshape(-1, 1)); X = sc.transform(h.reshape(-1, 1)); x = sc.transform([[val]])
            votes = [IsolationForest(random_state=0, contamination="auto").fit(X).predict(x)[0],
                     LocalOutlierFactor(n_neighbors=min(10, len(h) - 1), novelty=True).fit(X).predict(x)[0],
                     OneClassSVM(nu=0.05, gamma="scale").fit(X).predict(x)[0]]
            score = sum(v == -1 for v in votes) / 3
            flagged = score >= 2 / 3
            method = "ensemble(IsolationForest,LOF,OneClassSVM)"
        else:
            med = np.median(h); mad = np.median(np.abs(h - med)) or max(abs(med) * 0.1, 1.0)
            z = abs(val - med) / (1.4826 * mad)
            score = float(min(1.0, z / 8)); flagged = z > 3.5; method = "robust-zscore"
        if flagged:
            out.append(dict(feature=feat, value=val, history_range=[float(h.min()), float(h.max())], score=round(float(score), 2), method=method))
    return out

def frequency_anomaly(doc, limit):
    since = datetime.utcnow() - timedelta(days=1)
    n = Document.query.filter(Document.uploader == doc.uploader, Document.uploaded_at >= since).count()
    return dict(count=n, window="24h", score=round(min(1.0, n / (limit * 2)), 2)) if n > limit else None
