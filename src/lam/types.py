from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Role = Literal["user", "assistant", "tool", "system"]


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_name: str | None = None


@dataclass(frozen=True)
class LLMReply:
    text: str
    tool_calls: tuple[ToolCall, ...] = ()
