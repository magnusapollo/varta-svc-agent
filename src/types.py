from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class ChatFilters(BaseModel):
    topic: Optional[List[str]] = None
    since: Optional[str] = None  # ISO date or ISO8601 period

class ChatRequest(BaseModel):
    conversationId: Optional[str] = None
    message: str
    filters: Optional[ChatFilters] = None
    mode: Optional[str] = Field(default="summary", pattern="^(summary|timeline|pros-cons|for-builders)$")

class RetrieveRequest(BaseModel):
    query: str
    k: int = 5
    filters: Optional[ChatFilters] = None
