from __future__ import annotations

from dataclasses import dataclass

import psycopg
from ollama import Client
from pgvector import Vector
from pgvector.psycopg import register_vector

EMBEDDING_MODEL = "bge-m3"
EMBEDDING_DIM = 1024

CREATE_EXTENSION_SQL = "CREATE EXTENSION IF NOT EXISTS vector;"
CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector({EMBEDDING_DIM}) NOT NULL
);
"""
INSERT_SQL = "INSERT INTO knowledge_chunks (source, content, embedding) VALUES (%s, %s, %s);"
SEARCH_SQL = """
SELECT source, content
FROM knowledge_chunks
ORDER BY embedding <=> %s
LIMIT %s;
"""
DELETE_BY_SOURCE_SQL = "DELETE FROM knowledge_chunks WHERE source = %s;"

DEFAULT_TOP_K = 3


@dataclass(frozen=True)
class RetrievedChunk:
    source: str
    content: str


class VectorStore:
    def __init__(self, dsn: str, ollama_host: str) -> None:
        self._dsn = dsn
        self._embed_client = Client(host=ollama_host)
        with psycopg.connect(self._dsn) as conn:
            conn.execute(CREATE_EXTENSION_SQL)
            register_vector(conn)
            conn.execute(CREATE_TABLE_SQL)
            conn.commit()

    def _embed(self, text: str) -> Vector:
        response = self._embed_client.embed(model=EMBEDDING_MODEL, input=text)
        return Vector(list(response.embeddings[0]))

    def replace_document(self, source: str, chunks: list[str]) -> None:
        with psycopg.connect(self._dsn) as conn:
            register_vector(conn)
            conn.execute(DELETE_BY_SOURCE_SQL, (source,))
            for chunk in chunks:
                embedding = self._embed(chunk)
                conn.execute(INSERT_SQL, (source, chunk, embedding))
            conn.commit()

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[RetrievedChunk]:
        embedding = self._embed(query)
        with psycopg.connect(self._dsn) as conn:
            register_vector(conn)
            rows = conn.execute(SEARCH_SQL, (embedding, top_k)).fetchall()
        return [RetrievedChunk(source=row[0], content=row[1]) for row in rows]
