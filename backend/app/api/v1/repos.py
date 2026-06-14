"""Repository ingestion and index management endpoints."""

from __future__ import annotations

import asyncio
import hashlib
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException, status

from app.dependencies import RedisCacheDep, SettingsDep
from app.models.request import IndexRequest, RepositoryIndexRequest
from app.models.response import (
    DeleteRepoResponse,
    RepoFileInfo,
    RepoFilesResponse,
    RepoIndexQueuedResponse,
    RepoStatusResponse,
)
from app.rag.embedder import CodeEmbedder
from app.tasks import celery_app, index_repo

router = APIRouter(prefix="/repos", tags=["repos"])


def create_repo_id(repository_url: str) -> str:
    """Create a stable, non-sensitive repository identifier."""
    digest = hashlib.sha256(repository_url.encode("utf-8")).hexdigest()
    return digest[:12]


@router.post("/index", response_model=RepoIndexQueuedResponse, status_code=status.HTTP_202_ACCEPTED)
async def index_repository(
    payload: IndexRequest,
    settings: SettingsDep,
    cache: RedisCacheDep,
) -> RepoIndexQueuedResponse:
    """Queue a repository for indexing unless a matching index already exists."""
    repo_id = payload.repo_id or create_repo_id(payload.github_url)
    meta_key = f"repo:{repo_id}:meta"
    meta = await cache.get_json(meta_key)
    remote_sha = await _remote_head_sha(payload.github_url)
    if _is_cached_index_current(meta=meta, github_url=payload.github_url, remote_sha=remote_sha):
        task_id = await cache.get_string(f"repo:{repo_id}:latest_task_id")
        files_payload = await cache.get_json(f"repo:{repo_id}:files")
        return RepoIndexQueuedResponse(
            repo_id=repo_id,
            task_id=task_id or "",
            status="ready",
            result=_cached_index_result(repo_id=repo_id, meta=meta or {}, files_payload=files_payload),
        )

    task = index_repo.delay(repo_id, payload.github_url)
    await cache.set_string(f"repo:{repo_id}:latest_task_id", str(task.id))
    await cache.set_json_persistent(
        f"task:{task.id}:progress",
        {
            "task_id": str(task.id),
            "status": "queued",
            "percent": 0,
            "progress": 0,
            "current_step": "queued",
            "current_agent": "queued",
            "message": "Repository indexing task queued.",
            "started_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "completed_steps": [],
        },
    )
    return RepoIndexQueuedResponse(repo_id=repo_id, task_id=str(task.id), status="queued")


@router.post("", response_model=RepoIndexQueuedResponse, status_code=status.HTTP_202_ACCEPTED)
async def index_repository_legacy(
    payload: RepositoryIndexRequest,
    settings: SettingsDep,
    cache: RedisCacheDep,
) -> RepoIndexQueuedResponse:
    """Backward-compatible repository indexing endpoint."""
    return await index_repository(
        IndexRequest(github_url=str(payload.repository_url), repo_id=payload.repo_id),
        settings,
        cache,
    )


@router.get("/{repo_id}/status", response_model=RepoStatusResponse)
async def get_repository_status(repo_id: str, cache: RedisCacheDep) -> RepoStatusResponse:
    """Return repository indexing status from Redis and Celery."""
    meta = await cache.get_json(f"repo:{repo_id}:meta")
    if meta is not None:
        return RepoStatusResponse(repo_id=repo_id, status="ready", meta=meta)

    task_id = await cache.get_string(f"repo:{repo_id}:latest_task_id")
    if not task_id:
        return RepoStatusResponse(repo_id=repo_id, status="failed", meta=None)

    task_status = AsyncResult(task_id, app=celery_app).status
    if task_status == "FAILURE":
        status_value = "failed"
    elif task_status == "SUCCESS":
        status_value = "ready"
    else:
        status_value = "indexing"
    return RepoStatusResponse(repo_id=repo_id, status=status_value, meta=None)


@router.get("/{repo_id}", response_model=RepoStatusResponse)
async def get_repository_status_legacy(repo_id: str, cache: RedisCacheDep) -> RepoStatusResponse:
    """Backward-compatible repository status endpoint."""
    return await get_repository_status(repo_id, cache)


@router.get("/{repo_id}/files", response_model=RepoFilesResponse)
async def get_repository_files(repo_id: str, cache: RedisCacheDep) -> RepoFilesResponse:
    """Return indexed file summaries."""
    payload = await cache.get_json(f"repo:{repo_id}:files")
    if payload is None:
        return RepoFilesResponse(repo_id=repo_id, files=[])
    files = [RepoFileInfo.model_validate(item) for item in payload.get("files", [])]
    return RepoFilesResponse(repo_id=repo_id, files=files)


@router.delete("/{repo_id}", response_model=DeleteRepoResponse)
async def delete_repository(repo_id: str, settings: SettingsDep, cache: RedisCacheDep) -> DeleteRepoResponse:
    """Delete vector index, Redis metadata, and local checkout for a repository."""
    await CodeEmbedder(settings=settings).delete_repo_index(repo_id)
    await cache.delete_pattern(f"repo:{repo_id}:*")
    await cache.delete_pattern(f"readme:{repo_id}:*")
    await cache.delete_pattern(f"qa:{repo_id}:*")
    await cache.delete_pattern(f"hybrid:{repo_id}:*")
    await cache.delete(f"chat:{repo_id}:history")

    repo_path = _safe_repo_path(settings.repos_base_dir, repo_id)
    if repo_path.exists():
        shutil.rmtree(repo_path)
    return DeleteRepoResponse(repo_id=repo_id, deleted=True)


async def _remote_head_sha(github_url: str) -> str | None:
    """Return remote HEAD SHA when Git is available; otherwise None."""
    try:
        return await asyncio.to_thread(_remote_head_sha_sync, github_url)
    except Exception:
        return None


def _remote_head_sha_sync(github_url: str) -> str | None:
    from git.cmd import Git

    output = Git().ls_remote(github_url, "HEAD")
    return output.split()[0] if output.strip() else None


def _is_cached_index_current(meta: dict[str, Any] | None, github_url: str, remote_sha: str | None) -> bool:
    if meta is None:
        return False
    if meta.get("url") != github_url:
        return False
    if remote_sha is None:
        return bool(meta.get("commit_sha"))
    return meta.get("commit_sha") == remote_sha


def _cached_index_result(
    repo_id: str,
    meta: dict[str, Any],
    files_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    files = files_payload.get("files", []) if files_payload is not None else []
    file_list = [str(item.get("file_path", "")) for item in files if isinstance(item, dict)]
    return {
        "repo_id": repo_id,
        "commit_sha": meta.get("commit_sha", "unknown"),
        "total_files": int(meta.get("file_count", len(file_list))),
        "total_chunks": int(meta.get("chunk_count", 0)),
        "file_list": file_list,
    }


def _safe_repo_path(base_dir: Path, repo_id: str) -> Path:
    base_path = base_dir.resolve()
    repo_path = (base_path / repo_id).resolve()
    if repo_path != base_path and base_path not in repo_path.parents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid repository identifier.")
    return repo_path


__all__ = ["create_repo_id", "router"]
