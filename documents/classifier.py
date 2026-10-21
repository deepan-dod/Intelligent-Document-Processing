import os
from datetime import datetime
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

DOC_TYPES = ["invoice", "purchase_order", "delivery", "contract", "certificate", "application",
             "receipt", "report", "registration", "identity", "technical", "other"]

SEED = {
 "invoice": ["invoice number vendor bill to tax gst total amount due", "tax invoice invoice date quantity unit price total payment terms"],
 "purchase_order": ["purchase order po number supplier order date unit price delivery date", "purchase order buyer supplier items quantity ordered po"],
 "delivery": ["delivery note delivery number consignee goods delivered quantity delivered received by", "delivery document shipment dispatched transporter delivery date"],
 "contract": ["contract agreement parties start date end date contract value terms obligations", "this agreement between parties terms and conditions obligations governing law"],
 "certificate": ["certificate certify issued to holder issuing organization issue date expiry date", "certificate of compliance certificate id valid until holder"],
 "application": ["application form applicant name date of birth signature declaration submit", "application form applicant address applying for"],
 "receipt": ["receipt received payment paid cash receipt amount received thank you", "payment receipt transaction paid by amount"],
 "report": ["business report quarterly summary findings analysis conclusion recommendations", "annual report executive summary performance results"],
 "registration": ["registration certificate registered company registration number incorporation registrar", "registration document registered address date of registration"],
 "identity": ["identity card id number date of birth nationality verification photo identification", "passport driving licence identity verification holder"],
 "technical": ["technical specification system architecture requirements interface version datasheet", "technical document manual installation configuration parameters"],
 "other": ["misc note memo letter general correspondence", "unknown text random content"],
}

def _doc_text(text):
    head = " ".join(text.split("\n")[:2])
    return (head + " ") * 3 + text   # title lines get extra weight

def train(extra=None, save_dir=None):
    X, y = [], []
    for t, ss in SEED.items():
        for s in ss:
            X.append(_doc_text(s)); y.append(t)
    for txt, lab in (extra or []):
        X.append(_doc_text(txt)); y.append(lab)
    pipe = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True), LogisticRegression(C=40, max_iter=2000))
    pipe.fit(X, y)
    version = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        joblib.dump({"model": pipe, "version": version}, os.path.join(save_dir, "classifier.joblib"))
    return pipe, version

_cache = {}

def _load(model_dir):
    p = os.path.join(model_dir, "classifier.joblib")
    if "m" not in _cache or _cache.get("p") != p:
        if os.path.exists(p):
            d = joblib.load(p); _cache.update(m=d["model"], v=d["version"], p=p)
        else:
            m, v = train(save_dir=model_dir); _cache.update(m=m, v=v, p=p)
    return _cache["m"], _cache["v"]

def reset_cache(): _cache.clear()

def classify(text, model_dir, min_conf=0.6):
    if not text.strip():
        return dict(doc_type="other", confidence=0.0, model_version="n/a", timestamp=datetime.utcnow(), needs_review=True)
    m, v = _load(model_dir)
    proba = m.predict_proba([_doc_text(text)])[0]
    i = int(proba.argmax())
    conf = float(proba[i])
    return dict(doc_type=m.classes_[i], confidence=round(conf, 3), model_version=v,
                timestamp=datetime.utcnow(), needs_review=conf < min_conf)
