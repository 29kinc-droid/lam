from __future__ import annotations

import json
from typing import Any

from ollama import Client

from lam.config import Settings
from lam.types import LLMReply, Message, ToolCall

# Ollama 기본 temperature(0.8)는 응답 변동성이 커서 낮춰서 고정한다.
DEFAULT_TEMPERATURE = 0.2

# Ollama 네이티브 tools= 파라미터가 qwen2.5:7b-instruct에서 특정 질문(예:
# "네가 쓸 수 있는 도구 목록 보여줘")과 결합될 때 빈 응답을 내는 버그가 있어서,
# tools=는 아예 쓰지 않고 프롬프트 기반 툴콜링(ReAct 원조 방식)으로 우회한다.
# 툴 설명을 텍스트로 시스템 프롬프트에 넣고, 모델이 아래 형식으로 응답하면
# 우리가 직접 파싱한다. 모델이 </tool_call> 닫는 태그를 자주 빼먹거나 태그 자체를
# 생략하고 JSON만 내는 경우가 있어서, 정규식으로 태그 쌍을 강제하지 않고
# "<tool_call>" 마커(또는 마커 없이 통째로 JSON) 뒤에서 JSONDecoder로 값 하나를
# 관대하게 읽어내는 방식으로 파싱한다.
TOOL_CALL_MARKER = "<tool_call>"
TOOL_CALL_CLOSING = "</tool_call>"

TOOL_INSTRUCTIONS_TEMPLATE = """다음은 사용 가능한 툴 목록이다:
{tool_descriptions}

툴을 호출하려면 아래 형식을 정확히 지켜서 출력해라:
<tool_call>
{{"name": "<툴 이름>", "arguments": {{<인자들을 JSON으로>}}}}
</tool_call>

한 번에 여러 툴을 호출하려면 <tool_call> 블록을 여러 개 연달아 써라.

중요: 사용 가능한 툴이 무엇인지 설명하거나 나열해달라는 질문에는 툴을 호출하지 말고
그냥 이 목록을 텍스트로 설명해라. 필요한 인자값을 모르거나 확신이 없으면 빈 값이나
지어낸 값으로 툴을 호출하지 말고, 먼저 사용자에게 값을 물어보거나 답변만 해라."""


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
        full_system = system
        if tools:
            instructions = TOOL_INSTRUCTIONS_TEMPLATE.format(
                tool_descriptions=_describe_tools(tools)
            )
            full_system = f"{system}\n\n{instructions}" if system else instructions

        chat_messages: list[dict[str, Any]] = []
        if full_system:
            chat_messages.append({"role": "system", "content": full_system})
        for m in messages:
            entry: dict[str, Any] = {"role": m.role, "content": m.content}
            if m.tool_name:
                entry["tool_name"] = m.tool_name
            chat_messages.append(entry)

        response = self._client.chat(
            model=self._model,
            messages=chat_messages,
            options={"temperature": DEFAULT_TEMPERATURE},
            # thinking을 지원하는 모델(예: qwen3)은 기본적으로 thinking이 켜져서
            # 숨은 추론 토큰을 잔뜩 생성한다 — 이 iGPU 환경에서 실측 4배(58초→
            # 14초) 차이가 나서 명시적으로 끈다. thinking 미지원 모델에는 무시됨.
            think=False,
        )
        raw_text = response.message.content or ""
        tool_calls, remaining_text = _parse_tool_calls(raw_text)
        return LLMReply(text=remaining_text, tool_calls=tool_calls)


def _describe_tools(tools: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for entry in tools:
        fn = entry.get("function", {})
        name = fn.get("name", "")
        description = fn.get("description", "")
        params = fn.get("parameters", {})
        properties: dict[str, Any] = params.get("properties", {})
        required = set(params.get("required", []))

        arg_lines: list[str] = []
        for pname, pinfo in properties.items():
            mark = "" if pname in required else "(선택)"
            ptype = pinfo.get("type", "")
            pdesc = pinfo.get("description", "")
            arg_lines.append(f"    - {pname}{mark} ({ptype}): {pdesc}")
        args_block = "\n" + "\n".join(arg_lines) if arg_lines else " (인자 없음)"

        lines.append(f"- {name}: {description}\n  인자:{args_block}")
    return "\n".join(lines)


def _decode_tool_call(text: str) -> tuple[ToolCall | None, int]:
    """text 맨 앞(공백·마크다운 코드펜스는 건너뜀)에서 JSON 값 하나를 관대하게
    읽어 ToolCall로 변환한다. 반환값의 두 번째 원소는 원본 text 기준으로
    소비한 문자 수다(실패 시 0).
    """
    stripped = text.lstrip()
    offset = len(text) - len(stripped)

    if stripped.startswith("```"):
        body = stripped[3:]
        first_newline = body.find("\n")
        if first_newline != -1:
            offset += 3 + first_newline + 1
            stripped = body[first_newline + 1 :]

    try:
        data, end = json.JSONDecoder().raw_decode(stripped)
    except json.JSONDecodeError:
        return None, 0
    if not isinstance(data, dict):
        return None, 0
    name = data.get("name")
    arguments = data.get("arguments")
    if isinstance(name, str) and isinstance(arguments, dict):
        return ToolCall(name=name, arguments=arguments), offset + end
    return None, 0


def _parse_tool_calls(text: str) -> tuple[tuple[ToolCall, ...], str]:
    calls: list[ToolCall] = []
    consumed: list[tuple[int, int]] = []

    search_from = 0
    while True:
        marker_pos = text.find(TOOL_CALL_MARKER, search_from)
        if marker_pos == -1:
            break
        json_region = text[marker_pos + len(TOOL_CALL_MARKER) :]
        call, region_end = _decode_tool_call(json_region)
        if call is None:
            search_from = marker_pos + len(TOOL_CALL_MARKER)
            continue

        end_pos = marker_pos + len(TOOL_CALL_MARKER) + region_end
        closing_pos = text.find(TOOL_CALL_CLOSING, end_pos, end_pos + 16)
        if closing_pos != -1:
            end_pos = closing_pos + len(TOOL_CALL_CLOSING)

        calls.append(call)
        consumed.append((marker_pos, end_pos))
        search_from = end_pos

    if not calls:
        # 태그 없이 통째로 JSON 툴콜만 낸 경우
        call, region_end = _decode_tool_call(text)
        if call is not None:
            return (call,), text[region_end:].strip()
        return (), text.strip()

    pieces: list[str] = []
    cursor = 0
    for start, end in consumed:
        pieces.append(text[cursor:start])
        cursor = end
    pieces.append(text[cursor:])
    remaining_text = "".join(pieces).strip()

    return tuple(calls), remaining_text
