"""OCR: PaddleOCR primary; falls back to the PDF text layer when PaddleOCR isn't installed."""
import fitz
import numpy as np

_paddle = None

def paddle_engine():
    global _paddle
    if _paddle is None:
        try:
            from paddleocr import PaddleOCR
            _paddle = PaddleOCR(lang="en", use_angle_cls=True)
        except Exception:
            _paddle = False
    return _paddle or None

def _parse_paddle(res, page):
    out = []
    if not res:
        return out
    first = res[0] if isinstance(res, list) else res
    if isinstance(first, dict) or hasattr(first, "keys"):   # PaddleOCR 3.x
        for r in res:
            polys = r.get("rec_polys") if r.get("rec_polys") is not None else r.get("dt_polys", [])
            for t, c, poly in zip(r.get("rec_texts", []), r.get("rec_scores", []), polys):
                pts = np.array(poly)
                out.append(dict(page=page, text=t, confidence=float(c),
                                bbox=[float(pts[:, 0].min()), float(pts[:, 1].min()), float(pts[:, 0].max()), float(pts[:, 1].max())]))
    else:                                                    # PaddleOCR 2.x
        for line in first or []:
            pts = np.array(line[0]); t, c = line[1]
            out.append(dict(page=page, text=t, confidence=float(c),
                            bbox=[float(pts[:, 0].min()), float(pts[:, 1].min()), float(pts[:, 0].max()), float(pts[:, 1].max())]))
    return out

def text_layer(pdf_path, zoom=2.0):
    out = []
    with fitz.open(pdf_path) as pdf:
        for pno, page in enumerate(pdf, 1):
            for b in page.get_text("dict")["blocks"]:
                for ln in b.get("lines", []):
                    t = "".join(s["text"] for s in ln["spans"]).strip()
                    if t:
                        out.append(dict(page=pno, text=t, confidence=0.99, bbox=[round(v * zoom, 1) for v in ln["bbox"]]))
    return out

def run_ocr(images, path, engine_pref="auto"):
    """Returns (lines, engine_name). lines = [{page,text,confidence,bbox}]"""
    eng = paddle_engine() if engine_pref in ("auto", "paddle") else None
    if eng:
        lines = []
        for i, im in enumerate(images, 1):
            try:
                res = eng.ocr(im) if hasattr(eng, "ocr") else eng.predict(im)
            except TypeError:
                res = eng.predict(im)
            lines += _parse_paddle(res, i)
        if lines:
            return lines, "paddleocr"
    if path.lower().endswith(".pdf"):
        lines = text_layer(path)
        if lines:
            return lines, "pdf-text-layer"
    return [], "none"
