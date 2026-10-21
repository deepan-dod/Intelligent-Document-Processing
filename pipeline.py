"""End-to-end pipeline: classify -> quality -> preprocess -> OCR -> fields -> entities -> relationships ->
consistency/duplicate/anomaly/integrity -> explainable risk -> investigation."""
import os
import numpy as np
from flask import current_app
from database.models import (db, Document, DocumentPage, OcrLine, DocumentField, DocumentEntity, Relationship,
                             Evidence, ModelPrediction)
from audit import audit_log as audit
from preprocessing import image_processing as ip, quality as qa
from ocr.engine import run_ocr
from documents import classifier
from understanding.field_extractor import extract_fields
from understanding.entity_extractor import extract_entities
from entities import resolver
from relationships import relationship_engine
from investigation import consistency, duplicate_detection, anomaly_detection, integrity_analysis, decision_engine

def _cfg(): return current_app.config

def _clean_json(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {str(k): _clean_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [_clean_json(v) for v in obj]
    elif hasattr(obj, "isoformat"):
        return obj.isoformat()
    elif hasattr(obj, "item") and getattr(obj, "size", 1) == 1:
        return obj.item()
    return obj

def _ev(doc, kind, title, detail=None, score=0.0, related=None, field=None):
    clean_detail = _clean_json(detail) if detail else {}
    e = Evidence(doc_id=doc.id, kind=kind, title=title, detail=clean_detail, score=score, related_doc_id=related, field_name=field)
    db.session.add(e); return e

def process_document(doc_id):
    doc = db.session.get(Document, doc_id)
    if not doc:
        return None
    cfg = _cfg()
    try:
        # Clean up prior artifacts for idempotency (e.g. on re-processing)
        DocumentPage.query.filter_by(doc_id=doc.id).delete()
        OcrLine.query.filter_by(doc_id=doc.id).delete()
        DocumentField.query.filter_by(doc_id=doc.id).delete()
        DocumentEntity.query.filter_by(doc_id=doc.id).delete()
        Evidence.query.filter_by(doc_id=doc.id).delete()
        ModelPrediction.query.filter_by(doc_id=doc.id).delete()
        db.session.flush()

        doc.status = "Processing"; db.session.commit()
        images = ip.load_pages(doc.stored_path)
        doc.page_count = len(images)
        doc.quality = qa.analyze_pages(images)
        audit.log("quality_analyzed", doc_id=doc.id, new=doc.quality["overall"])
        processed = [ip.preprocess(i) for i in images]
        folder = os.path.join(cfg["UPLOAD_FOLDER"], "processed")
        for n, (p, im) in enumerate(zip(ip.save_processed(processed, folder, f"doc{doc.id}"), processed), 1):
            db.session.add(DocumentPage(doc_id=doc.id, number=n, width=im.shape[1], height=im.shape[0], processed_path=p))
        low_quality = doc.quality["overall"] < cfg["MIN_QUALITY"]
        if low_quality:
            _ev(doc, "quality", f"Low document quality ({doc.quality['overall']:.0%}); OCR may be unreliable", doc.quality, 1 - doc.quality["overall"])
        # OCR (PaddleOCR primary, PDF text layer fallback)
        lines, engine = run_ocr(processed, doc.stored_path, cfg["OCR_ENGINE"])
        doc.ocr_engine = engine
        for l in lines:
            db.session.add(OcrLine(doc_id=doc.id, **l))
        doc.full_text = "\n".join(l["text"] for l in lines)
        audit.log("ocr_completed", doc_id=doc.id, new=f"{len(lines)} lines via {engine}")
        # classification
        c = classifier.classify(doc.full_text, cfg["MODEL_DIR"], cfg["CLASSIFY_MIN_CONF"])
        doc.doc_type, doc.type_confidence, doc.type_model, doc.classified_at, doc.needs_type_review = \
            str(c["doc_type"]), float(c["confidence"]), str(c["model_version"]), c["timestamp"], bool(c["needs_review"])
        db.session.add(ModelPrediction(model="classifier", version=c["model_version"], doc_id=doc.id, prediction=doc.doc_type, confidence=doc.type_confidence))
        if c["needs_review"]:
            _ev(doc, "classification", f"Low-confidence document type ({c['doc_type']} {c['confidence']:.0%}); human review needed", c, 1 - c["confidence"])
        audit.log("classified", doc_id=doc.id, new=f"{doc.doc_type} ({doc.type_confidence:.0%})")
        # fields + entities
        fields = extract_fields(doc.doc_type, lines)
        for f in fields:
            db.session.add(DocumentField(doc_id=doc.id, **f))
        entities = extract_entities(fields, doc.full_text)
        variants = resolver.link_document(doc, entities, cfg["ENTITY_MATCH"])
        audit.log("entities_extracted", doc_id=doc.id, new=len(entities))
        for v in variants:
            _ev(doc, "entity", f"Entity name '{v['mention']}' differs from canonical '{v['canonical']}' (match {v['score']:.0%})", v, 1 - v["score"])
        # integrity warning signals
        sig = integrity_analysis.analyze(doc.stored_path, images, [l["confidence"] for l in lines])
        doc.meta = {"integrity": sig}
        for w in sig["warnings"]:
            if not w.startswith("Text/image"):
                _ev(doc, "integrity", w, sig, 0.5)
        doc.status = "Processed (low quality)" if low_quality else "Processed"
        db.session.flush()
        analyze(doc)
        audit.log("processing_completed", doc_id=doc.id, new=doc.status)
    except Exception as exc:  # never crash silently
        db.session.rollback()
        doc = db.session.get(Document, doc_id)
        if doc:
            doc.status, doc.error = "Failed", str(exc)
            db.session.commit()
            audit.log("processing_failed", doc_id=doc.id, reason=str(exc))
    return db.session.get(Document, doc_id)

def analyze(doc):
    """Idempotent cross-document analysis + risk scoring (re-run after human corrections)."""
    cfg = _cfg()
    Evidence.query.filter(Evidence.doc_id == doc.id, Evidence.kind.in_(["conflict", "duplicate", "anomaly", "ocr"])).delete(synchronize_session=False)
    Relationship.query.filter(Relationship.src_type == "document", Relationship.src_id == doc.id, Relationship.rel.in_(["contradicts", "matches"])).delete(synchronize_session=False)
    related = relationship_engine.detect(doc)
    for c in consistency.check(doc, related):
        _ev(doc, "conflict", f"{c['field']} differs: {c['found']} vs {c['expected']} ({' / '.join(c['sources'])})", c, 1.0, c["related_doc_id"], c["field"])
        db.session.add(Relationship(src_type="document", src_id=doc.id, rel="contradicts", dst_type="document", dst_id=c["related_doc_id"], confidence=0.9, note=c["field"]))
    for d in duplicate_detection.find(doc, cfg["DUP_THRESHOLD"]):
        _ev(doc, "duplicate", f"Possible duplicate of DOC-{d['related_doc_id']} ({d['similarity']:.0%}) — human verification required", d, d["similarity"], d["related_doc_id"])
        for a, b in ((doc.id, d["related_doc_id"]),):
            if not Relationship.query.filter_by(src_id=a, dst_id=b, rel="matches").first():
                db.session.add(Relationship(src_type="document", src_id=a, rel="matches", dst_type="document", dst_id=b, confidence=d["similarity"]))
    for a in anomaly_detection.numeric_anomalies(doc):
        _ev(doc, "anomaly", f"Unusual {a['feature']}: {a['value']:g} (historical {a['history_range'][0]:g}–{a['history_range'][1]:g})", a, a["score"], field=a["feature"])
    fa = anomaly_detection.frequency_anomaly(doc, cfg["FREQ_LIMIT"])
    if fa:
        _ev(doc, "anomaly", f"Unusual document frequency: {fa['count']} uploads in {fa['window']}", fa, fa["score"])
    low = [f for f in DocumentField.query.filter_by(doc_id=doc.id) if f.confidence < cfg["LOW_CONF"] and not f.corrected]
    if low:
        _ev(doc, "ocr", f"Low-confidence fields need verification: {', '.join(f.name for f in low)}",
            {"fields": [{"name": f.name, "confidence": f.confidence} for f in low]}, 1 - float(np.mean([f.confidence for f in low])))
    db.session.flush()
    inv, score, prio, factors = decision_engine.upsert_investigation(doc, cfg)
    db.session.commit()
    if inv:
        audit.log("investigation_scored", doc_id=doc.id, investigation_id=inv.id, new=f"{score} {prio}")
    return inv
