from __future__ import annotations

import re

CITATION_PATTERN = re.compile(r"\[([^\[\]]+)\]")


def validate_citations(response_text: str, known_sources: set[str]) -> list[str]:
    cited = set(CITATION_PATTERN.findall(response_text))
    unknown = cited - known_sources
    return [f"출처 '{source}'는 이번 턴 검색 결과에 없습니다" for source in sorted(unknown)]
