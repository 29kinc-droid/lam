from __future__ import annotations

from lam.llm.client import OllamaClient
from lam.types import Message

VALIDATOR_SYSTEM_PROMPT = (
    "너는 답변 검증기다. 주어진 '근거'와 '답변'을 비교해서, 답변이 근거에 없는 "
    "사실을 단정적으로 주장하는지 확인해라. 문제가 없으면 정확히 'OK'라고만 답하고, "
    "문제가 있으면 'ISSUE: <한 문장 이유>' 형식으로만 답해라."
)


def validate_output(
    client: OllamaClient, response_text: str, evidence: str
) -> str | None:
    if not evidence.strip():
        return None

    prompt = f"근거:\n{evidence}\n\n답변:\n{response_text}"
    result = client.send(
        [Message(role="user", content=prompt)], system=VALIDATOR_SYSTEM_PROMPT
    )
    text = result.text.strip()
    if text.upper().startswith("OK"):
        return None
    return text
