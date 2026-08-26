from __future__ import annotations

from pathlib import Path

from lam.config import load_settings
from lam.rag.chunking import chunk_text
from lam.rag.vector_store import VectorStore

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "docs" / "knowledge"


def main() -> None:
    settings = load_settings()
    store = VectorStore(settings.database_url, settings.ollama_host)

    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        chunks = chunk_text(text)
        store.replace_document(source=path.name, chunks=chunks)
        print(f"{path.name}: {len(chunks)}개 청크 색인 완료")


if __name__ == "__main__":
    main()
