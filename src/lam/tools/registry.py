from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Tool:
    name: str
    description: str
    fn: Callable[[dict[str, Any]], Any]
    parameters: dict[str, Any]


class ToolRegistry:
    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {t.name: t for t in tools}

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def call(self, name: str, args: dict[str, Any]) -> Any:
        if name not in self._tools:
            raise ValueError(f"Unknown tool: {name}")
        return self._tools[name].fn(args)

    def spec(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]
