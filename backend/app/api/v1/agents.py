"""Agent health and background task status endpoints."""

from __future__ import annotations

from celery.result import AsyncResult
from fastapi import APIRouter

from app.dependencies import RedisCacheDep
from app.models.response import AgentStatus, AgentTaskStatusResponse, AgentsStatusResponse
from app.tasks import celery_app

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/status", response_model=AgentsStatusResponse)
async def get_agents_status() -> AgentsStatusResponse:
    """Return the configured agent roster."""
    agents = [
        AgentStatus(name="retrieval", status="ready"),
        AgentStatus(name="code_analysis", status="ready"),
        AgentStatus(name="security", status="ready"),
        AgentStatus(name="test_generation", status="ready"),
        AgentStatus(name="readme", status="ready"),
        AgentStatus(name="dependency", status="ready"),
        AgentStatus(name="refactor", status="ready"),
        AgentStatus(name="review", status="ready"),
    ]
    return AgentsStatusResponse(agents=agents)


@router.get("/status/{task_id}", response_model=AgentTaskStatusResponse)
async def get_agent_task_status(task_id: str, cache: RedisCacheDep) -> AgentTaskStatusResponse:
    """Return Celery task status plus agent progress details from Redis."""
    progress = await cache.get_json(f"task:{task_id}:progress") or {}
    celery_status = AsyncResult(task_id, app=celery_app).status
    status_value = str(progress.get("status") or _normalize_celery_status(celery_status))
    return AgentTaskStatusResponse(
        task_id=task_id,
        status=status_value,
        progress=int(progress.get("progress", progress.get("percent", 100 if status_value == "ready" else 0))),
        current_agent=str(progress.get("current_agent") or progress.get("current_step") or ""),
        completed_steps=list(progress.get("completed_steps", [])),
        current_step=str(progress.get("current_step")) if progress.get("current_step") is not None else None,
        message=str(progress.get("message")) if progress.get("message") is not None else None,
        started_at=str(progress.get("started_at")) if progress.get("started_at") is not None else None,
        updated_at=str(progress.get("updated_at")) if progress.get("updated_at") is not None else None,
    )


def _normalize_celery_status(status: str) -> str:
    if status == "SUCCESS":
        return "ready"
    if status == "FAILURE":
        return "failed"
    if status in {"PENDING", "STARTED", "RETRY", "RECEIVED"}:
        return "indexing"
    return status.lower()


__all__ = ["router"]
