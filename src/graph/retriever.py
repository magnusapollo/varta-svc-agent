from typing import Any

from ..config import settings
from ..retrieval.hybrid import hybrid_search, resolve_items


async def retrieve_docs(plan: dict[str, Any]) -> list[dict[str, Any]]:
    # In v1, USE_MOCKS governs whether we call Core API (omitted here) or use fixtures.
    # For simplicity, we always use local hybrid over fixtures;
    # switching to Core API is via client_coreapi.
    k = plan.get("k", settings.retrieve_k)
    res = hybrid_search(plan["query"], k, plan.get("topics"), plan.get("since"))
    # attach snippets for downstream answerer
    metas = resolve_items([r["item_id"] for r in res])
    meta_by_id = {m["item_id"]: m for m in metas}
    enriched = []
    for r in res:
        m = meta_by_id.get(r["item_id"], {})
        enriched.append({**r, **m})
    return enriched
