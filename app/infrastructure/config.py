from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_env: str = "development"
    api_base_url: str = "http://localhost:8000"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/retail_ai"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    redis_url: str = "redis://localhost:6379/0"
    redis_session_ttl_seconds: int = 86_400
    redis_session_prefix: str = "retail-ai:session"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
