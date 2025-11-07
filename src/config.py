import os

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    use_mocks: bool = os.getenv("USE_MOCKS", "true").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    core_api_base: str = os.getenv("CORE_API_BASE", "http://localhost:8080/api/v1")
    model_name: str = os.getenv("MODEL_NAME", "stub-local")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    max_tokens: int = int(os.getenv("MAX_TOKENS", "800"))
    temperature: float = float(os.getenv("TEMPERATURE", "0.3"))

    retrieve_k: int = int(os.getenv("RETRIEVE_K", "6"))
    alpha_embed: float = float(os.getenv("ALPHA_EMBED", "0.6"))
    beta_keyword: float = float(os.getenv("BETA_KEYWORD", "0.3"))
    gamma_recency: float = float(os.getenv("GAMMA_RECENCY", "0.1"))
    max_per_domain: int = int(os.getenv("MAX_PER_DOMAIN", "2"))
    min_citations: int = int(os.getenv("MIN_CITATIONS", "2"))
    recency_halflife_days: float = float(os.getenv("RECENCY_HALFLIFE_DAYS", "10"))


settings = Settings()
