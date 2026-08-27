from __future__ import annotations

from lam.tools.calculator import CALCULATOR_TOOL
from lam.tools.registry import Tool
from lam.types import ToolCall
from lam.validators.input_validator import validate_tool_call

_ENUM_TOOL = Tool(
    name="pick_color",
    description="테스트용",
    fn=lambda args: "ok",
    parameters={
        "type": "object",
        "properties": {"color": {"type": "string", "enum": ["red", "blue"]}},
        "required": ["color"],
    },
)


def test_missing_required_field_is_reported() -> None:
    errors = validate_tool_call(CALCULATOR_TOOL, ToolCall(name="calculator", arguments={}))
    assert any("필수 인자 누락" in e for e in errors)


def test_wrong_type_is_reported() -> None:
    call = ToolCall(name="calculator", arguments={"expression": 123})
    errors = validate_tool_call(CALCULATOR_TOOL, call)
    assert any("타입이 올바르지" in e for e in errors)


def test_valid_call_has_no_errors() -> None:
    call = ToolCall(name="calculator", arguments={"expression": "1+1"})
    assert validate_tool_call(CALCULATOR_TOOL, call) == []


def test_unknown_argument_is_reported() -> None:
    call = ToolCall(
        name="calculator", arguments={"expression": "1+1", "extra": "x"}
    )
    errors = validate_tool_call(CALCULATOR_TOOL, call)
    assert any("알 수 없는 인자" in e for e in errors)


def test_value_outside_enum_is_reported() -> None:
    call = ToolCall(name="pick_color", arguments={"color": "green"})
    errors = validate_tool_call(_ENUM_TOOL, call)
    assert any("허용된 목록에 없습니다" in e for e in errors)


def test_value_inside_enum_has_no_errors() -> None:
    call = ToolCall(name="pick_color", arguments={"color": "red"})
    assert validate_tool_call(_ENUM_TOOL, call) == []
