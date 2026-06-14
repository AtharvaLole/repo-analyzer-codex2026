"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the API, workers, and agent layer."""

    app_name: str = "AI Software Engineering Assistant"
    app_version: str = "0.1.0"
    environment: str = Field(default="local", validation_alias="ENVIRONMENT")
    debug: bool = Field(default=True, validation_alias="DEBUG")
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    redis_url: str = "redis://localhost:6379/0"
    chroma_path: Path = Field(default=Path("./.data/chroma"), validation_alias="CHROMA_PATH")
    chroma_persist_dir: Path | None = Field(default=None, validation_alias="CHROMA_PERSIST_DIR")
    repo_storage_path: Path = Path("./.data/repos")
    repos_base_dir: Path = Field(default=Path("./.data/repos"), validation_alias="REPOS_BASE_DIR")
    max_repo_size_mb: int = Field(default=250, validation_alias="MAX_REPO_SIZE_MB", ge=1)

    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    anthropic_api_key: SecretStr | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    llm_provider: str = "openai"
    chat_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    sentry_dsn: str | None = Field(default=None, validation_alias="SENTRY_DSN")
    sentry_traces_sample_rate: float = 0.1

    clerk_issuer: str | None = Field(default=None, validation_alias="CLERK_ISSUER")
    clerk_jwks_url: str | None = Field(default=None, validation_alias="CLERK_JWKS_URL")

    @property
    def CHROMA_PERSIST_DIR(self) -> Path:
        """Compatibility property for prompt-level settings naming."""
        return self.chroma_persist_dir or self.chroma_path

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


__all__ = ["Settings", "get_settings"]
