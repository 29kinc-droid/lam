from __future__ import annotations

import psycopg

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS episodes (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tool_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

INSERT_SQL = """
INSERT INTO episodes (session_id, role, content, tool_name)
VALUES (%s, %s, %s, %s);
"""


class EpisodicStore:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        with psycopg.connect(self._dsn) as conn:
            conn.execute(CREATE_TABLE_SQL)
            conn.commit()

    def record(
        self, session_id: str, role: str, content: str, tool_name: str | None = None
    ) -> None:
        with psycopg.connect(self._dsn) as conn:
            conn.execute(INSERT_SQL, (session_id, role, content, tool_name))
            conn.commit()
