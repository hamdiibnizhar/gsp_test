from fastapi.testclient import TestClient

from src.api.app import create_app
from src.config import AppConfig


def build_test_app():
    config = AppConfig(
        storage_dir="/tmp/gsp-test-data",
        milvus_uri="/tmp/gsp-test-data/milvus.db",
        redis_enabled=False,
        watch_directory="/tmp/gsp-test-watch",
        processed_directory="/tmp/gsp-test-processed",
        failed_directory="/tmp/gsp-test-failed",
    )
    return create_app(config=config)


def test_health():
    client = TestClient(build_test_app())
    res = client.get("/health")
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] == "ok"
    assert payload["ollama_base_url"] == "http://10.30.50.2:11434"
    assert payload["ollama_model"] == "gpt-oss:20b"
    assert payload["vector_store"] == "milvus"


def test_ingest_and_query():
    client = TestClient(build_test_app())

    ingest = client.post("/ingest", json={"paths": ["sample_docs/company_policy.md"]})
    assert ingest.status_code == 200
    payload = ingest.json()
    assert payload["status"] == "success"
    assert payload["documents_indexed"] >= 1
    assert payload["chunks_created"] >= 1

    query = client.post(
        "/query",
        json={"question": "berapa lama retensi data transaksi pelanggan?", "top_k": 3},
    )
    assert query.status_code == 200
    data = query.json()
    assert "answer" in data
    assert "sources" in data
    assert data["fallback_used"] in [True, False]


def test_metrics():
    client = TestClient(build_test_app())
    res = client.get("/metrics")
    assert res.status_code == 200
    metrics = res.json()
    assert "total_documents" in metrics
    assert "total_chunks" in metrics
    assert "average_retrieval_latency_ms" in metrics
    assert "cache_hit_rate" in metrics
