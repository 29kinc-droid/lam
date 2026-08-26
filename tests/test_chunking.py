from __future__ import annotations

from lam.rag.chunking import chunk_text


def test_chunk_text_empty_returns_no_chunks() -> None:
    assert chunk_text("") == []


def test_chunk_text_single_chunk_when_short() -> None:
    text = " ".join(f"word{i}" for i in range(10))
    chunks = chunk_text(text, chunk_size=200, overlap=30)
    assert chunks == [text]


def test_chunk_text_splits_and_overlaps() -> None:
    text = " ".join(f"word{i}" for i in range(10))
    chunks = chunk_text(text, chunk_size=4, overlap=1)
    assert len(chunks) > 1
    # 마지막 청크의 첫 단어가 이전 청크의 마지막 단어와 겹쳐야 한다.
    first_chunk_words = chunks[0].split()
    second_chunk_words = chunks[1].split()
    assert first_chunk_words[-1] == second_chunk_words[0]
