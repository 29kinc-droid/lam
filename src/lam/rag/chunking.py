from __future__ import annotations

# iGPU(Vulkan) 환경에서는 입력 컨텍스트 길이가 응답 속도에 큰 영향을 준다(실측:
# ~1000자 추가만으로 16배 지연). top_k(=3)는 유지하되 청크를 작게 잘라서
# 한 번에 딸려오는 총 텍스트량을 줄인다.
DEFAULT_CHUNK_SIZE = 100
DEFAULT_OVERLAP = 15


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
