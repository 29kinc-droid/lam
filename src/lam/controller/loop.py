from __future__ import annotations

from typing import Any

from lam.llm.client import OllamaClient
from lam.memory.episodic import EpisodicStore
from lam.memory.state import SessionState
from lam.rag.graph_store import GraphStore
from lam.rag.vector_store import RetrievedChunk, VectorStore
from lam.tools.registry import ToolRegistry
from lam.types import Message, ToolCall
from lam.validators.input_validator import validate_tool_call
from lam.validators.output_validator import validate_output
from lam.validators.post_exec_validator import validate_citations

DEFAULT_MAX_ROUNDS = 5
DEFAULT_RAG_TOP_K = 3
MAX_ROUNDS_MESSAGE = (
    "죄송합니다, 이 요청은 최대 반복 횟수(max_rounds)를 초과해 처리하지 못했습니다."
)


class ConversationLoop:
    def __init__(
        self,
        client: OllamaClient,
        tools: ToolRegistry,
        system: str | None = None,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
        session_id: str | None = None,
        state: SessionState | None = None,
        episodes: EpisodicStore | None = None,
        rag: VectorStore | None = None,
        rag_top_k: int = DEFAULT_RAG_TOP_K,
        graph: GraphStore | None = None,
        debug: bool = False,
    ) -> None:
        self._client = client
        self._tools = tools
        self._system = system
        self._max_rounds = max_rounds
        self._session_id = session_id
        self._state = state
        self._episodes = episodes
        self._rag = rag
        self._rag_top_k = rag_top_k
        self._graph = graph
        self._debug = debug
        self._history: list[Message] = (
            state.load_history(session_id) if state and session_id else []
        )

    def _remember(self, message: Message) -> None:
        self._history.append(message)
        if self._state and self._session_id:
            self._state.append_message(self._session_id, message)
        if self._episodes and self._session_id:
            self._episodes.record(
                self._session_id, message.role, message.content, message.tool_name
            )

    def _compose_system(
        self, rag_chunks: list[RetrievedChunk], graph_text: str | None
    ) -> str | None:
        blocks: list[str] = []

        if rag_chunks:
            context = "\n\n".join(f"[{c.source}]\n{c.content}" for c in rag_chunks)
            blocks.append(f"다음은 참고할 수 있는 관련 문서 내용입니다:\n{context}")

        if graph_text:
            blocks.append(f"다음은 지식그래프에서 검색된 관련 사실입니다:\n{graph_text}")

        if not blocks:
            return self._system

        combined = "\n\n".join(blocks)
        return f"{self._system}\n\n{combined}" if self._system else combined

    def _validate_final_response(
        self, response_text: str, rag_chunks: list[RetrievedChunk]
    ) -> list[str]:
        if not rag_chunks:
            return []

        issues = validate_citations(response_text, {c.source for c in rag_chunks})

        evidence = "\n\n".join(c.content for c in rag_chunks)
        output_issue = validate_output(self._client, response_text, evidence)
        if output_issue:
            issues.append(output_issue)

        return issues

    def _debug_print_turn_start(self, user_input: str, system: str | None) -> None:
        print("\n========== [DEBUG] 새 턴 ==========")
        print(f"[사용자 입력]\n{user_input}")
        print(f"\n[이번 턴 시스템 프롬프트 (RAG/그래프 컨텍스트 포함)]\n{system or '(없음)'}")
        print("====================================")

    def _debug_print_round(self, round_index: int, new_messages: list[Message]) -> None:
        print(
            f"\n----- [DEBUG] round {round_index + 1}/{self._max_rounds} "
            "(이전 라운드 이후 새로 추가된 메시지) -----"
        )
        if not new_messages:
            print("  (없음 — 턴 시작 직후)")
        for m in new_messages:
            preview = m.content if len(m.content) <= 500 else m.content[:500] + " ...(truncated)"
            extra = ""
            if m.tool_calls:
                extra += f" tool_calls={list(m.tool_calls)}"
            if m.tool_name:
                extra += f" tool_name={m.tool_name}"
            print(f"  {m.role}: {preview}{extra}")
        print("---------------------------------------------------\n")

    def send(self, user_input: str) -> str:
        turn_start = len(self._history)
        self._remember(Message(role="user", content=user_input))

        rag_chunks = (
            self._rag.search(user_input, top_k=self._rag_top_k) if self._rag else []
        )
        graph_text = None
        if self._graph:
            triples = self._graph.search(user_input)
            if triples:
                graph_text = "\n".join(
                    f"{t.source} -[{t.label}]-> {t.target}" for t in triples
                )
        system = self._compose_system(rag_chunks, graph_text)

        if self._debug:
            self._debug_print_turn_start(user_input, system)

        last_shown = turn_start
        for round_index in range(self._max_rounds):
            if self._debug:
                self._debug_print_round(round_index, self._history[last_shown:])
                last_shown = len(self._history)

            reply = self._client.send(
                self._history, system=system, tools=self._tools.spec()
            )

            if reply.tool_calls:
                self._remember(
                    Message(
                        role="assistant",
                        content=reply.text,
                        tool_calls=reply.tool_calls,
                    )
                )
                for call in reply.tool_calls:
                    result = self._execute_tool_call(call.name, call.arguments)
                    self._remember(
                        Message(role="tool", content=result, tool_name=call.name)
                    )
                continue

            issues = self._validate_final_response(reply.text, rag_chunks)
            if issues and round_index < self._max_rounds - 1:
                self._remember(Message(role="assistant", content=reply.text))
                feedback = (
                    "검증 결과 다음 문제가 발견되었습니다: "
                    + "; ".join(issues)
                    + " 이 점을 반영해서 응답을 다시 작성해줘."
                )
                self._remember(
                    Message(role="tool", content=feedback, tool_name="validator")
                )
                continue

            self._remember(Message(role="assistant", content=reply.text))
            return reply.text

        return MAX_ROUNDS_MESSAGE

    def _execute_tool_call(self, name: str, arguments: dict[str, Any]) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"오류: 알 수 없는 툴입니다: {name}"

        errors = validate_tool_call(tool, ToolCall(name=name, arguments=arguments))
        if errors:
            return "툴 인자 오류: " + "; ".join(errors)

        try:
            return str(self._tools.call(name, arguments))
        except ValueError as exc:
            return f"오류: {exc}"
