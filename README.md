# Local Agentic RAG API

Sistem RAG (Retrieval-Augmented Generation) lokal untuk ingest dokumen internal, retrieval berbasis vector, dan query API dengan citation, confidence score, fallback, serta metrik observability.

**Stack:** FastAPI · PostgreSQL + pgvector · Redis · Kafka · Ollama · Tesseract OCR

---

## Arsitektur Ringkas

```mermaid
flowchart TD
    subgraph kafka_cluster["kafka cluster"]
        kafka1_leader --> kafka2 -->Kafka3 --> kafka_2n+1
    end
    subgraph DWH["Data Warehouse"]
        Broker_DWH["keaep Alived Leader"] --> Worker1 -->worker2 --> Worker_2n+1
    end
    subgraph DL["Data Lake"]
        Broker_DL["keaep Alived Leader"] --> Node1 -->Node2 --> Node_2n+1
    end

    Data_Source --> API--> Drop[Drop Folder] <--> DL["Input folder"]
    File --> Drop
    Drop --> Scanner[Scan folder setiap 2 detik]
    Scanner --> OCR --> Ingestion

    Scanner --> Ingestion[Ingestion Service] --> kafka_cluster
    kafka_cluster --> Doc_parse["Document Parser"]
    Doc_parse --> Chuncking --> Embedding --> Vector[Vector DB PgVector Ext] --> DWH


    Vector --> Retriever

    Retriever --> cache[Redis]
    cache --> Response
    Query[User Query] --> API_Layer[Query API]
    API_Layer --> Retriever[Retriever]
    Retriever --> Rerank[Rerank/Score]
    Rerank --> LLM
    LLM --> Ans_Builder[Grounded Answer Builder]
    Ans_Builder --> Response[Response + Citations + Confidence]
    API_Layer --> Cache[Cache/Session]
    API_Layer --> Metrics[Metrics + Logging]
```

---

## 1. Cara Menjalankan

### Docker (disarankan)

```bash
cd GSP
docker compose down -v        # bersihkan volume lama jika ada
docker compose up --build
```

Service aktif di `http://localhost:8000`. Semua container (postgres, redis, kafka, rag-api, folder-watcher, kafka-ingester) naik otomatis.

> **Catatan:** `gsp-rag-api` menunggu postgres healthy sebelum start. Postgres biasanya siap dalam 10-15 detik.

---

## 2. Struktur Direktori

```
GSP/
├── incoming_docs/     # drop file di sini untuk auto-ingest via Kafka
├── processed_docs/    # file berhasil di-index dipindahkan ke sini
├── failed_docs/       # file gagal setelah retry habis
├── data/
│   └── documents.json # metadata catalog (jumlah chunk per dokumen)
├── sample_docs/       # contoh dokumen untuk testing
├── src/
│   ├── api/           # FastAPI routes & schemas
│   ├── rag/           # RAGService, PGVectorStore, embeddings, cache
│   ├── streaming/     # Kafka producer, consumer, watcher
│   ├── document_processor/ # parse PDF/MD/TXT + OCR
│   └── config.py
└── docker-compose.yml
```

---

## 3. Endpoint API

### `GET /health`
Cek status service.

```bash
curl http://localhost:8000/health
```

### `GET /metrics`
Metrik operasional.

```bash
curl http://localhost:8000/metrics
```

Response:
```json
{
  "total_documents": 3,
  "total_chunks": 42,
  "average_retrieval_latency_ms": 12.5,
  "cache_hit_rate": 0.75
}
```

### `POST /ingest`

**Upload file langsung:**
```bash
curl -X POST http://localhost:8000/ingest \
  -F "file=@/path/ke/dokumen.pdf"
```

**Via path JSON (path di dalam container):**
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"paths": ["sample_docs/company_policy.md"]}'
```

Response:
```json
{
  "status": "success",
  "documents_indexed": 1,
  "chunks_created": 12
}
```

### `POST /query`

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Apa kebijakan retensi data?", "top_k": 5}'
```

Response:
```json
{
  "answer": "Berdasarkan dokumen internal...",
  "sources": [
    {"document": "company_policy.md", "chunk_id": "company_policy_001", "score": 0.72}
  ],
  "confidence": 0.72,
  "fallback_used": false
}
```

