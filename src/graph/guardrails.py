from typing import Dict, List
from ..config import settings


def enforce_citations(
    answer: str, retrieved: List[Dict], citation_ids: List[str], min_citations: int
) -> Dict:
    if not retrieved or len(citation_ids) == 0:
        fallback = "I don’t know yet. Try refining the topic or timeframe (e.g., add a 'since:P7D' filter)."
        return {
            "answer": fallback,
            "answer_stream": [fallback],
            "citations": [],
        }

    # ensure at least min_citations if available
    have = set(citation_ids)
    for r in retrieved:
        if len(have) >= min_citations:
            break
        have.add(r["item_id"])

    # build citation objects in the order they appear in answer markers if any
    by_id = {r["item_id"]: r for r in retrieved}
    ordered = []
    for iid in citation_ids:
        if iid in by_id:
            it = by_id[iid]
            ordered.append({k: it[k] for k in ["item_id", "title", "url", "published_at"]})

    # stream simulation: split by sentence
    chunks = [s.strip() + " " for s in answer.split(". ") if s.strip()]
    return {
        "answer": answer,
        "answer_stream": chunks,
        "citations": ordered,
    }
