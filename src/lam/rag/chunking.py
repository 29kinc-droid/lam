from __future__ import annotations

DEFAULT_CHUNK_SIZE = 200
DEFAULT_OVERLAP = 30


def chunk_text(
    text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_OVERLAP
) -> list[str]:
    words = text.split()
    if not words:
        return []

    step = max(chunk_size - overlap, 1)
    chunks: list[str] = []
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_size])
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(words):
            break
    return chunks
