"""Celery application and task definitions."""

from __future__ import annotations

import asyncio
import json
import shutil
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from celery import Celery

from app.config import get_settings
from app.crews.readme_crew import README_CACHE_TTL_SECONDS, ReadmeCrew, ReadmeResult
from app.rag.embedder import CodeEmbedder
from app.rag.indexer import IndexResult, RepoIndexer

TASK_PROGRESS_TTL_SECONDS = 86_400
CLEANUP_REPO_AGE_DAYS = 7
CLEANUP_PERIOD_SECONDS = 86_400

settings = get_settings()

celery_app = Celery(
    "repo_analyzer",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default",
    task_routes={
        "tasks.index_repo": {"queue": "indexing"},
        "app.tasks.index_repository": {"queue": "indexing"},
        "tasks.generate_readme": {"queue": "readme"},
    },
    beat_schedule={
        "cleanup-old-repos-daily": {
            "task": "tasks.cleanup_old_repos",
            "schedule": CLEANUP_PERIOD_SECONDS,
        },
    },
)


def _redis_client() -> Any | None:
    try:
        from redis import Redis
    except ImportError:
        return None
    return Redis.from_url(settings.redis_url, decode_responses=True)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _set_task_progress(
    task_id: str,
    status: str,
    percent: int,
    current_step: str,
    message: str,
    started_at: str | None = None,
    completed_steps: list[str] | None = None,
    error: str | None = None,
) -> None:
    """Write task progress in the Prompt 10 shape plus legacy API aliases."""
    client = _redis_client()
    if client is None or not task_id:
        return

    existing = _get_json_from_redis(client, f"task:{task_id}:progress") or {}
    now = _utc_now()
    payload: dict[str, Any] = {
        "task_id": task_id,
        "status": status,
        "percent": max(0, min(100, percent)),
        "progress": max(0, min(100, percent)),
        "current_step": current_step,
        "current_agent": current_step,
        "message": message,
        "started_at": started_at or str(existing.get("started_at") or now),
        "updated_at": now,
        "completed_steps": completed_steps if completed_steps is not None else list(existing.get("completed_steps", [])),
    }
    if error is not None:
        payload["error"] = error
    client.set(f"task:{task_id}:progress", json.dumps(payload), ex=TASK_PROGRESS_TTL_SECONDS)


@celery_app.task(bind=True, name="tasks.index_repo", max_retries=3, default_retry_delay=60)
def index_repo(self: Any, repo_id: str, github_url: str) -> dict[str, Any]:
    """Clone, chunk, embed, and cache repository metadata."""
    task_id = _task_id(self)
    started_at = _utc_now()
    completed_steps: list[str] = []
    current_step = "clone"
    percent = 10

    try:
        repo_indexer = RepoIndexer(settings=settings)

        _set_task_progress(
            task_id=task_id,
            status="indexing",
            percent=10,
            current_step="clone",
            message="Cloning or pulling repository.",
            started_at=started_at,
            completed_steps=completed_steps,
        )
        repo_path = repo_indexer.clone_repo(github_url=github_url, repo_id=repo_id)
        completed_steps.append("clone")

        current_step = "chunk"
        percent = 40
        _set_task_progress(
            task_id=task_id,
            status="indexing",
            percent=40,
            current_step="chunk",
            message="Chunking repository files.",
            started_at=started_at,
            completed_steps=completed_steps,
        )
        result, chunks = repo_indexer.index_local_repo(repo_id=repo_id, repo_path=repo_path)
        completed_steps.append("chunk")

        current_step = "embed"
        percent = 80
        _set_task_progress(
            task_id=task_id,
            status="indexing",
            percent=80,
            current_step="embed",
            message=f"Embedding and indexing {result.total_chunks} chunks into ChromaDB.",
            started_at=started_at,
            completed_steps=completed_steps,
        )
        asyncio.run(_embed_chunks(repo_id=repo_id, chunks=chunks, commit_sha=result.commit_sha))
        completed_steps.append("embed")

        current_step = "metadata"
        percent = 100
        _store_index_metadata(
            task_id=task_id,
            repo_id=repo_id,
            github_url=github_url,
            result=result,
            chunks=chunks,
        )
        completed_steps.append("metadata")
        _set_task_progress(
            task_id=task_id,
            status="ready",
            percent=100,
            current_step="metadata",
            message="Repository indexed successfully.",
            started_at=started_at,
            completed_steps=completed_steps,
        )
        return result.model_dump()
    except Exception as exc:
        _retry_or_fail(
            task=self,
            task_id=task_id,
            exc=exc,
            current_step=current_step,
            percent=percent,
            started_at=started_at,
            completed_steps=completed_steps,
        )
        raise exc


