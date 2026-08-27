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
MAX_VALIDATION_RETRIES = 1
MAX_EMPTY_RETRIES = 2
EMPTY_RETRY_FEEDBACK = (
    "방금 응답이 비어 있었습니다. 지금까지의 대화 맥락을 참고해서 "
    "실제로 도움이 되는 답변을 다시 작성해줘."
)
MAX_ROUNDS_MESSAGE = (
    "죄송합니다, 이 요청은 최대 반복 횟수(max_rounds)를 초과해 처리하지 못했습니다."
)
EMPTY_RESPONSE_MESSAGE = "죄송합니다, 지금 응답을 생성하지 못했습니다. 다시 시도해주세요."

PLAN_SYSTEM_PROMPT = (
    "너는 계획 수립 전용 도우미다. 사용자의 요청에 바로 답하지 말고, 이 요청을 "
    "처리하려면 어떤 정보가 필요하고 어떤 순서로 처리해야 하는지 번호를 매긴 "
    "계획으로만 정리해라. 각 단계에서 사용자에게 물어봐야 할 정보가 있으면 "
    "명시해라. 실제 답이나 계산은 하지 마라."
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
        self._plan_text: str | None = None

    def plan(self, user_input: str) -> str:
        """호출자가 명시적으로 트리거하는 경량 계획 수립. 같은 모델을 계획

        전용 프롬프트로 한 번 호출해서 단계 목록을 얻고, 이후 send() 호출마다
        시스템 프롬프트에 계속 끼워넣는다. 언제 계획이 필요한지는 자동 판단하지
        않는다(경량화 — 별도 판단 LLM 호출을 추가하지 않기 위함).
        """
        reply = self._client.send(
            [Message(role="user", content=user_input)], system=PLAN_SYSTEM_PROMPT
        )
        self._plan_text = reply.text
        return self._plan_text

    def clear_plan(self) -> None:
        self._plan_text = None

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

        if self._plan_text:
            blocks.append(
                "다음은 이 작업을 위해 미리 세워둔 계획이다. 지금까지의 대화를 "
                "보고 몇 번째 단계까지 왔는지 스스로 판단해서, 그 단계에 필요한 "
                "정보가 부족하면 사용자에게 물어보고, 충분하면 다음 단계로 "
                "진행해라:\n" + self._plan_text
            )

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
        self,
        response_text: str,
        rag_chunks: list[RetrievedChunk],
        graph_text: str | None,
        user_input: str,
    ) -> list[str]:
        if not rag_chunks and not graph_text:
            return []

        issues = validate_citations(response_text, {c.source for c in rag_chunks})

        evidence_parts = [c.content for c in rag_chunks]
        if graph_text:
            evidence_parts.append(graph_text)
        evidence_parts.append(
            "사용 가능한 툴 목록(이 목록에 부합하는 내용은 근거 없는 주장이 아니다):\n"
            + self._tools.describe()
        )
        evidence_parts.append(
            "사용자가 이번 턴에 직접 말한 내용(이걸 재진술·요약·정리하는 것은 "
            "근거 없는 주장이 아니다):\n" + user_input
        )
        evidence = "\n\n".join(evidence_parts)

        output_issue = validate_output(self._client, response_text, evidence)
        if output_issue:
            issues.append(output_issue)

        return issues

    def _debug_print_turn_start(
        self, user_input: str, system: str | None, tools_desc: str
    ) -> None:
        print("\n========== [DEBUG] 새 턴 ==========")
        print(f"[사용자 입력]\n{user_input}")
        print(f"\n[이번 턴 시스템 프롬프트 (RAG/그래프 컨텍스트 포함)]\n{system or '(없음)'}")
        print(f"\n[이번 턴 사용 가능한 툴 스키마 (tools 파라미터)]\n{tools_desc or '(없음)'}")
        print("====================================")

    def _debug_print_round(
        self, round_index: int, new_messages: list[Message], tools_enabled: bool
    ) -> None:
        tools_note = "" if tools_enabled else " [이번 호출은 검증 재시도라 툴 비활성화됨]"
        print(
            f"\n----- [DEBUG] round {round_index + 1}/{self._max_rounds}{tools_note} "
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
        tools_spec = self._tools.spec()

        if self._debug:
            self._debug_print_turn_start(user_input, system, self._tools.describe())

        last_shown = turn_start
        validation_retries = 0
        empty_retries = 0
        tools_enabled_this_round = True
        for round_index in range(self._max_rounds):
            if self._debug:
                self._debug_print_round(
                    round_index, self._history[last_shown:], tools_enabled_this_round
                )
                last_shown = len(self._history)

            reply = self._client.send(
                self._history,
                system=system,
                tools=tools_spec if tools_enabled_this_round else None,
            )
            tools_enabled_this_round = True

            if not reply.text.strip() and not reply.tool_calls:
                if empty_retries < MAX_EMPTY_RETRIES and round_index < self._max_rounds - 1:
                    empty_retries += 1
                    self._remember(
                        Message(
                            role="tool",
                            content=EMPTY_RETRY_FEEDBACK,
                            tool_name="empty_response_retry",
                        )
                    )
                    continue
                return EMPTY_RESPONSE_MESSAGE

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

            issues = self._validate_final_response(
                reply.text, rag_chunks, graph_text, user_input
            )
            can_retry = (
                issues
                and validation_retries < MAX_VALIDATION_RETRIES
                and round_index < self._max_rounds - 1
            )
            if can_retry:
                validation_retries += 1
                self._remember(Message(role="assistant", content=reply.text))
                feedback = (
                    "검증 결과 다음 문제가 발견되었습니다: "
                    + "; ".join(issues)
                    + " 새로운 툴을 호출하지 말고, 위 문제를 반영해서 텍스트 답변만 다시 작성해줘."
                )
                self._remember(
                    Message(role="tool", content=feedback, tool_name="validator")
                )
                tools_enabled_this_round = False
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
        except Exception as exc:  # noqa: BLE001 - 툴 인자는 LLM이 준 신뢰 불가 입력
            return f"오류: {exc}"
