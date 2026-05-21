from __future__ import annotations

import logging
import time
from typing import List, Tuple

from src.config import AppConfig
from src.document_processor import DocumentProcessor
from src.rag.cache import RedisResponseCache
from src.rag.embeddings import HashingEmbedder
from src.rag.llm import OllamaClient
from src.rag.models import Chunk, MetricsStore
from src.rag.storage import DocumentCatalogStore, PGVectorStore


LOGGER = logging.getLogger("local_rag")


class RAGService:
    def __init__(self, config: AppConfig):
        self.config = config
        self.embedder = HashingEmbedder(dim=config.embed_dim)
        self.processor = DocumentProcessor(
            chunk_size=config.chunk_size,
            overlap=config.chunk_overlap,
            ocr_enabled=config.ocr_enabled,
            ocr_min_text_chars=config.ocr_min_text_chars,
            ocr_dpi=config.ocr_dpi,
            ocr_lang=config.ocr_lang,
        )
        self.store = PGVectorStore(
            dsn=config.pgvector_dsn,
            table_name=config.pgvector_table,
            dimension=config.embed_dim,
        )
        self.metrics = MetricsStore()
        self.cache = RedisResponseCache(
            redis_url=config.redis_url,
            key_prefix=config.redis_cache_prefix,
            ttl_seconds=config.redis_cache_ttl_seconds,
            enabled=config.redis_enabled,
        )
        self.catalog_store = DocumentCatalogStore(config.storage_dir)
        self.documents = self.catalog_store.load()
        self.ollama = OllamaClient(
            base_url=config.ollama_base_url,
            model=config.ollama_model,
            timeout_seconds=config.ollama_timeout_seconds,
        )
        self.sync_from_storage(force=True)

    def ingest(self, docs: List[Tuple[str, str]]) -> dict:
        total_chunks = 0
        indexed_docs = 0

        for doc_name, raw_text in docs:
            text = self.processor.clean(raw_text)
            if not text:
                LOGGER.warning("Skipping empty document: %s", doc_name)
                continue

            chunk_items = self.processor.chunk(doc_name, text)
            chunks = [
                Chunk(
                    document=doc_name,
                    chunk_id=chunk_id,
                    text=chunk_text,
                    embedding=self.embedder.embed(chunk_text),
                )
                for chunk_id, chunk_text in chunk_items
            ]
            self.store.replace_document(doc_name, chunks)
            self.documents[doc_name] = len(chunks)
            indexed_docs += 1
            total_chunks += len(chunks)

        self.catalog_store.save(self.documents)
        self._refresh_metrics()
        self.cache.clear()

        return {
            "status": "success",
            "documents_indexed": indexed_docs,
            "chunks_created": total_chunks,
        }

    def query(self, question: str, top_k: int = 5) -> dict:
        if not question.strip():
            raise ValueError("Question must not be empty")

        self.sync_from_storage()
        cache_key = f"{question.strip().lower()}::{top_k}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            self.metrics.total_queries += 1
            self.metrics.cache_hits += 1
            return cached

        start = time.perf_counter()
        query_embedding = self.embedder.embed(question)
        candidates = self._retrieve(query_embedding, top_k=top_k)
        latency_ms = (time.perf_counter() - start) * 1000

        self.metrics.total_queries += 1
        self.metrics.total_retrieval_latency_ms += latency_ms

        if not candidates:
            response = {
                "answer": "Saya belum menemukan jawaban pada dokumen yang tersedia.",
                "sources": [],
                "confidence": 0.0,
                "fallback_used": True,
            }
            self.cache.set(cache_key, response)
            return response

        top_score = max(score for _, score in candidates)
        confidence = max(0.0, min(1.0, top_score))
        sources = [
            {
                "document": chunk.document,
                "chunk_id": chunk.chunk_id,
                "score": round(score, 4),
            }
            for chunk, score in candidates
        ]

        if top_score < self.config.confidence_threshold:
            response = {
                "answer": "Jawaban tidak ditemukan dengan confidence memadai pada dokumen internal.",
                "sources": sources,
                "confidence": round(confidence, 4),
                "fallback_used": True,
            }
            self.cache.set(cache_key, response)
            return response

        context = "\n\n".join(chunk.text for chunk, _ in candidates[:2])
        answer = self.ollama.generate_answer(question=question, context=context)
        if answer is None:
            answer = self._build_grounded_fallback(context)

        response = {
            "answer": answer,
            "sources": sources,
            "confidence": round(confidence, 4),
            "fallback_used": False,
        }
        self.cache.set(cache_key, response)
        return response

    def _retrieve(self, query_embedding: List[float], top_k: int) -> List[Tuple[Chunk, float]]:
        return self.store.search(query_embedding, top_k=top_k)

    def _build_grounded_fallback(self, context: str) -> str:
        return f"Berdasarkan dokumen internal, konteks relevan: {context[:500]}"

    def sync_from_storage(self, force: bool = False) -> None:
        if force:
            self.documents = self.catalog_store.load()
        self._refresh_metrics()

    def _refresh_metrics(self) -> None:
        self.metrics.total_documents = len(self.documents)
        self.metrics.total_chunks = self.store.total_chunks()
