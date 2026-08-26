from __future__ import annotations

from lam.config import load_settings
from lam.controller.loop import ConversationLoop
from lam.llm.client import OllamaClient
from lam.memory.episodic import EpisodicStore
from lam.memory.state import SessionState
from lam.rag.graph_store import GraphStore
from lam.rag.vector_store import VectorStore
from lam.tools import default_tools
from lam.tools.registry import ToolRegistry

SYSTEM_PROMPT = (
    "You are a helpful assistant. Use tools when they help answer the question. "
    "관련 문서를 인용할 때는 반드시 [파일명] 형식으로 출처를 표시해라."
)


def main() -> None:
    settings = load_settings()
    client = OllamaClient(settings)
    state = SessionState(settings.redis_url)
    episodes = EpisodicStore(settings.database_url)
    rag = VectorStore(settings.database_url, settings.ollama_host)
    graph = GraphStore(
        settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
    )
    tools = ToolRegistry(default_tools(graph=graph))
    loop = ConversationLoop(
        client,
        tools,
        system=SYSTEM_PROMPT,
        session_id=settings.session_id,
        state=state,
        episodes=episodes,
        rag=rag,
        graph=graph,
    )

    print(f"LAM 프로토타입 대화 시작 (세션: {settings.session_id}, 종료: exit/quit)")
    while True:
        try:
            user_input = input("you> ").strip()
        except EOFError:
            break
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue
        reply = loop.send(user_input)
        print(f"lam> {reply}")


if __name__ == "__main__":
    main()
