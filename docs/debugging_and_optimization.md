# Debugging and Optimization

## 1) Retrieval tidak relevan
- Tuning chunk size/overlap (contoh 80/20, 150/30) lalu ukur recall.
- Ganti embedding model ke model semantic lebih kuat (mis. `bge-small`, `e5-small`).
- Tambahkan hybrid search: lexical BM25 + vector score fusion.
- Tambahkan reranker cross-encoder untuk top-20 menjadi top-5.

## 2) Jawaban meyakinkan tapi tidak ada di dokumen
- Citation enforcement: response wajib mengandung source chunk.
- Confidence gate: jika skor retrieval rendah, fallback/no-answer.
- Prompt/template grounding: jawaban harus hanya dari konteks.
- Tambahkan answer verifier sederhana berbasis entailment check.

## 3) Latency naik dari 1s ke 8s
- Gunakan ANN index (HNSW/IVF) di Milvus/FAISS.
- Cache query populer (Redis).
- Batching embedding query/document.
- Asynchronous ingestion + read/write separation.
- Profiling per-stage (parse, embed, retrieve, generate).

## 4) Local LLM boros RAM/VRAM
- Quantization (4-bit/5-bit via llama.cpp GGUF).
- Turunkan context window default.
- Gunakan model lebih kecil + speculative routing.
- Offload sebagian layer ke CPU dan aktifkan KV cache reuse.

## 5) Pertanyaan lanjutan butuh konteks percakapan
- Simpan session memory per user (Redis/postgres).
- Query rewriting berbasis history (standalone question rewrite).
- Context compression: ringkas history panjang sebelum retrieval.
- Sliding-window memory + TTL.

## Metrics Observability yang wajib
- Retrieval latency p50/p95.
- Hit rate cache.
- Confidence distribution.
- Fallback ratio.
- Ingestion throughput dan failure rate.
