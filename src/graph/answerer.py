from ..config import settings
from ..llm.provider import Model


def synthesize_answer(
    query: str, retrieved: list[dict], model: Model, max_tokens: int, temperature: float
) -> tuple[str, list[str]]:
    # Select up to MIN_CITATIONS docs for inline markers, ensure diversity
    top = retrieved[: max(settings.min_citations, len(retrieved))]
    top_ids = [r["item_id"] for r in top]
    answer, _stream = model.generate_answer(
        query, top, max_tokens=max_tokens, temperature=temperature
    )
    return answer, top_ids
