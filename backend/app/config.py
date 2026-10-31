from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
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
    reviewer: Literal["stub", "llm"] = "stub"

    # ---- the "llm" reviewer: any server that speaks the OpenAI chat API (Ollama, vLLM, ...) ----
    # Ollama's address is http://localhost:11434/v1. Start Ollama with a larger context window
    # (OLLAMA_CONTEXT_LENGTH=16384), or long snippets are silently cut off.
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "qwen2.5-coder:7b"
    llm_api_key: str = ""  # local servers need none; hosted ones do
    llm_timeout_seconds: float = Field(default=300.0, gt=0, le=1800)
    llm_temperature: float = Field(default=0.1, ge=0, le=1)
    llm_max_output_tokens: int = Field(default=4096, ge=256, le=32768)
    # How many model calls run at once. A single local model should stay at 1; others wait.
    llm_max_concurrency: int = Field(default=1, ge=1, le=16)
    # Longest snippet accepted while the llm reviewer is active (a small model and its context
    # window cannot read more than this reliably). Roughly 500 lines.
    llm_max_code_chars: int = Field(default=20_000, ge=500)

    # Pause between the stub reviewer's progress steps, so the progress display can be seen in
    # development. Leave at 0 for tests and production.
    stub_step_delay_seconds: float = Field(default=0.0, ge=0, le=5)

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
    def code_limit(self) -> int:
        """The longest snippet the active reviewer will accept."""
        if self.reviewer == "llm":
            return min(self.max_code_chars, self.llm_max_code_chars)
        return self.max_code_chars

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def docs_enabled(self) -> bool:
        return self.environment != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
