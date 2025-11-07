from __future__ import annotations

from typing import Any

import httpx

from ..config import settings


class CoreApiClient:
    def __init__(self, base_url: str | None = None):
        self.base = base_url or settings.core_api_base
        self._client = httpx.AsyncClient(timeout=10)

    async def search(self, query: str, k: int, filters: dict | None) -> list[dict[str, Any]]:
        # Contract: GET /search?q=...&k=...&topic=...&since=...
        params = {"q": query, "k": k}
        if filters:
            if filters.get("topic"):
                params["topic"] = ",".join(filters["topic"])
            if filters.get("since"):
                params["since"] = filters["since"]
        r = await self._client.get(f"{self.base}/search", params=params)
        r.raise_for_status()
        return r.json().get("results", [])

    async def item(self, slug: str) -> dict[str, Any]:
        r = await self._client.get(f"{self.base}/items/{slug}")
        r.raise_for_status()
        return r.json()

    async def aclose(self):
        await self._client.aclose()
