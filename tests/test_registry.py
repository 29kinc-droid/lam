from __future__ import annotations

import pytest

from lam.tools.registry import Tool, ToolRegistry


def _make_tool(name: str) -> Tool:
    return Tool(
        name=name,
        description=f"{name} 설명",
        fn=lambda args: f"{name}-result",
        parameters={"type": "object", "properties": {}},
    )


def test_registry_spec_lists_all_tools() -> None:
    registry = ToolRegistry([_make_tool("a"), _make_tool("b")])
    spec = registry.spec()
    names = {entry["function"]["name"] for entry in spec}
    assert names == {"a", "b"}


def test_registry_call_dispatches_to_correct_tool() -> None:
    registry = ToolRegistry([_make_tool("a"), _make_tool("b")])
    assert registry.call("b", {}) == "b-result"


def test_registry_call_unknown_tool_raises() -> None:
    registry = ToolRegistry([_make_tool("a")])
    with pytest.raises(ValueError):
        registry.call("missing", {})


def test_registry_get_returns_none_for_unknown() -> None:
    registry = ToolRegistry([_make_tool("a")])
    assert registry.get("missing") is None
    assert registry.get("a") is not None
