"""README generation endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.crews.readme_crew import ReadmeResult
from app.dependencies import RedisCacheDep, SettingsDep
from app.models.request import ReadmeGenerateRequest
from app.models.response import ReadmeResponse, TaskQueuedResponse
from app.tasks.local_jobs import run_generate_readme_job

router = APIRouter(prefix="/readme", tags=["readme"])


@router.post("/generate", response_model=TaskQueuedResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_readme_endpoint(
    payload: ReadmeGenerateRequest,
    background_tasks: BackgroundTasks,
    settings: SettingsDep,
    cache: RedisCacheDep,
) -> TaskQueuedResponse:
    """Queue README generation."""
    if payload.force_regenerate:
        await cache.delete_pattern(f"readme:{payload.repo_id}:*")

    task_id = str(uuid.uuid4())
    await cache.set_json_persistent(
        f"task:{task_id}:progress",
        {
            "task_id": task_id,
            "status": "queued",
            "percent": 0,
            "progress": 0,
            "current_step": "queued",
            "current_agent": "queued",
            "message": "README generation task queued.",
            "started_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "completed_steps": [],
        },
    )
    background_tasks.add_task(run_generate_readme_job, payload.repo_id, task_id, settings)
    return TaskQueuedResponse(task_id=task_id, status="queued")


@router.get("/{repo_id}", response_model=ReadmeResponse)
async def get_readme(repo_id: str, cache: RedisCacheDep) -> ReadmeResponse:
    """Return cached README content for the repository."""
    commit_sha = await _commit_sha(repo_id, cache)
    cached = await cache.get_string(f"readme:{repo_id}:{commit_sha}")
    if cached is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="README has not been generated.")

    result = ReadmeResult.model_validate_json(cached)
    return ReadmeResponse(
        repo_id=repo_id,
        content=result.content,
        markdown=result.content,
        generated_at=datetime.now(UTC).isoformat(),
        confidence=result.confidence,
        format="markdown",
    )


async def _commit_sha(repo_id: str, cache: RedisCacheDep) -> str:
    commit_sha = await cache.get_string(f"repo:{repo_id}:commit_sha")
    if commit_sha:
        return commit_sha

    meta = await cache.get_json(f"repo:{repo_id}:meta")
    if meta is not None and isinstance(meta.get("commit_sha"), str):
        return str(meta["commit_sha"])
    return "unknown"


__all__ = ["router"]
