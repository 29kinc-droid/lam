from __future__ import annotations

from lam.validators.post_exec_validator import validate_citations


def test_unknown_citation_is_reported() -> None:
    issues = validate_citations("참고: [unknown.md] 내용", {"lam-intro.md"})
    assert len(issues) == 1
    assert "unknown.md" in issues[0]


def test_known_citation_has_no_issues() -> None:
    assert validate_citations("참고: [lam-intro.md] 내용", {"lam-intro.md"}) == []


def test_no_citation_has_no_issues() -> None:
    assert validate_citations("그냥 평문 답변입니다.", {"lam-intro.md"}) == []
