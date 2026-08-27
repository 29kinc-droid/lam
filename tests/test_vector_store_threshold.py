from __future__ import annotations

import pytest

from lam.config import load_settings
from lam.rag.vector_store import VectorStore

pytestmark = pytest.mark.integration


def test_unrelated_query_returns_no_chunks() -> None:
    settings = load_settings()
    store = VectorStore(settings.database_url, settings.ollama_host)

    assert store.search("3 더하기 4는?") == []


def test_related_query_returns_matching_chunk() -> None:
    settings = load_settings()
    store = VectorStore(settings.database_url, settings.ollama_host)

    results = store.search("ReAct 루프가 뭐야?")

    assert any(r.source == "react-loop.md" for r in results)
