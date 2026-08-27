from __future__ import annotations

from lam.llm.client import _parse_tool_calls
from lam.types import ToolCall


def test_well_formed_tagged_call() -> None:
    text = '<tool_call>\n{"name": "calculator", "arguments": {"expression": "3+4"}}\n</tool_call>'
    calls, remaining = _parse_tool_calls(text)
    assert calls == (ToolCall(name="calculator", arguments={"expression": "3+4"}),)
    assert remaining == ""


def test_missing_closing_tag_still_parses() -> None:
    text = '<tool_call>\n{"name": "calculator", "arguments": {"expression": ""}}\n<tool_call>\n'
    calls, _remaining = _parse_tool_calls(text)
    assert calls == (ToolCall(name="calculator", arguments={"expression": ""}),)


def test_bare_json_without_tags() -> None:
    text = '{"name": "calculator", "arguments": {"expression": "37 * 59"}}'
    calls, remaining = _parse_tool_calls(text)
    assert calls == (ToolCall(name="calculator", arguments={"expression": "37 * 59"}),)
    assert remaining == ""


def test_plain_text_has_no_tool_calls() -> None:
    text = "안녕하세요! 어떻게 도와드릴까요?"
    calls, remaining = _parse_tool_calls(text)
    assert calls == ()
    assert remaining == text


def test_preamble_text_kept_alongside_tagged_call() -> None:
    text = (
        "네, 계산해드릴게요.\n"
        '<tool_call>\n{"name": "calculator", "arguments": {"expression": "3+4"}}\n</tool_call>'
    )
    calls, remaining = _parse_tool_calls(text)
    assert calls == (ToolCall(name="calculator", arguments={"expression": "3+4"}),)
    assert remaining == "네, 계산해드릴게요."


def test_multiple_tool_calls_in_order() -> None:
    text = (
        '<tool_call>{"name": "a", "arguments": {}}</tool_call>'
        '<tool_call>{"name": "b", "arguments": {"x": 1}}</tool_call>'
    )
    calls, remaining = _parse_tool_calls(text)
    assert calls == (
        ToolCall(name="a", arguments={}),
        ToolCall(name="b", arguments={"x": 1}),
    )
    assert remaining == ""


def test_code_fenced_json_inside_tags() -> None:
    text = (
        "<tool_call>\n```json\n"
        '{"name": "calculator", "arguments": {"expression": "1+1"}}\n'
        "```\n</tool_call>"
    )
    calls, _remaining = _parse_tool_calls(text)
    assert calls == (ToolCall(name="calculator", arguments={"expression": "1+1"}),)
