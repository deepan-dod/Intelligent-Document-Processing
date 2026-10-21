import re
from difflib import SequenceMatcher
from database.models import db, Entity, EntityAlias, DocumentEntity

SUFFIXES = {"pvt", "ltd", "private", "limited", "inc", "llc", "llp", "co", "corp", "corporation", "company"}

def normalize(name):
    n = re.sub(r"(?<=\b\w)\.(?=\w\b)", "", name.lower())      # A.B.C -> ABC
    n = re.sub(r"(?<=\w)\.(?=\w)", "", n)
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    toks = [t for t in n.split() if t not in SUFFIXES]
    return " ".join(toks)

def similarity(a, b):
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    seq = SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    jac = len(ta & tb) / len(ta | tb)
    contain = 0.9 if (na in nb or nb in na) and min(len(na), len(nb)) >= 4 else 0
    return round(max(seq, jac, contain), 3)

def resolve(mention, etype, threshold=0.8):
    """Returns (Entity, score, is_new). Non-name types match exactly; names use fuzzy score (never blind merge)."""
    best, best_s = None, 0.0
    for ent in Entity.query.filter_by(etype=etype):
        names = [ent.canonical_name] + [a.alias for a in ent.aliases]
        s = 1.0 if mention.lower() in (n.lower() for n in names) else max(similarity(mention, n) for n in names)
        if etype in ("contract_id", "certificate_id", "document_id"):
            s = 1.0 if s == 1.0 else 0.0
        if s > best_s:
            best, best_s = ent, s
    if best is not None and best_s >= threshold:
        if mention.lower() not in {a.alias.lower() for a in best.aliases} | {best.canonical_name.lower()}:
            db.session.add(EntityAlias(entity_id=best.id, alias=mention, match_score=best_s))
        return best, best_s, False
    ent = Entity(canonical_name=mention, etype=etype)
    db.session.add(ent); db.session.flush()
    return ent, 1.0, True

def link_document(doc, entities, threshold):
    """Persist DocumentEntity rows; returns list of name-variant findings."""
    variants = []
    for e in entities:
        ent, score, new = resolve(e["mention"], e["etype"], threshold)
        db.session.add(DocumentEntity(doc_id=doc.id, entity_id=ent.id, mention=e["mention"], etype=e["etype"],
                                      role=e["role"], confidence=e["confidence"], match_score=score))
        if not new and e["mention"].lower() != ent.canonical_name.lower():
            variants.append(dict(mention=e["mention"], canonical=ent.canonical_name, score=score, entity=ent.id))
    db.session.flush()
    return variants
