from __future__ import annotations

import pytest

from lam.config import load_settings
from lam.controller.loop import ConversationLoop
from lam.llm.client import OllamaClient
from lam.memory.episodic import EpisodicStore
from lam.memory.state import SessionState
from lam.rag.graph_store import GraphStore
from lam.rag.vector_store import VectorStore
from lam.tools import default_tools
from lam.tools.registry import ToolRegistry

pytestmark = pytest.mark.integration


def test_full_pipeline_calculator_tool_call() -> None:
    """RAG/그래프/메모리/검증기가 모두 연결된 상태에서 툴콜링이 끝까지 도는지 확인한다."""
    settings = load_settings()
    client = OllamaClient(settings)
    state = SessionState(settings.redis_url)
    episodes = EpisodicStore(settings.database_url)
    rag = VectorStore(settings.database_url, settings.ollama_host)
    graph = GraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    tools = ToolRegistry(default_tools(graph=graph))

    loop = ConversationLoop(
        client,
        tools,
        system="You are a helpful assistant. Use tools when they help answer the question.",
        session_id="pytest-e2e",
        state=state,
        episodes=episodes,
        rag=rag,
        graph=graph,
    )

    reply = loop.send("37 곱하기 59는 얼마야? 계산기 툴을 써서 정확히 계산해줘.")

    assert "2183" in reply
