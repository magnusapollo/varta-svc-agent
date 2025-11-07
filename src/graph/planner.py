from typing import Any


def plan_request(query: str, filters: dict[str, Any] | None, k_default: int) -> dict[str, Any]:
    mode = (filters or {}).get("mode") or "summary"
    topics = (filters or {}).get("topic") or []
    since = (filters or {}).get("since")

    # trivial planner: adjust retrieval params based on query heuristics
    k = k_default
    if any(w in query.lower() for w in ["compare", "vs", "pros", "cons"]):
        k = max(k_default, 8)

    return {
        "query": query,
        "topics": topics,
        "since": since,
        "k": k,
        "mode": mode,
    }
