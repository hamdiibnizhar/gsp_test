# Scalable Ingestion Design

## Diagram Streaming
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

## Peran Message Broker
- Kafka sebagai buffer untuk decouple producer-consumer.
- Menjaga query service tetap berjalan saat ingestion mencapai puncak.

## Batch vs Streaming
- Streaming untuk near-real-time updates tiap menit, khusus untuk menjalankan data penting.
- Micro-batch (mis. 30-60 detik) untuk efisiensi embed/index write, mengurangi cost

## Strategi Index Update
- Upsert berdasarkan `doc_id` + `chunk_id` + `embedding_version`.
- Gunakan event delete untuk dokumen yang dicabut.

## Backpressure
- Auto-scale worker berdasarkan lag.
- Limit concurrency parser/embedding.
- Prioritaskan query traffic dengan pool terpisah.

## Failure Handling
- Retry eksponensial untuk error sementara.
- DLQ untuk dokumen korup/unsupported.
- Idempotency key mencegah duplicate indexing.

## Observability
- Kafka lag, ingestion TPS, error ratio, DLQ count.
- Indexing latency end-to-end.
- Consistency checker antara metadata DB dan vector DB.

## Menjaga Consistency Metadata vs Vector
- dengan membuatnya sebagai cluster dan terdistribusi
- dengan Two-phase upsert: tulis metadata `pending`, lalu commit vector, lalu `active`.
- Scheduled reconciliation job untuk mismatch repair.

## Re-index saat Embedding Model Berubah
- Terapkan `embedding_version`
- Re-index blue/green: bangun index baru paralel, swap temporary saat selesai.
- Jalankan background backfill agar query tidak downtime
