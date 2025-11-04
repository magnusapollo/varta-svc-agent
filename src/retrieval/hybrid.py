from __future__ import annotations
import json, math, time
from typing import Dict, Any, List, Tuple
import numpy as np
from pathlib import Path
import tldextract

from ..utils.time import parse_since_to_timestamp
from ..config import settings

_FIX = Path(__file__).resolve().parents[2] / "fixtures"
_items = json.loads((_FIX / "items.json").read_text(encoding="utf-8"))
_snips = json.loads((_FIX / "snippets.json").read_text(encoding="utf-8"))

# ----------------------------
# Build corpus
# ----------------------------
_docs: List[str] = []
ids: List[str] = []
timestamps: List[int] = []
domains: List[str] = []

for it in _items:
    ids.append(it["id"])
    txt = " ".join([it["title"], it.get("excerpt", ""), _snips.get(it["id"], "")])
    _docs.append(txt)
    ts = int(time.mktime(time.strptime(it["published_at"], "%Y-%m-%d")))
    timestamps.append(ts)
    ext = tldextract.extract(it["url"]).registered_domain
    domains.append(ext or "unknown.test")

# ----------------------------
# Keyword TF-IDF (no sklearn, with optional sklearn fast-path)
# ----------------------------
try:
    # Fast path if scikit-learn is available (optional; not required)
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore

    _tfidf = TfidfVectorizer(max_features=20000)
    _X_sparse = _tfidf.fit_transform(_docs)
    _X = _X_sparse.toarray().astype(np.float32)

    def _tfidf_encode(texts: List[str]) -> np.ndarray:
        return _tfidf.transform(texts).toarray().astype(np.float32)

except Exception:
    # Pure-Python fallback (no scipy/sklearn)
    from ..utils.tfidf import SimpleTfidfVectorizer

    _tfidf = SimpleTfidfVectorizer(max_features=20000)
    _X = _tfidf.fit_transform(_docs).astype(np.float32)

    def _tfidf_encode(texts: List[str]) -> np.ndarray:
        return _tfidf.transform(texts).astype(np.float32)

# ----------------------------
# Embeddings (sentence-transformers optional)
# ----------------------------
try:
    from sentence_transformers import SentenceTransformer  # type: ignore

    _emb_model = SentenceTransformer(settings.EMBEDDING_MODEL)
    _emb_dim = _emb_model.get_sentence_embedding_dimension()
    vecs = _emb_model.encode(_docs, normalize_embeddings=True)
    vecs = np.asarray(vecs, dtype=np.float32)
except Exception:
    # Fallback: use TF-IDF vectors as pseudo-embeddings
    vecs = _X.copy()
    norms = np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-8
    vecs = vecs / norms
    _emb_dim = vecs.shape[1]

# In-memory "vector store"
class InMemoryVectorStore:
    def __init__(self, dim: int):
        self.dim = dim
        self.ids: List[str] = []
        self.vecs: np.ndarray | None = None

    def add(self, ids: List[str], vectors: np.ndarray) -> None:
        assert vectors.shape[1] == self.dim
        self.ids.extend(ids)
        if self.vecs is None:
            self.vecs = vectors.astype(np.float32)
        else:
            self.vecs = np.vstack([self.vecs, vectors.astype(np.float32)])

    def search(self, q: np.ndarray, k: int) -> List[Tuple[str, float]]:
        if self.vecs is None or len(self.ids) == 0:
            return []
        q = q.astype(np.float32)
        sims = (self.vecs @ q) / (np.linalg.norm(self.vecs, axis=1) * (np.linalg.norm(q) + 1e-8) + 1e-8)
        idx = np.argsort(-sims)[:k]
        return [(self.ids[i], float(sims[i])) for i in idx]


_vec_store = InMemoryVectorStore(dim=_emb_dim)
_vec_store.add(ids, vecs)

# ----------------------------
# Scoring components
# ----------------------------
def _keyword_scores(q: str, k: int) -> List[Tuple[str, float]]:
    qv = _tfidf_encode([q])[0]
    sims = _X @ qv
    idx = np.argsort(-sims)[:k]
    return [(ids[i], float(sims[i])) for i in idx]

def _embed_scores(q: str, k: int) -> List[Tuple[str, float]]:
    try:
        qv = _emb_model.encode([q], normalize_embeddings=True)  # type: ignore[name-defined]
        qv = np.asarray(qv[0], dtype=np.float32)
    except Exception:
        qv = _tfidf_encode([q])[0]
        qv = qv / (np.linalg.norm(qv) + 1e-8)
    return _vec_store.search(qv, k)

def _recency_boost(ts: int, now_ts: int) -> float:
    half_life = settings.RECENCY_HALFLIFE_DAYS * 86400.0
    age = max(0.0, now_ts - ts)
    return 2 ** (-age / half_life)

# ----------------------------
# Public API
# ----------------------------
def hybrid_search(query: str, k: int, topics: List[str] | None, since: str | None) -> List[Dict[str, Any]]:
    now_ts = int(time.time())
    base_k = max(k * 6, 30)

    kw = dict(_keyword_scores(query, base_k))
    em = dict(_embed_scores(query, base_k))

    # merge + recency
    scores: Dict[str, float] = {}
    for doc_id in set(list(kw.keys()) + list(em.keys())):
        s_kw = kw.get(doc_id, 0.0)
        s_em = em.get(doc_id, 0.0)
        idx = ids.index(doc_id)
        ts = timestamps[idx]
        rec = _recency_boost(ts, now_ts)
        score = settings.ALPHA_EMBED * s_em + settings.BETA_KEYWORD * s_kw + settings.GAMMA_RECENCY * rec
        scores[doc_id] = score

    # filters
    if since:
        cutoff = parse_since_to_timestamp(since, now_ts)
        scores = {i: s for i, s in scores.items() if timestamps[ids.index(i)] >= cutoff}

    if topics:
        topics_set = set(t.lower() for t in topics)
        def has_topic(it): return bool(set(t.lower() for t in it.get("topics", [])) & topics_set)
        scores = {i: s for i, s in scores.items() if has_topic(_items[ids.index(i)])}

    # diversify by domain
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    per_domain: Dict[str, int] = {}
    out: List[Dict[str, Any]] = []
    for doc_id, sc in ranked:
        meta = _items[ids.index(doc_id)]
        dom = domains[ids.index(doc_id)]
        if per_domain.get(dom, 0) >= settings.MAX_PER_DOMAIN:
            continue
        out.append({
            "item_id": doc_id,
            "score": round(sc, 6),
            "slug": meta["slug"],
            "title": meta["title"],
        })
        per_domain[dom] = per_domain.get(dom, 0) + 1
        if len(out) >= k:
            break
    return out

def resolve_items(item_ids: List[str]) -> List[Dict[str, Any]]:
    by_id = {it["id"]: it for it in _items}
    result: List[Dict[str, Any]] = []
    for iid in item_ids:
        it = by_id.get(iid)
        if not it:
            continue
        result.append({
            "item_id": it["id"],
            "title": it["title"],
            "url": it["url"],
            "published_at": it["published_at"],
            "snippet": _snips.get(iid, ""),
        })
    return result
