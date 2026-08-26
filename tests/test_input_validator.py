from __future__ import annotations

from lam.tools.calculator import CALCULATOR_TOOL
from lam.types import ToolCall
from lam.validators.input_validator import validate_tool_call


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
