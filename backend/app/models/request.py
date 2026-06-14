"""Request models."""

from typing import Any, Self
from urllib.parse import urlparse

from pydantic import AnyUrl, BaseModel, Field, field_validator, model_validator


class IndexRequest(BaseModel):
    """Payload for queueing repository indexing."""

    github_url: str = Field(min_length=1)
    repo_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]+$", max_length=128)

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("GitHub URL must use http or https.")
        if parsed.netloc.lower() != "github.com":
            raise ValueError("GitHub URL must point to github.com.")
        parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(parts) < 2:
            raise ValueError("GitHub URL must include owner and repository.")
        return value


class RepositoryIndexRequest(BaseModel):
    """Payload for repository indexing."""

    repository_url: AnyUrl
    branch: str = Field(default="main", min_length=1, max_length=128)
    repo_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]+$", max_length=128)
    include_globs: list[str] = Field(
        default_factory=lambda: [
            "**/*.py",
            "**/*.ts",
            "**/*.tsx",
            "**/*.js",
            "**/*.jsx",
            "**/*.md",
        ],
    )
    exclude_globs: list[str] = Field(
        default_factory=lambda: [
            "**/.git/**",
            "**/node_modules/**",
            "**/.next/**",
            "**/__pycache__/**",
            "**/.venv/**",
            "**/dist/**",
            "**/build/**",
        ],
    )


class ChatMessage(BaseModel):
    """Prior chat message supplied by the client."""

    role: str = Field(pattern=r"^(user|assistant|system)$")
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    """Repository-aware chat payload."""

    repo_id: str = Field(min_length=1, max_length=128)
    question: str = Field(default="", min_length=1)
    message: str | None = Field(default=None, min_length=1)
    stream: bool = False
    history: list[ChatMessage] = Field(default_factory=list)
    top_k: int = Field(default=6, ge=1, le=20)

    @model_validator(mode="before")
    @classmethod
    def support_legacy_message_field(cls, data: Any) -> Any:
        if isinstance(data, dict) and "question" not in data and "message" in data:
            data = {**data, "question": data["message"]}
        return data

    @model_validator(mode="after")
    def require_question(self) -> Self:
        if not self.question.strip():
            raise ValueError("question is required.")
        return self


class ReadmeRequest(BaseModel):
    """README generation payload."""

    repo_id: str = Field(min_length=1, max_length=128)
    audience: str = Field(default="engineering team", min_length=1, max_length=128)
    include_setup: bool = True
    include_architecture: bool = True


class ReadmeGenerateRequest(BaseModel):
    """Payload for queueing README generation."""

    repo_id: str = Field(min_length=1, max_length=128)
    force_regenerate: bool = False


__all__ = [
    "ChatMessage",
    "ChatRequest",
    "IndexRequest",
    "ReadmeGenerateRequest",
    "ReadmeRequest",
    "RepositoryIndexRequest",
]
