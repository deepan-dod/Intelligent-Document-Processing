"""Training / MLOps: trains classifier (seed + human feedback), logs to MLflow when available, registers versions."""
import os
from database.models import db, Document, Feedback, ModelVersion, ModelPrediction
from documents import classifier

def train_classifier(model_dir, tracking_uri=None):
    from sklearn.model_selection import cross_val_predict
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support
    extra = [(d.full_text, fb.human_label.split("=")[-1]) for fb in Feedback.query.filter_by(task="classification")
             if (d := db.session.get(Document, fb.doc_id)) and d.full_text]
    pipe, version = classifier.train(extra, save_dir=model_dir)
    X = [classifier._doc_text(s) for t, ss in classifier.SEED.items() for s in ss] + [classifier._doc_text(t) for t, _ in extra]
    y = [t for t, ss in classifier.SEED.items() for _ in ss] + [l for _, l in extra]
    pred = pipe.predict(X)  # resubstitution metrics on the small seed set (replace with real held-out data)
    p, r, f, _ = precision_recall_fscore_support(y, pred, average="weighted", zero_division=0)
    metrics = dict(accuracy=float(accuracy_score(y, pred)), precision=float(p), recall=float(r), f1=float(f), n_train=len(y), feedback_samples=len(extra))
    try:
        import mlflow
        mlflow.set_tracking_uri(tracking_uri or os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns"))
        mlflow.set_experiment("document-classifier")
        with mlflow.start_run(run_name=version):
            mlflow.log_metrics(metrics); mlflow.log_param("model", "tfidf+logreg")
            mlflow.log_artifact(os.path.join(model_dir, "classifier.joblib"))
    except Exception as e:  # MLflow optional at runtime
        metrics["mlflow"] = f"skipped: {e.__class__.__name__}"
    ModelVersion.query.filter_by(name="classifier").update({"active": False})
    mv = ModelVersion(name="classifier", version=version, metrics=metrics, path=os.path.join(model_dir, "classifier.joblib"), active=True)
    db.session.add(mv); db.session.commit()
    classifier.reset_cache()
    return mv

def monitoring():
    """Human correction rate, feedback counts, confidence drift (mean confidence recent vs. earlier)."""
    import numpy as np
    preds = ModelPrediction.query.order_by(ModelPrediction.id).all()
    conf = [p.confidence for p in preds]
    half = len(conf) // 2
    drift = float(np.mean(conf[half:]) - np.mean(conf[:half])) if half >= 3 else None
    fb = Feedback.query.count()
    corrections = Feedback.query.filter(Feedback.ai_prediction != Feedback.human_label).count()
    return dict(predictions=len(preds), feedback=fb, human_correction_rate=round(corrections / fb, 3) if fb else None,
                mean_confidence=round(float(np.mean(conf)), 3) if conf else None, prediction_drift=drift)
