from __future__ import annotations

from typing import Any

from lam.controller.loop import MAX_ROUNDS_MESSAGE, ConversationLoop
from lam.llm.client import OllamaClient
from lam.tools.registry import Tool, ToolRegistry
from lam.types import LLMReply, Message, ToolCall


class _AlwaysToolClient(OllamaClient):
    def __init__(self) -> None:
        self.calls = 0

    def send(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMReply:
        self.calls += 1
        return LLMReply(text="", tool_calls=(ToolCall(name="noop", arguments={}),))


def test_max_rounds_circuit_breaker_stops_infinite_tool_loop() -> None:
    noop_tool = Tool(
        name="noop",
        description="테스트용 무동작 툴",
        fn=lambda args: "ok",
        parameters={"type": "object", "properties": {}},
    )
    client = _AlwaysToolClient()
    loop = ConversationLoop(client, ToolRegistry([noop_tool]), max_rounds=3)

    result = loop.send("아무거나")

    assert result == MAX_ROUNDS_MESSAGE
    assert client.calls == 3
