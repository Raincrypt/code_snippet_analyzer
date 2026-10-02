from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration, read from environment variables (and `backend/.env` if present)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["console", "json"] = "console"

    # SQLite works with zero setup. In production use PostgreSQL, e.g.
    # postgresql://user:password@host:5432/dbname (needs: pip install -e ".[postgres]").
    database_url: str = "sqlite+aiosqlite:///./app.db"

    # Comma-separated browser origins allowed to call the API directly.
    # Empty is fine when the frontend reaches the API through a same-origin proxy.
    cors_origins: str = ""

    # Which Reviewer implementation to use (see app/services/reviewer.py).
    reviewer: Literal["stub"] = "stub"

    max_code_chars: int = 100_000
    max_question_chars: int = 4_000

    @field_validator("database_url")
    @classmethod
    def use_async_driver(cls, url: str) -> str:
        """Hosting platforms hand out plain postgres:// URLs; SQLAlchemy needs the async driver."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+asyncpg://" + url.removeprefix(prefix)
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def docs_enabled(self) -> bool:
        return self.environment != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
