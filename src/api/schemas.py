from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    paths: List[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=20)
