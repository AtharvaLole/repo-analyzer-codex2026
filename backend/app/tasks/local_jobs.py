"""Local background jobs for the demo runtime.

These jobs replace Celery for the judge/demo version. They keep the same Redis
progress keys used by the frontend, but run inside the FastAPI process.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.crews.readme_crew import README_CACHE_TTL_SECONDS, ReadmeCrew
from app.rag.embedder import CodeEmbedder
from app.rag.indexer import IndexResult, RepoIndexer

TASK_PROGRESS_TTL_SECONDS = 86_400


def utc_now() -> str:
    """Return an ISO UTC timestamp."""
    return datetime.now(UTC).isoformat()


async def run_index_repo_job(repo_id: str, github_url: str, task_id: str, settings: Settings | None = None) -> None:
    """Index a repository and write progress to Redis."""
    settings = settings or get_settings()
    started_at = utc_now()
    completed_steps: list[str] = []
    chunks: list[Any] = []

    try:
        indexer = RepoIndexer(settings=settings)

        await set_task_progress(
            task_id=task_id,
            status="indexing",
            percent=10,
            current_step="clone",
            message="Cloning or pulling repository.",
            started_at=started_at,
            completed_steps=completed_steps,
        )
        repo_path = await asyncio.to_thread(indexer.clone_repo, github_url, repo_id)
        completed_steps.append("clone")

        await set_task_progress(
            task_id=task_id,
            status="indexing",
            percent=40,
            current_step="chunk",
            message="Parsing and chunking repository files.",
            started_at=started_at,
            completed_steps=completed_steps,
        )
        result, chunks = await asyncio.to_thread(indexer.index_local_repo, repo_id, repo_path)
        completed_steps.append("chunk")

        await set_task_progress(
            task_id=task_id,
            status="indexing",
            percent=80,
            current_step="embed",
            message=f"Embedding and indexing {result.total_chunks} chunks.",
            started_at=started_at,
            completed_steps=completed_steps,
        )
        embedder = CodeEmbedder(settings=settings)
        try:
            await embedder.index_chunks(repo_id=repo_id, chunks=chunks, commit_sha=result.commit_sha)
        finally:
            await embedder.close()
        completed_steps.append("embed")

        await store_index_metadata(
            task_id=task_id,
            repo_id=repo_id,
            github_url=github_url,
            result=result,
            chunks=chunks,
            settings=settings,
        )
        completed_steps.append("metadata")
        await set_task_progress(
            task_id=task_id,
            status="ready",
            percent=100,
            current_step="complete",
            message="Repository indexed successfully.",
            started_at=started_at,
            completed_steps=completed_steps,
        )
    except Exception as exc:
        await set_task_progress(
            task_id=task_id,
            status="failed",
            percent=80 if chunks else 10,
            current_step="failed",
            message=str(exc),
            started_at=started_at,
            completed_steps=completed_steps,
            error=str(exc),
        )


async def run_generate_readme_job(repo_id: str, task_id: str, settings: Settings | None = None) -> None:
    """Generate a README and write progress to Redis."""
    settings = settings or get_settings()
    started_at = utc_now()
    completed_steps: list[str] = []

    try:
        await set_task_progress(
            task_id=task_id,
            status="indexing",
            percent=20,
            current_step="verify",
            message="Verifying repository index.",
            started_at=started_at,
            completed_steps=completed_steps,
        )
        meta = await get_json(f"repo:{repo_id}:meta", settings=settings)
        if meta is None:
            raise ValueError(f"Repository '{repo_id}' is not indexed.")
        completed_steps.append("verify")

        await set_task_progress(
            task_id=task_id,
            status="indexing",
            percent=70,
            current_step="readme",
            message="Generating README.",
            started_at=started_at,
            completed_steps=completed_steps,
        )
        result = await ReadmeCrew(settings=settings).run(repo_id=repo_id)
        completed_steps.append("readme")

        commit_sha = str(meta.get("commit_sha") or "unknown")
        await set_string(
            f"readme:{repo_id}:{commit_sha}",
            result.model_dump_json(),
            ttl_seconds=README_CACHE_TTL_SECONDS,
            settings=settings,
        )
        await set_string(f"repo:{repo_id}:readme_generated_at", utc_now(), settings=settings)
        completed_steps.append("cache")

        await set_task_progress(
            task_id=task_id,
            status="ready",
            percent=100,
            current_step="complete",
            message="README generated successfully.",
            started_at=started_at,
            completed_steps=completed_steps,
        )
    except Exception as exc:
        await set_task_progress(
            task_id=task_id,
            status="failed",
            percent=20,
            current_step="failed",
            message=str(exc),
            started_at=started_at,
            completed_steps=completed_steps,
            error=str(exc),
        )


async def store_index_metadata(
    task_id: str,
    repo_id: str,
    github_url: str,
    result: IndexResult,
    chunks: list[Any],
    settings: Settings,
) -> None:
    """Store repository metadata and file summaries."""
    now = utc_now()
    metadata = {
        "url": github_url,
        "commit_sha": result.commit_sha,
        "indexed_at": now,
        "last_accessed_at": now,
        "file_count": result.total_files,
        "chunk_count": result.total_chunks,
    }
    await set_json_persistent(f"repo:{repo_id}:meta", metadata, settings=settings)
    await set_json_persistent(f"repo:{repo_id}:files", {"files": file_summaries(chunks)}, settings=settings)
    await set_string(f"repo:{repo_id}:commit_sha", result.commit_sha, settings=settings)
    await set_string(f"repo:{repo_id}:latest_task_id", task_id, settings=settings)


async def set_task_progress(
    task_id: str,
    status: str,
    percent: int,
    current_step: str,
    message: str,
    started_at: str,
    completed_steps: list[str],
    error: str | None = None,
) -> None:
    """Write progress in the shape expected by the frontend."""
    payload: dict[str, Any] = {
        "task_id": task_id,
        "status": status,
        "percent": max(0, min(100, percent)),
        "progress": max(0, min(100, percent)),
        "current_step": current_step,
        "current_agent": current_step,
        "message": message,
        "started_at": started_at,
        "updated_at": utc_now(),
        "completed_steps": completed_steps,
    }
    if error is not None:
        payload["error"] = error
    await set_json(f"task:{task_id}:progress", payload, ttl_seconds=TASK_PROGRESS_TTL_SECONDS)


async def get_json(key: str, settings: Settings) -> dict[str, Any] | None:
    from redis.asyncio import Redis

    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        raw = await client.get(key)
        if raw is None:
            return None
        parsed = json.loads(str(raw))
        return parsed if isinstance(parsed, dict) else None
    finally:
        await client.aclose()


async def set_json(key: str, value: dict[str, Any], ttl_seconds: int, settings: Settings | None = None) -> None:
    from redis.asyncio import Redis

    settings = settings or get_settings()
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.set(key, json.dumps(value), ex=ttl_seconds)
    finally:
        await client.aclose()


async def set_json_persistent(key: str, value: dict[str, Any], settings: Settings) -> None:
    from redis.asyncio import Redis

    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.set(key, json.dumps(value))
    finally:
        await client.aclose()


async def set_string(
    key: str,
    value: str,
    ttl_seconds: int | None = None,
    settings: Settings | None = None,
) -> None:
    from redis.asyncio import Redis

    settings = settings or get_settings()
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        if ttl_seconds is None:
            await client.set(key, value)
        else:
            await client.set(key, value, ex=ttl_seconds)
    finally:
        await client.aclose()


def file_summaries(chunks: list[Any]) -> list[dict[str, Any]]:
    """Summarize chunks by file for the frontend file tree."""
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


async def cleanup_repo(repo_id: str, settings: Settings) -> None:
    """Delete local checkout and vector collection for a repo."""
    await CodeEmbedder(settings=settings).delete_repo_index(repo_id)
    repo_path = safe_repo_path(settings.repos_base_dir, repo_id)
    if repo_path.exists():
        await asyncio.to_thread(shutil.rmtree, repo_path)


def safe_repo_path(base_dir: Path, repo_id: str) -> Path:
    """Resolve a repo path while preventing path traversal."""
    base_path = base_dir.resolve()
    repo_path = (base_path / repo_id).resolve()
    if repo_path == base_path or base_path not in repo_path.parents:
        raise ValueError(f"Invalid repository identifier: {repo_id}")
    return repo_path


__all__ = [
    "cleanup_repo",
    "file_summaries",
    "run_generate_readme_job",
    "run_index_repo_job",
    "safe_repo_path",
    "set_task_progress",
    "store_index_metadata",
    "utc_now",
]
