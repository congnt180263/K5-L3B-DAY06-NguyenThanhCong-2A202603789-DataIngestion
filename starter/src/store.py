"""Store and search vectors using PostgreSQL + pgvector."""
import json
from typing import Any
import psycopg
from .models import Chunk


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        """Retain connection settings and validate model dimensions."""
        self.database_url = database_url
        self.dimensions = int(dimensions)
        if self.dimensions <= 0:
            raise ValueError(f"Invalid dimensions: {self.dimensions}")

    def create_schema(self) -> None:
        """Create extension and chunks table with vector column and metadata."""
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                # Enable pgvector extension
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

                # Check if table already exists with mismatched dimension
                cur.execute("SELECT to_regclass('chunks');")
                if cur.fetchone()[0] is not None:
                    cur.execute(
                        """
                        SELECT atttypmod 
                        FROM pg_attribute 
                        WHERE attrelid = 'chunks'::regclass AND attname = 'embedding';
                        """
                    )
                    row = cur.fetchone()
                    if row and row[0] != self.dimensions:
                        cur.execute("DROP TABLE IF EXISTS chunks CASCADE;")

                # Create schema for chunk storage
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS chunks (
                        chunk_id TEXT NOT NULL,
                        strategy TEXT NOT NULL,
                        document_id TEXT NOT NULL,
                        source TEXT NOT NULL,
                        page INTEGER NOT NULL,
                        section TEXT,
                        text TEXT NOT NULL,
                        metadata JSONB,
                        embedding vector({self.dimensions}),
                        PRIMARY KEY (chunk_id, strategy)
                    );
                    CREATE INDEX IF NOT EXISTS idx_chunks_strategy ON chunks(strategy);
                    CREATE INDEX IF NOT EXISTS idx_chunks_section ON chunks(section);
                    """
                )
            conn.commit()

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Validate lengths/dimensions and write without duplicates.

        Removes obsolete chunks for the given strategy first (idempotent re-ingestion).
        """
        if len(chunks) != len(vectors):
            raise ValueError(f"Mismatch between chunks ({len(chunks)}) and vectors ({len(vectors)})")

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                # Clean up existing chunks for this strategy to avoid duplicates
                cur.execute("DELETE FROM chunks WHERE strategy = %s;", (strategy,))

                # Insert chunks with vectors
                insert_sql = """
                    INSERT INTO chunks (
                        chunk_id, strategy, document_id, source, page, section, text, metadata, embedding
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (chunk_id, strategy) DO UPDATE SET
                        text = EXCLUDED.text,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding;
                """
                records = []
                for chunk, vec in zip(chunks, vectors):
                    if len(vec) != self.dimensions:
                        raise ValueError(f"Vector dimension {len(vec)} != store dimension {self.dimensions}")
                    
                    vec_str = "[" + ",".join(str(v) for v in vec) + "]"
                    sec = chunk.metadata.get("section")
                    meta_json = json.dumps(chunk.metadata, ensure_ascii=False)
                    records.append(
                        (
                            chunk.chunk_id,
                            strategy,
                            chunk.document_id,
                            chunk.source,
                            chunk.page,
                            sec,
                            chunk.text,
                            meta_json,
                            vec_str,
                        )
                    )

                cur.executemany(insert_sql, records)
            conn.commit()

    def search(
        self,
        strategy: str,
        query_vector: list[float],
        top_k: int = 3,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Filter metadata in SQL, rank by cosine distance (<=>), and return top-k."""
        if len(query_vector) != self.dimensions:
            raise ValueError(f"Query vector dimension {len(query_vector)} != {self.dimensions}")

        vec_str = "[" + ",".join(str(v) for v in query_vector) + "]"

        query_sql = """
            SELECT
                chunk_id,
                document_id,
                source,
                page,
                section,
                text,
                metadata,
                1 - (embedding <=> %s::vector) AS similarity
            FROM chunks
            WHERE strategy = %s
        """
        params: list[Any] = [vec_str, strategy]

        if filters:
            for k, v in filters.items():
                if k == "section":
                    query_sql += " AND section = %s"
                    params.append(v)
                else:
                    query_sql += " AND metadata->>%s = %s"
                    params.extend([k, str(v)])

        query_sql += " ORDER BY embedding <=> %s::vector ASC LIMIT %s;"
        params.extend([vec_str, top_k])

        results: list[dict[str, Any]] = []
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(query_sql, params)
                for row in cur.fetchall():
                    chunk_id, doc_id, source, page, section, text, meta, sim = row
                    results.append(
                        {
                            "chunk_id": chunk_id,
                            "document_id": doc_id,
                            "source": source,
                            "page": page,
                            "section": section,
                            "text": text,
                            "metadata": meta if isinstance(meta, dict) else json.loads(meta or "{}"),
                            "score": float(sim),
                        }
                    )

        return results
