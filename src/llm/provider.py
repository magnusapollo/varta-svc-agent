from __future__ import annotations

import logging
import os
from typing import Protocol

logger = logging.getLogger(__name__)


# --------- Provider interface ---------
class Model(Protocol):
    def generate_answer(
        self, query: str, docs: list[dict], max_tokens: int = 500, temperature: float = 0.8
    ) -> tuple[str, list[str]]:
        """
        Returns:
          answer_text: str
          citation_ids: List[str]  # ids matching inline [n] markers in the answer
        """
        ...


# --------- Local stub (existing) ---------
class LocalStub:
    name = "stub-local"

    def generate_answer(self, query: str, docs: list[dict]) -> tuple[str, list[str]]:
        if not docs:
            msg = "I don't know yet. Add a topic or timeframe to help me retrieve the right items."
            return msg, []

        lines = []
        # We map [n] to the *given order* of docs
        citation_ids: list[str] = []
        for i, d in enumerate(docs, start=1):
            tag = f"[{i}]"
            snippet = (d.get("snippet") or d.get("excerpt") or "").strip()
            title = d.get("title", "").strip()
            if snippet:
                lines.append(f"• {snippet} {tag}")
            else:
                lines.append(f"• {title} {tag}")
            citation_ids.append(d["item_id"])

        answer = f"Here's what I found on “{query}”:\n" + "\n".join(lines)
        return answer, citation_ids


# --------- OpenAI provider ---------
class OpenAIChat:
    """
    Lightweight OpenAI chat provider.
    - Uses environment:
        OPENAI_API_KEY (required)
        OPENAI_BASE_URL (optional, for self-hosted / Azure)
    - Model name comes from `MODEL_NAME`, e.g.:
        - "openai:gpt-5" (recommended pattern)
        - "gpt-5" (treated as OpenAI model)
        - "openai:gpt-4o-mini" etc.
    - We instruct the model that sources are indexed [1..N] in the order provided.
      We then return citation_ids = [doc.item_id for doc in docs[:N]] so the caller
      can resolve [n] → that id/title/url.
    """

    def __init__(self, model_name: str):
        self.model = self._normalize_model(model_name)
        try:
            # Prefer modern SDK usage
            from openai import OpenAI  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "The 'openai' package is required for OpenAI provider. "
                "Add `openai>=1.0.0` to requirements and set OPENAI_API_KEY."
            ) from e

        base = os.getenv("OPENAI_BASE_URL")
        if base:
            self._client = OpenAI(base_url=base, api_key=os.getenv("OPENAI_API_KEY"))
        else:
            self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set in the environment.")

    @staticmethod
    def _normalize_model(name: str) -> str:
        # Accept both "openai:MODEL" and raw model names (e.g., "gpt-5")
        if name.startswith("openai:"):
            return name.split(":", 1)[1]
        return name

    def generate_answer(
        self, query: str, docs: list[dict], max_tokens: int
    ) -> tuple[str, list[str]]:
        if not docs:
            return "I don't know yet. Try adding a topic filter or a timeframe like since:P7D.", []

        # Build source list in fixed order; instruct model to cite with [n]
        sources_lines = []
        citation_ids: list[str] = []
        for i, d in enumerate(docs, start=1):
            sources_lines.append(
                f"[{i}] {d.get('title', '').strip()} — {d.get('url', '')} "
                f"(published: {d.get('published_at', '')})\n"
                f"Snippet: {(d.get('snippet') or d.get('excerpt') or '').strip()}"
            )
            citation_ids.append(d["item_id"])
        sources_block = "\n\n".join(sources_lines)

        system = (
            "You are an assistant for a site-only RAG chat. "
            "Synthesize concise answers **only** from the provided sources. "
            "Every substantive claim must end with an inline citation marker like [1] or [2]. "
            "Prefer 2-3 citations from different sources when available. "
            "If the sources are insufficient, say you don't know."
        )

        user = (
            f"User question:\n{query}\n\n"
            f"Sources (use [n] markers exactly as indexed):\n{sources_block}\n\n"
            "Answer requirements:\n"
            "- Be concise and factual.\n"
            "- Use only the sources above; no external info.\n"
            "- Add [n] markers at the end of sentences that use source n.\n"
            "- If uncertain, say you don't know."
        )

        try:
            # Prefer chat.completions endpoint for broad compatibility
            resp = self._client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_output_tokens=max_tokens,
            )
            content = resp.output_text
            logger.debug("Model Response: %s", content)
        except Exception as e:
            # Fall back gracefully to a stub-like response on error
            logger.error("Model failed, falling back to local. Error: %s", e)
            fallback_lines = []
            for i, d in enumerate(docs[:3], start=1):
                snippet = (d.get("snippet") or d.get("excerpt") or "").strip()
                title = d.get("title", "").strip()
                tag = f"[{i}]"
                fallback_lines.append(f"• {snippet or title} {tag}")
            content = (
                "Here's what I found (OpenAI call failed; using fallback stitching):\n"
                + "\n".join(fallback_lines)
            )

        # We return the ids in the exact order we enumerated sources so [n] → docs[n-1]
        return content, citation_ids


# --------- Registry / factory ---------
_REGISTRY = {
    "stub-local": LocalStub(),
    # We register a sentinel; instances of OpenAIChat are created dynamically
}


def choose_model(name: str | None) -> Model:
    logger.info(f"model chosen: {name}")
    if not name:
        return _REGISTRY["stub-local"]
    lower = name.lower()
    # Treat any "openai:*" or a known OpenAI family (e.g., gpt-5, gpt-4o) as OpenAI
    if lower.startswith("openai:") or lower.startswith("gpt-"):
        return OpenAIChat(name)

    return _REGISTRY.get(name, _REGISTRY["stub-local"])
