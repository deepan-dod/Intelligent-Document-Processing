import cv2
import numpy as np
from preprocessing.image_processing import estimate_skew

def _clip(x): return float(max(0.0, min(1.0, x)))

def analyze(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = g.shape
    sharp = cv2.Laplacian(g, cv2.CV_64F).var()
    mean, std = float(g.mean()), float(g.std())
    noise = float(np.abs(g.astype(np.float32) - cv2.medianBlur(g, 3).astype(np.float32)).mean())
    skew = estimate_skew(g)
    ink = float((g < 128).mean())
    s = {"resolution": _clip(min(h, w) / 800), "sharpness": _clip(sharp / 120),
         "brightness": _clip(1 - abs(mean - 190) / 190), "contrast": _clip(std / 55),
         "noise": _clip(1 - noise / 12), "skew": _clip(1 - abs(skew) / 15),
         "text_visibility": _clip(ink / 0.02) if ink < 0.02 else _clip(1 - (ink - 0.35) / 0.4)}
    s["overall"] = round(sum(s.values()) / len(s), 3)
    s["skew_degrees"] = round(skew, 2)
    return {k: round(v, 3) for k, v in s.items()}

def analyze_pages(images):
    rs = [analyze(i) for i in images[:5]]
    return {k: round(float(np.mean([r[k] for r in rs])), 3) for k in rs[0]}