@celery_app.task(bind=True, name="tasks.generate_readme", max_retries=2)
def generate_readme(self: Any, repo_id: str) -> dict[str, Any]:
    """Generate and cache a repository README."""
    task_id = _task_id(self)
    started_at = _utc_now()
    completed_steps: list[str] = []
    current_step = "verify"
    percent = 10

    try:
        _set_task_progress(
            task_id=task_id,
            status="indexing",
            percent=10,
            current_step="verify",
            message="Verifying repository index metadata.",
            started_at=started_at,
            completed_steps=completed_steps,
        )
        metadata = _repo_metadata(repo_id)
        if metadata is None:
            raise ValueError(f"Repository '{repo_id}' is not indexed.")
        _touch_repo_metadata(repo_id=repo_id, metadata=metadata)
        completed_steps.append("verify")

        current_step = "readme"
        percent = 70
        _set_task_progress(
            task_id=task_id,
            status="indexing",
            percent=70,
            current_step="readme",
            message="Generating README with CrewAI.",
            started_at=started_at,
            completed_steps=completed_steps,
        )
        result = asyncio.run(ReadmeCrew(settings=settings).run(repo_id=repo_id))
        completed_steps.append("readme")

        current_step = "cache"
        percent = 90
        _set_task_progress(
            task_id=task_id,
            status="indexing",
            percent=90,
            current_step="cache",
            message="Storing README result in Redis.",
            started_at=started_at,
            completed_steps=completed_steps,
        )
        _store_readme_result(repo_id=repo_id, result=result)
        completed_steps.append("cache")

        _set_task_progress(
            task_id=task_id,
            status="ready",
            percent=100,
            current_step="complete",
            message="README generated successfully.",
            started_at=started_at,
            completed_steps=completed_steps,
        )
        return result.model_dump()
    except Exception as exc:
        _retry_or_fail(
            task=self,
            task_id=task_id,
            exc=exc,
            current_step=current_step,
            percent=percent,
            started_at=started_at,
            completed_steps=completed_steps,
        )
        raise exc


@celery_app.task(name="tasks.cleanup_old_repos")
def cleanup_old_repos() -> dict[str, Any]:
    """Delete repository data that has not been accessed in seven days."""
    client = _redis_client()
    if client is None:
        return {"scanned": 0, "deleted_count": 0, "deleted": [], "status": "redis_unavailable"}

    cutoff = datetime.now(UTC) - timedelta(days=CLEANUP_REPO_AGE_DAYS)
    scanned = 0
    deleted: list[str] = []

    for raw_key in client.scan_iter(match="repo:*:meta"):
        key = str(raw_key)
        scanned += 1
        repo_id = _repo_id_from_meta_key(key)
        if repo_id is None:
            continue

        metadata = _get_json_from_redis(client, key)
        if metadata is None:
            continue

        accessed_at = _parse_datetime(str(metadata.get("last_accessed_at") or metadata.get("indexed_at") or ""))
        if accessed_at is None or accessed_at >= cutoff:
            continue

        _delete_repo_resources(client=client, repo_id=repo_id)
        deleted.append(repo_id)

    return {"scanned": scanned, "deleted_count": len(deleted), "deleted": deleted, "status": "complete"}


