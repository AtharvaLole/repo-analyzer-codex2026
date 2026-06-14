"""Response models."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    redis: str = "unknown"
    chroma: str = "unknown"
    version: str | None = None


class TaskQueuedResponse(BaseModel):
    """Queued background task response."""

    task_id: str
    status: Literal["queued"]


class RepositoryIndexResponse(BaseModel):
    """Repository indexing status response."""

    repo_id: str
    status: str
    task_id: str | None = None
    message: str


class RepoIndexQueuedResponse(BaseModel):
    """Repository indexing queue response."""

    repo_id: str
    task_id: str
    status: Literal["queued", "ready"]
    result: dict | None = None


class RepoStatusResponse(BaseModel):
    """Repository indexing status response."""

    repo_id: str
    status: Literal["indexing", "ready", "failed"]
    meta: dict | None = None


class RepoFileInfo(BaseModel):
    """Indexed repository file summary."""

    file_path: str
    language: str
    chunk_count: int = Field(ge=0)


class RepoFilesResponse(BaseModel):
    """Indexed file list response."""

    repo_id: str
    files: list[RepoFileInfo]


class DeleteRepoResponse(BaseModel):
    """Repository deletion response."""

    repo_id: str
    deleted: bool


class CodeCitation(BaseModel):
    """Source code citation returned with AI answers."""

    repo_id: str
    file_path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    score: float = Field(ge=0.0)
    text: str | None = None


class Citation(BaseModel):
    """Workflow citation response."""

    file_path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    snippet: str
    relevance: str


class ChatResponse(BaseModel):
    """Repository-aware chat response."""

    repo_id: str | None = None
    answer: str
    citations: list[Citation | CodeCitation] = Field(default_factory=list)
    confidence: int = Field(default=0, ge=0, le=100)
    intent: str = "unknown"
    active_agents: list[str] = Field(default_factory=list)
    agent_trace: list[str] = Field(default_factory=list)


class ReadmeResponse(BaseModel):
    """README draft response."""

    content: str
    generated_at: str
    confidence: int = Field(ge=0, le=100)
    format: Literal["markdown"] = "markdown"
    repo_id: str | None = None
    markdown: str | None = None


class AgentStatus(BaseModel):
    """Single agent status entry."""

    name: str
    status: str
    detail: str | None = None


class AgentsStatusResponse(BaseModel):
    """Configured agent roster response."""

    agents: list[AgentStatus]


class AgentTaskStatusResponse(BaseModel):
    """Background task and agent progress response."""

    task_id: str
    status: str
    progress: int = Field(ge=0, le=100)
    current_agent: str
    completed_steps: list[str] = Field(default_factory=list)
    current_step: str | None = None
    message: str | None = None
    started_at: str | None = None
    updated_at: str | None = None


__all__ = [
    "AgentStatus",
    "AgentTaskStatusResponse",
    "AgentsStatusResponse",
    "Citation",
    "ChatResponse",
    "CodeCitation",
    "DeleteRepoResponse",
    "HealthResponse",
    "RepoFileInfo",
    "RepoFilesResponse",
    "RepoIndexQueuedResponse",
    "RepoStatusResponse",
    "ReadmeResponse",
    "RepositoryIndexResponse",
    "TaskQueuedResponse",
]
