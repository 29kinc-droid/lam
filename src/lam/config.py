from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b-instruct"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"
DEFAULT_DATABASE_URL = "postgresql://lam:lam@localhost:5432/lam"
DEFAULT_SESSION_ID = "default"
DEFAULT_NEO4J_URI = "bolt://localhost:7687"
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
