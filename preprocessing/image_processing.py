import os
import cv2
import numpy as np
import fitz  # PyMuPDF

def load_pages(path, zoom=2.0):
    """Return list of BGR page images (PDF pages rendered, or the single image)."""
    if path.lower().endswith(".pdf"):
        out = []
        with fitz.open(path) as pdf:
            for p in pdf:
                pm = p.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
                arr = np.frombuffer(pm.samples, np.uint8).reshape(pm.h, pm.width, 3)
                out.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
        return out
    img = cv2.imread(path)
    if img is None:
        raise ValueError("Unreadable image")
    return [img]

def estimate_skew(gray):
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    pts = cv2.findNonZero(bw)
    if pts is None or len(pts) < 50:
        return 0.0
    ang = cv2.minAreaRect(pts)[-1]
    ang = ang - 90 if ang > 45 else ang
    return float(-ang if abs(ang) < 45 else 0.0) if abs(ang) <= 15 else 0.0

def rotate(img, angle, border=255):
    if abs(angle) < 0.3:
        return img
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_CUBIC, borderValue=(border,) * 3 if img.ndim == 3 else border)

def preprocess(img):
    """grayscale -> denoise -> contrast (CLAHE) -> deskew -> border cleanup -> normalize. Returns BGR."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = cv2.medianBlur(g, 3)  # fast salt-and-pepper noise removal
    g = cv2.createCLAHE(2.0, (8, 8)).apply(g)
    g = rotate(g, estimate_skew(g))
    g = cv2.normalize(g, None, 0, 255, cv2.NORM_MINMAX)
    g = cv2.copyMakeBorder(g[4:-4, 4:-4], 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=255)  # border cleanup
    h, w = g.shape
    if max(h, w) < 1200:  # upscale small scans
        g = cv2.resize(g, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    return cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)

def save_processed(images, folder, stem):
    os.makedirs(folder, exist_ok=True)
    paths = []
    for i, im in enumerate(images, 1):
        p = os.path.join(folder, f"{stem}_p{i}_processed.png")
        cv2.imwrite(p, im); paths.append(p)
    return paths