> Jika Ollama tidak bisa diakses, `answer` berisi cuplikan konteks dokumen (fallback lokal) dan `fallback_used: true`.

---

## 4. Ingest via Folder (Kafka Streaming)

Cara paling mudah — tinggal copy file:

```bash
cp dokumen.pdf GSP/incoming_docs/
```

Alur otomatis:
1. `folder-watcher` scan setiap 2 detik, tunggu file stabil 3 detik
2. Publish event ke Kafka topic `rag.document.ingest`
3. `kafka-ingester` consume, parse, chunk, embed, simpan ke PGVector
4. File berhasil → `processed_docs/` | Gagal setelah 3x retry → `failed_docs/` + DLQ

---

## 5. Konfigurasi `.env`

| Variable | Default | Keterangan |
|---|---|---|
| `PGVECTOR_DSN` | `postgresql://gsp:gsp@postgres:5432/gsp` | Koneksi PostgreSQL pgvector |
| `PGVECTOR_TABLE` | `rag_chunks` | Nama tabel vector |
| `OLLAMA_BASE_URL` | `http://10.30.50.2:11434` | Endpoint Ollama LLM |
| `OLLAMA_MODEL` | `gpt-oss:20b` | Model yang digunakan |
| `OLLAMA_TIMEOUT_SECONDS` | `20` | Timeout request ke Ollama |
| `REDIS_URL` | `redis://redis:6379/0` | Koneksi Redis cache |
| `REDIS_ENABLED` | `true` | Aktifkan/nonaktifkan cache |
| `REDIS_CACHE_TTL_SECONDS` | `0` | TTL cache (0 = tidak expire) |
| `RAG_CHUNK_SIZE` | `120` | Ukuran chunk (kata) |
| `RAG_CHUNK_OVERLAP` | `30` | Overlap antar chunk (kata) |
| `RAG_EMBED_DIM` | `384` | Dimensi embedding |
| `RAG_CONFIDENCE_THRESHOLD` | `0.15` | Minimum score untuk jawaban |
| `OCR_ENABLED` | `true` | OCR untuk PDF scan |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka broker |
| `INGEST_MAX_RETRIES` | `3` | Jumlah retry sebelum DLQ |
| `WATCHER_POLL_SECONDS` | `2` | Interval scan folder |
| `WATCHER_STABLE_SECONDS` | `3` | Waktu tunggu file stabil |

---

## 6. Menjalankan Test

```bash
cd GSP
pytest -q
```

---

## 7. Dependency Utama

| Package | Versi | Peran |
|---|---|---|
| `fastapi` | 0.115.2 | REST API framework |
| `uvicorn` | 0.30.6 | ASGI server |
| `psycopg2-binary` | 2.9.9 | PostgreSQL adapter |
| `pgvector` | 0.3.6 | pgvector type adapter |
| `redis` | 6.1.1 | Response cache |
| `kafka-python` | 2.2.15 | Kafka producer/consumer |
| `pypdf` | 5.5.0 | Parse PDF |
| `pdf2image` | 1.17.0 | PDF ke image untuk OCR |
| `pytesseract` | 0.3.13 | OCR engine |
| `pydantic` | 2.9.2 | Schema validation |
| `python-dotenv` | 1.2.2 | Load `.env` |

---

## 8. Trade-off Teknis

- **Hashing embedder** dipilih agar lokal, ringan, tanpa dependency model besar. Konsekuensi: kualitas semantic retrieval di bawah transformer embedding.
- **pgvector** menggantikan Milvus karena lebih ringan, native arm64, dan tidak membutuhkan layanan tambahan (etcd, minio).
- **HNSW index** di pgvector untuk approximate nearest neighbor search dengan metrik cosine.
- Jika Ollama tidak reachable, sistem fallback ke grounded local answer dari konteks retrieval.

---

## 9. Limitasi

- Embedding berbasis hashing — bukan semantic transformer.
- Belum ada reranker model-based.
- Single-node PostgreSQL — untuk multi-writer gunakan pgvector dengan connection pooler (PgBouncer) atau migrasi ke distributed setup.
