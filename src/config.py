from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class AppConfig:
    chunk_size: int = 120
    chunk_overlap: int = 30
    embed_dim: int = 384
    ollama_base_url: str = "http://10.30.50.2:11434"
    ollama_model: str = "gpt-oss:20b"
    ollama_timeout_seconds: float = 20.0
    confidence_threshold: float = 0.15
    storage_dir: str = str(PROJECT_ROOT / "data")
    pgvector_dsn: str = "postgresql://gsp:gsp@localhost:5432/gsp"
    pgvector_table: str = "rag_chunks"
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = True
    redis_cache_prefix: str = "gsp:query-cache"
    redis_cache_ttl_seconds: int = 0
    ocr_enabled: bool = True
    ocr_min_text_chars: int = 80
    ocr_dpi: int = 200
    ocr_lang: str = "eng"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_ingest_topic: str = "rag.document.ingest"
    kafka_retry_topic: str = "rag.document.ingest.retry"
    kafka_dlq_topic: str = "rag.document.ingest.dlq"
    kafka_group_id: str = "rag-ingester"
    watch_directory: str = str(PROJECT_ROOT / "incoming_docs")
    processed_directory: str = str(PROJECT_ROOT / "processed_docs")
    failed_directory: str = str(PROJECT_ROOT / "failed_docs")
    watcher_poll_seconds: float = 2.0
    watcher_stable_seconds: float = 3.0
    ingest_max_retries: int = 3

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            chunk_size=int(os.getenv("RAG_CHUNK_SIZE", str(cls.chunk_size))),
            chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", str(cls.chunk_overlap))),
            embed_dim=int(os.getenv("RAG_EMBED_DIM", str(cls.embed_dim))),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", cls.ollama_base_url),
            ollama_model=os.getenv("OLLAMA_MODEL", cls.ollama_model),
            ollama_timeout_seconds=float(
                os.getenv("OLLAMA_TIMEOUT_SECONDS", str(cls.ollama_timeout_seconds))
            ),
            confidence_threshold=float(
                os.getenv("RAG_CONFIDENCE_THRESHOLD", str(cls.confidence_threshold))
            ),
            storage_dir=os.getenv("RAG_STORAGE_DIR", cls.storage_dir),
            pgvector_dsn=os.getenv("PGVECTOR_DSN", cls.pgvector_dsn),
            pgvector_table=os.getenv("PGVECTOR_TABLE", cls.pgvector_table),
            redis_url=os.getenv("REDIS_URL", cls.redis_url),
            redis_enabled=os.getenv("REDIS_ENABLED", "true").lower() in {"1", "true", "yes"},
            redis_cache_prefix=os.getenv("REDIS_CACHE_PREFIX", cls.redis_cache_prefix),
            redis_cache_ttl_seconds=int(
                os.getenv("REDIS_CACHE_TTL_SECONDS", str(cls.redis_cache_ttl_seconds))
            ),
            ocr_enabled=os.getenv("OCR_ENABLED", "true").lower() in {"1", "true", "yes"},
            ocr_min_text_chars=int(
                os.getenv("OCR_MIN_TEXT_CHARS", str(cls.ocr_min_text_chars))
            ),
            ocr_dpi=int(os.getenv("OCR_DPI", str(cls.ocr_dpi))),
            ocr_lang=os.getenv("OCR_LANG", cls.ocr_lang),
            kafka_bootstrap_servers=os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS", cls.kafka_bootstrap_servers
            ),
            kafka_ingest_topic=os.getenv("KAFKA_INGEST_TOPIC", cls.kafka_ingest_topic),
            kafka_retry_topic=os.getenv("KAFKA_RETRY_TOPIC", cls.kafka_retry_topic),
            kafka_dlq_topic=os.getenv("KAFKA_DLQ_TOPIC", cls.kafka_dlq_topic),
            kafka_group_id=os.getenv("KAFKA_GROUP_ID", cls.kafka_group_id),
            watch_directory=os.getenv("WATCH_DIRECTORY", cls.watch_directory),
            processed_directory=os.getenv(
                "PROCESSED_DIRECTORY", cls.processed_directory
            ),
            failed_directory=os.getenv("FAILED_DIRECTORY", cls.failed_directory),
            watcher_poll_seconds=float(
                os.getenv("WATCHER_POLL_SECONDS", str(cls.watcher_poll_seconds))
            ),
            watcher_stable_seconds=float(
                os.getenv("WATCHER_STABLE_SECONDS", str(cls.watcher_stable_seconds))
            ),
            ingest_max_retries=int(
                os.getenv("INGEST_MAX_RETRIES", str(cls.ingest_max_retries))
            ),
        )
