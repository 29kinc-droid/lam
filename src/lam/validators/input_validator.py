from __future__ import annotations

from typing import Any

from lam.tools.registry import Tool
from lam.types import ToolCall

_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "object": dict,
    "array": list,
}


def validate_tool_call(tool: Tool, call: ToolCall) -> list[str]:
    errors: list[str] = []
    properties: dict[str, Any] = tool.parameters.get("properties", {})
    required: list[str] = tool.parameters.get("required", [])

    for field in required:
        if field not in call.arguments:
            errors.append(f"필수 인자 누락: {field}")

    for name, value in call.arguments.items():
        prop = properties.get(name)
        if prop is None:
            errors.append(f"알 수 없는 인자: {name}")
            continue
        expected = _TYPE_MAP.get(prop.get("type", ""))
        if expected and not isinstance(value, expected):
            errors.append(f"'{name}'의 타입이 올바르지 않습니다 (기대: {prop.get('type')})")
            continue

        allowed = prop.get("enum")
        if allowed is not None and value not in allowed:
            # 대괄호를 쓰면 응답 텍스트에 이 오류 메시지가 인용될 때 인용검증기의
            # "[출처명]" 패턴과 충돌하므로(실제로 한 번 발생) 괄호를 쓰지 않는다.
            allowed_text = ", ".join(str(a) for a in allowed)
            errors.append(
                f"'{name}'의 값 '{value}'은 허용된 목록에 없습니다 "
                f"(가능한 값: {allowed_text})"
            )

    return errors
