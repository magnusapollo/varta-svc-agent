from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    USE_MOCKS: bool = os.getenv("USE_MOCKS", "true").lower() == "true"
    CORE_API_BASE: str = os.getenv("CORE_API_BASE", "http://localhost:8080/api/v1")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "stub-local")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "800"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.3"))

    RETRIEVE_K: int = int(os.getenv("RETRIEVE_K", "6"))
    ALPHA_EMBED: float = float(os.getenv("ALPHA_EMBED", "0.6"))
    BETA_KEYWORD: float = float(os.getenv("BETA_KEYWORD", "0.3"))
    GAMMA_RECENCY: float = float(os.getenv("GAMMA_RECENCY", "0.1"))
    MAX_PER_DOMAIN: int = int(os.getenv("MAX_PER_DOMAIN", "2"))
    MIN_CITATIONS: int = int(os.getenv("MIN_CITATIONS", "2"))
    RECENCY_HALFLIFE_DAYS: float = float(os.getenv("RECENCY_HALFLIFE_DAYS", "10"))

settings = Settings()
