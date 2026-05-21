from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Chunk:
    document: str
    chunk_id: str
    text: str
    embedding: List[float]

    def to_dict(self) -> dict:
        return {
            "document": self.document,
            "chunk_id": self.chunk_id,
            "text": self.text,
            "embedding": self.embedding,
        }


@dataclass
class MetricsStore:
    total_documents: int = 0
    total_chunks: int = 0
    total_queries: int = 0
    total_retrieval_latency_ms: float = 0.0
    cache_hits: int = 0

    def to_dict(self) -> dict:
        average_latency = (
            self.total_retrieval_latency_ms / self.total_queries
            if self.total_queries > 0
            else 0.0
        )
        cache_hit_rate = self.cache_hits / self.total_queries if self.total_queries > 0 else 0.0
        return {
            "total_documents": self.total_documents,
            "total_chunks": self.total_chunks,
            "average_retrieval_latency_ms": round(average_latency, 2),
            "cache_hit_rate": round(cache_hit_rate, 4),
        }