@celery_app.task(name="app.tasks.index_repository")
def index_repository_task(payload: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible task entry point for repository indexing."""
    repo_id = str(payload.get("repo_id", "unknown"))
    github_url = str(payload.get("github_url") or payload.get("repository_url") or "")
    result, chunks = _index_repository_direct(repo_id=repo_id, github_url=github_url)
    _store_index_metadata(
        task_id="legacy",
        repo_id=repo_id,
        github_url=github_url,
        result=result,
        chunks=chunks,
    )
    return result.model_dump()


async def _embed_chunks(repo_id: str, chunks: list[Any], commit_sha: str) -> None:
    embedder = CodeEmbedder(settings=settings)
    try:
        await embedder.index_chunks(repo_id=repo_id, chunks=chunks, commit_sha=commit_sha)
    finally:
        await embedder.close()


def _index_repository_direct(repo_id: str, github_url: str) -> tuple[IndexResult, list[Any]]:
    repo_indexer = RepoIndexer(settings=settings)
    repo_path = repo_indexer.clone_repo(github_url=github_url, repo_id=repo_id)
    result, chunks = repo_indexer.index_local_repo(repo_id=repo_id, repo_path=repo_path)
    asyncio.run(_embed_chunks(repo_id=repo_id, chunks=chunks, commit_sha=result.commit_sha))
    return result, chunks


def _store_index_metadata(
    task_id: str,
    repo_id: str,
    github_url: str,
    result: IndexResult,
    chunks: list[Any],
) -> None:
    client = _redis_client()
    if client is None:
        return

    now = _utc_now()
    metadata = {
        "url": github_url,
        "commit_sha": result.commit_sha,
        "indexed_at": now,
        "last_accessed_at": now,
        "file_count": result.total_files,
        "chunk_count": result.total_chunks,
    }
    client.set(f"repo:{repo_id}:meta", json.dumps(metadata))
    client.set(f"repo:{repo_id}:files", json.dumps({"files": _file_summaries(chunks)}))
    client.set(f"repo:{repo_id}:commit_sha", result.commit_sha)
    client.set(f"repo:{repo_id}:latest_task_id", task_id)


def _store_readme_result(repo_id: str, result: ReadmeResult) -> None:
    client = _redis_client()
    if client is None:
        return

    commit_sha = _repo_commit_sha(repo_id) or "unknown"
    client.set(
        f"readme:{repo_id}:{commit_sha}",
        result.model_dump_json(),
        ex=README_CACHE_TTL_SECONDS,
    )
    client.set(f"repo:{repo_id}:readme_generated_at", _utc_now())


def _repo_metadata(repo_id: str) -> dict[str, Any] | None:
    client = _redis_client()
    if client is None:
        return None
    return _get_json_from_redis(client, f"repo:{repo_id}:meta")


def _repo_commit_sha(repo_id: str) -> str | None:
    client = _redis_client()
    if client is None:
        return None

    value = client.get(f"repo:{repo_id}:commit_sha")
    if value:
        return str(value)

    metadata = _get_json_from_redis(client, f"repo:{repo_id}:meta")
    if metadata is None:
        return None
    commit_sha = metadata.get("commit_sha")
    return str(commit_sha) if commit_sha else None


def _touch_repo_metadata(repo_id: str, metadata: dict[str, Any]) -> None:
    client = _redis_client()
    if client is None:
        return
    metadata["last_accessed_at"] = _utc_now()
    client.set(f"repo:{repo_id}:meta", json.dumps(metadata))


def _delete_repo_resources(client: Any, repo_id: str) -> None:
    asyncio.run(_delete_chroma_collection(repo_id))
    _delete_pattern(client, f"repo:{repo_id}:*")
    _delete_pattern(client, f"readme:{repo_id}:*")
    _delete_pattern(client, f"qa:{repo_id}:*")
    _delete_pattern(client, f"hybrid:{repo_id}:*")
    client.delete(f"chat:{repo_id}:history")

    repo_path = _safe_repo_path(settings.repos_base_dir, repo_id)
    if repo_path.exists():
        shutil.rmtree(repo_path)


async def _delete_chroma_collection(repo_id: str) -> None:
    embedder = CodeEmbedder(settings=settings)
    try:
        await embedder.delete_repo_index(repo_id)
    finally:
        await embedder.close()


def _retry_or_fail(
    task: Any,
    task_id: str,
    exc: Exception,
    current_step: str,
    percent: int,
    started_at: str,
    completed_steps: list[str],
) -> None:
    retries = int(getattr(task.request, "retries", 0))
    max_retries = int(getattr(task, "max_retries", 0) or 0)
    if retries < max_retries:
        base_delay = int(getattr(task, "default_retry_delay", 60) or 60)
        countdown = base_delay * (2**retries)
        _set_task_progress(
            task_id=task_id,
            status="retrying",
            percent=percent,
            current_step=current_step,
            message=f"{exc}. Retrying in {countdown} seconds.",
            started_at=started_at,
            completed_steps=completed_steps,
            error=str(exc),
        )
        raise task.retry(exc=exc, countdown=countdown)

    _set_task_progress(
        task_id=task_id,
        status="failed",
        percent=percent,
        current_step=current_step,
        message="Task failed after all retry attempts.",
        started_at=started_at,
        completed_steps=completed_steps,
        error=str(exc),
    )


def _get_json_from_redis(client: Any, key: str) -> dict[str, Any] | None:
    value = client.get(key)
    if value is None:
        return None
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _delete_pattern(client: Any, pattern: str) -> int:
    deleted = 0
    for key in client.scan_iter(match=pattern):
        deleted += int(client.delete(key))
    return deleted


def _file_summaries(chunks: list[Any]) -> list[dict[str, Any]]:
    chunk_counts = Counter(str(chunk.file_path) for chunk in chunks)
    languages: dict[str, str] = {}
    for chunk in chunks:
        languages.setdefault(str(chunk.file_path), str(chunk.language))
    return [
        {
            "file_path": file_path,
            "language": languages.get(file_path, "text"),
            "chunk_count": count,
        }
        for file_path, count in sorted(chunk_counts.items())
    ]


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _repo_id_from_meta_key(key: str) -> str | None:
    prefix = "repo:"
    suffix = ":meta"
    if not key.startswith(prefix) or not key.endswith(suffix):
        return None
    repo_id = key[len(prefix) : -len(suffix)]
    return repo_id or None


def _safe_repo_path(base_dir: Path, repo_id: str) -> Path:
    base_path = base_dir.resolve()
    repo_path = (base_path / repo_id).resolve()
    if repo_path == base_path or base_path not in repo_path.parents:
        raise ValueError(f"Invalid repository identifier: {repo_id}")
    return repo_path


def _task_id(task: Any) -> str:
    request_id = getattr(task.request, "id", None)
    return str(request_id or "unknown")


__all__ = [
    "celery_app",
    "cleanup_old_repos",
    "generate_readme",
    "index_repo",
    "index_repository_task",
]
