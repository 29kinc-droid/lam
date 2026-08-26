from __future__ import annotations

from pathlib import Path
from typing import Any

from lam.tools.registry import Tool

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def read_file(args: dict[str, Any]) -> str:
    requested = str(args["path"])
    target = (PROJECT_ROOT / requested).resolve()

    if not target.is_relative_to(PROJECT_ROOT):
        raise ValueError("프로젝트 디렉터리 밖의 경로는 읽을 수 없습니다.")
    if not target.is_file():
        raise ValueError(f"파일을 찾을 수 없습니다: {requested}")

    return target.read_text(encoding="utf-8", errors="replace")


FILE_READER_TOOL = Tool(
    name="read_file",
    description=(
        "프로젝트 디렉터리 안에 있는 텍스트 파일의 내용을 읽을 때 사용한다. "
        "프로젝트 밖의 파일이나 존재하지 않는 파일은 읽을 수 없다."
    ),
    fn=read_file,
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "프로젝트 루트 기준 상대 경로 (예: 'docs/00-overview.md')",
            }
        },
        "required": ["path"],
    },
)
