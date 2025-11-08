from ..config import settings
from ..llm.provider import choose_model

model = choose_model(settings.model_name)


def synthesize_answer(
    query: str, retrieved: list[dict], max_tokens: int = 3000, temperature: float = 0.5
) -> tuple[str, list[str]]:
    # Select up to MIN_CITATIONS docs for inline markers, ensure diversity
    top = retrieved[: max(settings.min_citations, len(retrieved))]
    top_ids = [r["item_id"] for r in top]
    answer, _stream = model.generate_answer(
        query, top, max_tokens=max_tokens, temperature=temperature
    )
    return answer, top_ids
