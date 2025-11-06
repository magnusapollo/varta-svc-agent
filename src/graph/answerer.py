from typing import List, Dict, Tuple
from ..llm.provider import Model
from ..config import settings

def synthesize_answer(query: str, retrieved: List[Dict], model: Model, max_tokens: int, temperature: float) -> Tuple[str, List[str]]:
    # Select up to MIN_CITATIONS docs for inline markers, ensure diversity
    top = retrieved[: max(settings.min_citations, len(retrieved))]
    top_ids = [r["item_id"] for r in top]
    answer, stream = model.generate_answer(query, top, max_tokens=max_tokens, temperature=temperature)
    return answer, top_ids
