from typing import List, Dict, Tuple
from ..llm.provider import choose_model
from ..config import settings

def synthesize_answer(query: str, retrieved: List[Dict], model_name: str, max_tokens: int, temperature: float) -> Tuple[str, List[str]]:
    model = choose_model(model_name)
    # Select up to MIN_CITATIONS docs for inline markers, ensure diversity
    top = retrieved[: max(settings.MIN_CITATIONS, len(retrieved))]
    top_ids = [r["item_id"] for r in top]
    answer, stream = model.generate_answer(query, top)
    return answer, top_ids
