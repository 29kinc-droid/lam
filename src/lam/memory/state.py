from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

import redis

from lam.types import Message, ToolCall

DEFAULT_HISTORY_LIMIT = 20


class SessionState:
    def __init__(self, redis_url: str) -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def _key(self, session_id: str) -> str:
        return f"lam:session:{session_id}:history"

    def load_history(
        self, session_id: str, limit: int = DEFAULT_HISTORY_LIMIT
    ) -> list[Message]:
        raw = self._client.lrange(self._key(session_id), -limit, -1)
        return [_decode_message(str(item)) for item in raw]

    def append_message(self, session_id: str, message: Message) -> None:
        self._client.rpush(self._key(session_id), _encode_message(message))


def _encode_message(message: Message) -> str:
    payload = {
        "role": message.role,
        "content": message.content,
        "tool_calls": [asdict(tc) for tc in message.tool_calls],
        "tool_name": message.tool_name,
    }
    return json.dumps(payload, ensure_ascii=False)


def _decode_message(raw: str) -> Message:
    data: dict[str, Any] = json.loads(raw)
    tool_calls = tuple(ToolCall(**tc) for tc in data.get("tool_calls", []))
    return Message(
        role=data["role"],
        content=data["content"],
        tool_calls=tool_calls,
        tool_name=data.get("tool_name"),
    )
