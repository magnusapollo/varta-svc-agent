from typing import Literal

from pydantic import BaseModel, Field


class ChatFilters(BaseModel):
    topic: list[str] | None = None
    since: str | None = None  # ISO date or ISO8601 period


class ChatRequest(BaseModel):
    conversationId: str | None = None
    message: str
    role: Literal["user", "system"]
    filters: ChatFilters | None = None
    mode: str | None = Field(
        default="summary", pattern="^(summary|timeline|pros-cons|for-builders)$"
    )


class RetrieveRequest(BaseModel):
    query: str
    k: int = 5
    filters: ChatFilters | None = None
