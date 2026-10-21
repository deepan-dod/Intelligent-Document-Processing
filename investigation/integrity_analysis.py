import re
import cv2
import numpy as np
import fitz

EDITORS = re.compile(r"photoshop|gimp|canva|paint|pixlr|editor|foxit phantom|sejda|ilovepdf|smallpdf", re.I)

def _pdf_dt(s):
    m = re.search(r"(\d{4})(\d{2})(\d{2})(\d{2})?(\d{2})?(\d{2})?", s or "")
    return tuple(int(x or 0) for x in m.groups()) if m else None

def metadata_signals(path):
    sig = {"normal": [], "warnings": []}
    if path.lower().endswith(".pdf"):
        with fitz.open(path) as pdf:
            md = pdf.metadata or {}
        prod = f"{md.get('producer', '')} {md.get('creator', '')}"
        if EDITORS.search(prod): sig["warnings"].append(f"Metadata: produced/edited with '{prod.strip()}'")
        c, m = _pdf_dt(md.get("creationDate")), _pdf_dt(md.get("modDate"))
        if c and m and m > c and (m[0], m[1], m[2]) != (c[0], c[1], c[2]):
            sig["warnings"].append("Metadata inconsistency: modification date differs from creation date")
        if not md.get("creationDate"): sig["warnings"].append("Metadata: no creation date present")
        if not sig["warnings"]: sig["normal"].append("PDF metadata consistent")
    return sig

def ela_signal(img_bgr, quality=90, z=6.0):
    """Error-level-analysis style check: blocks recompressing very differently from the rest of the image."""
    ok, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    diff = cv2.absdiff(img_bgr, cv2.imdecode(buf, 1)).astype(np.float32).mean(axis=2)
    h, w = diff.shape; bs = 32
    blocks = np.array([diff[y:y + bs, x:x + bs].mean() for y in range(0, h - bs, bs) for x in range(0, w - bs, bs)])
    if blocks.size < 20: return None
    med = np.median(blocks); mad = np.median(np.abs(blocks - med)) + 1e-3
    zmax = (blocks.max() - med) / (1.4826 * mad)
    frac = float((blocks > med + z * 1.4826 * mad).mean())
    return dict(zmax=round(float(zmax), 1), fraction=round(frac, 4)) if zmax > 12 and 0 < frac < 0.05 and blocks.max() > 3 else None

def analyze(path, images, ocr_confidences):
    sig = metadata_signals(path)
    if not path.lower().endswith(".pdf"):
        r = ela_signal(images[0])
        (sig["warnings"].append(f"Unusual image region (compression-level outlier, z={r['zmax']})") if r else sig["normal"].append("Uniform compression levels"))
    if ocr_confidences:
        (sig["normal"] if np.mean(ocr_confidences) >= 0.8 else sig["warnings"]).append(
            "OCR structure consistent" if np.mean(ocr_confidences) >= 0.8 else "Text/image inconsistency: low average OCR confidence")
    sig["status"] = "Review Recommended" if sig["warnings"] else "No warning signals"
    sig["note"] = "Warning signals only; not proof of forgery or fraud."
    return sig
