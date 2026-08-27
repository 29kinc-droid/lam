from __future__ import annotations

from typing import Any

from ollama import Client

from lam.config import Settings
from lam.types import LLMReply, Message, ToolCall

# Ollama 기본 temperature(0.8)는 툴콜링 프롬프트에서 빈 응답/언어 섞임 등
# 변동성이 커서, 좀 더 일관된 응답을 위해 낮춰서 고정한다.
DEFAULT_TEMPERATURE = 0.2


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self._client = Client(host=settings.ollama_host)
        self._model = settings.ollama_model

    def send(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMReply:
        chat_messages: list[dict[str, Any]] = []
        if system:
            chat_messages.append({"role": "system", "content": system})
        for m in messages:
            entry: dict[str, Any] = {"role": m.role, "content": m.content}
            if m.tool_name:
                entry["tool_name"] = m.tool_name
            chat_messages.append(entry)

        response = self._client.chat(
            model=self._model,
            messages=chat_messages,
            tools=tools or None,
            options={"temperature": DEFAULT_TEMPERATURE},
        )
        message = response.message
        tool_calls = tuple(
            ToolCall(name=tc.function.name, arguments=dict(tc.function.arguments))
            for tc in (message.tool_calls or [])
        )
        return LLMReply(text=message.content or "", tool_calls=tool_calls)
