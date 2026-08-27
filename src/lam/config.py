from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# "localhost"가 아닌 127.0.0.1을 쓴다: Windows에서 "localhost"는 IPv6(::1)로
# 먼저 시도되는데, Docker Desktop이 광고하는 [::]:PORT 매핑이 실제로는 응답하지
# 않아 연결이 통째로 멈추는 문제를 겪었다(psycopg에서 실측: 수십 초 이상 행,
# 127.0.0.1로 바꾸면 즉시 연결).
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
# qwen2.5:7b-instruct는 특정 자기소개성 질문+tools= 조합에서 100% 빈 응답을
# 내는 버그가 있었다(llm/client.py 참고). qwen3:8b는 같은 시나리오+2026-08
# 기준 외부 벤치마크(Berkeley BFCL 등)에서도 이 체급 툴콜링 신뢰도가 더
# 낫다고 확인돼서 교체.
DEFAULT_OLLAMA_MODEL = "qwen3:8b"
DEFAULT_REDIS_URL = "redis://127.0.0.1:6379/0"
DEFAULT_DATABASE_URL = "postgresql://lam:lam@127.0.0.1:5432/lam"
DEFAULT_SESSION_ID = "default"
DEFAULT_NEO4J_URI = "bolt://127.0.0.1:7687"
DEFAULT_NEO4J_USER = "neo4j"
DEFAULT_NEO4J_PASSWORD = "lam12345"
DEFAULT_DEBUG = False


@dataclass(frozen=True)
class Settings:
    ollama_host: str
    ollama_model: str
    redis_url: str
    database_url: str
    session_id: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    debug: bool


def load_settings() -> Settings:
    return Settings(
        ollama_host=os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST),
        ollama_model=os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
        redis_url=os.environ.get("REDIS_URL", DEFAULT_REDIS_URL),
        database_url=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL),
        session_id=os.environ.get("SESSION_ID", DEFAULT_SESSION_ID),
        neo4j_uri=os.environ.get("NEO4J_URI", DEFAULT_NEO4J_URI),
        neo4j_user=os.environ.get("NEO4J_USER", DEFAULT_NEO4J_USER),
        neo4j_password=os.environ.get("NEO4J_PASSWORD", DEFAULT_NEO4J_PASSWORD),
        debug=os.environ.get("DEBUG", "").strip().lower() in {"1", "true", "yes"},
    )
