from __future__ import annotations

from typing import Any

from lam.controller.loop import EMPTY_RESPONSE_MESSAGE, ConversationLoop
from lam.llm.client import OllamaClient
from lam.tools.registry import ToolRegistry
from lam.types import LLMReply, Message


class _EmptyThenRealClient(OllamaClient):
    def __init__(self, empty_count: int) -> None:
        self.calls = 0
        self._empty_count = empty_count

    def send(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMReply:
        self.calls += 1
        if self.calls <= self._empty_count:
            return LLMReply(text="", tool_calls=())
        return LLMReply(text="이제 실제 응답입니다.", tool_calls=())


class _AlwaysEmptyClient(OllamaClient):
    def __init__(self) -> None:
        self.calls = 0

    def send(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMReply:
        self.calls += 1
        return LLMReply(text="", tool_calls=())


def test_empty_response_recovers_after_retry() -> None:
    client = _EmptyThenRealClient(empty_count=1)
    loop = ConversationLoop(client, ToolRegistry([]))

    result = loop.send("아무거나")

    assert result == "이제 실제 응답입니다."
    assert client.calls == 2


def test_always_empty_gives_up_within_budget() -> None:
    client = _AlwaysEmptyClient()
    loop = ConversationLoop(client, ToolRegistry([]), max_rounds=5)

    result = loop.send("아무거나")

    assert result == EMPTY_RESPONSE_MESSAGE
    # MAX_EMPTY_RETRIES=2 -> 최초 호출 + 재시도 2번 = 3번 호출 후 포기
    assert client.calls == 3
