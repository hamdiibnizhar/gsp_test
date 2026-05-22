from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    paths: List[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=20)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "gsp-rag"
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
