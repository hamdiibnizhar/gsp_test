from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, List, Tuple



from src.rag.models import Chunk


class DocumentCatalogStore:
    def __init__(self, storage_dir: str):
        self.root = Path(storage_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.catalog_path = self.root / "documents.json"

    def load(self) -> Dict[str, int]:
        if not self.catalog_path.exists():
            return {}

        payload = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        return {str(key): int(value) for key, value in payload.get("documents", {}).items()}

    def save(self, documents: Dict[str, int]) -> None:
        payload = {"documents": documents}
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.root,
            delete=False,
            suffix=".json",
        ) as temp_file:
            json.dump(payload, temp_file)
            temp_path = Path(temp_file.name)
        temp_path.replace(self.catalog_path)


class PGVectorStore:
    def __init__(self, *, dsn: str, table_name: str, dimension: int):
        try:
            import psycopg2
            from pgvector.psycopg2 import register_vector
        except ImportError as exc:  # pragma: no cover
            raise ValueError("PGVector support unavailable. Install `psycopg2-binary` and `pgvector`.") from exc

        self._dsn = dsn
        self.table_name = table_name
        self.dimension = dimension
        self._conn = psycopg2.connect(dsn)
        # Extension must exist before register_vector looks up the OID
        with self._conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        self._conn.commit()
        register_vector(self._conn)
        self._ensure_table()

    def _connection(self):
        import psycopg2
        from pgvector.psycopg2 import register_vector
        if self._conn.closed:
            self._conn = psycopg2.connect(self._dsn)
            with self._conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            self._conn.commit()
            register_vector(self._conn)
        return self._conn

    def _ensure_table(self) -> None:
        from psycopg2 import sql
        conn = self._connection()
        tbl = sql.Identifier(self.table_name)
        with conn.cursor() as cur:
            cur.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {tbl} (
                    id BIGSERIAL PRIMARY KEY,
                    document VARCHAR(512) NOT NULL,
                    chunk_id VARCHAR(128) NOT NULL,
                    text TEXT NOT NULL,
                    embedding vector({dim}) NOT NULL
                )
            """).format(tbl=tbl, dim=sql.SQL(str(self.dimension))))
            cur.execute(sql.SQL("""
                CREATE INDEX IF NOT EXISTS {idx} ON {tbl} USING hnsw (embedding vector_cosine_ops)
            """).format(idx=sql.Identifier(f"{self.table_name}_emb_idx"), tbl=tbl))
            cur.execute(sql.SQL("""
                CREATE INDEX IF NOT EXISTS {idx} ON {tbl} (document)
            """).format(idx=sql.Identifier(f"{self.table_name}_doc_idx"), tbl=tbl))
        conn.commit()

    def replace_document(self, document: str, chunks: List[Chunk]) -> None:
        from psycopg2 import sql
        conn = self._connection()
        tbl = sql.Identifier(self.table_name)
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("DELETE FROM {tbl} WHERE document = %s").format(tbl=tbl),
                (document,),
            )
            if chunks:
                cur.executemany(
                    sql.SQL(
                        "INSERT INTO {tbl} (document, chunk_id, text, embedding) VALUES (%s, %s, %s, %s)"
                    ).format(tbl=tbl),
                    [(c.document, c.chunk_id, c.text, c.embedding) for c in chunks],
                )
        conn.commit()

    def search(self, query_embedding: List[float], top_k: int) -> List[Tuple[Chunk, float]]:
        from psycopg2 import sql
        conn = self._connection()
        tbl = sql.Identifier(self.table_name)
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("""
                    SELECT document, chunk_id, text,
                           1 - (embedding <=> %s::vector) AS score
                    FROM {tbl}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """).format(tbl=tbl),
                (query_embedding, query_embedding, top_k),
            )
            rows = cur.fetchall()
        return [
            (Chunk(document=r[0], chunk_id=r[1], text=r[2], embedding=[]), float(r[3]))
            for r in rows
        ]

    def total_chunks(self) -> int:
        from psycopg2 import sql
        conn = self._connection()
        with conn.cursor() as cur:
            cur.execute(sql.SQL("SELECT COUNT(*) FROM {tbl}").format(tbl=sql.Identifier(self.table_name)))
            return cur.fetchone()[0]
