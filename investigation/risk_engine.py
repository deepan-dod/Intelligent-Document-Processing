def band(score, bands):
    return next(name for lo, name in bands if score >= lo)

def compute(evidence, weights, bands):
    """Explainable additive score. Each factor is capped at its configured weight (conflicts may exceed up to +40%).
    Returns (score, priority, factors[], per-evidence points)."""
    by = {}
    for e in evidence:
        by.setdefault(e.kind, []).append(e)
    factors, pts = [], {}
    for kind, items in by.items():
        w = weights.get(kind, 0)
        if not w: continue
        if kind == "conflict":
            total = min(w * 1.4, w + 5 * (len(items) - 1))
        elif kind in ("duplicate", "anomaly"):
            total = w * max(max(e.score or 0, 0.6) for e in items)
        elif kind == "integrity":
            total = min(w * 2, w * len(items) / 2 + w / 2)
        else:
            total = w * min(1.0, 0.5 + 0.25 * len(items))
        total = round(total)
        factors.append({"factor": kind, "points": total, "count": len(items)})
        for e in items: pts[e.id] = round(total / len(items))
    score = min(100, sum(f["points"] for f in factors))
    return score, band(score, bands), sorted(factors, key=lambda f: -f["points"]), pts
