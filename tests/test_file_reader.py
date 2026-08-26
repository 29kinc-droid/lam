from __future__ import annotations

import pytest

from lam.tools.file_reader import read_file


def test_read_file_returns_content() -> None:
    content = read_file({"path": "docs/knowledge/lam-intro.md"})
    assert "나이팅게일" in content


def test_read_file_missing_file_raises() -> None:
    with pytest.raises(ValueError):
        read_file({"path": "docs/knowledge/does-not-exist.md"})


def test_read_file_blocks_path_traversal() -> None:
    with pytest.raises(ValueError):
        read_file({"path": "../outside.txt"})
