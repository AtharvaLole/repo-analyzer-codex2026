"""Chat endpoints for repository question answering."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.dependencies import RedisCacheDep
from app.graph.workflow import run_workflow
from app.models.request import ChatRequest
from app.models.response import ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=None)
async def chat(payload: ChatRequest, cache: RedisCacheDep) -> ChatResponse | StreamingResponse:
    """Run the workflow for a repository-aware question."""
    await _ensure_indexed(payload.repo_id, cache)
    if payload.stream:
        return StreamingResponse(
            _stream_workflow(payload=payload, cache=cache),
            media_type="text/plain",
        )

    state = await run_workflow(repo_id=payload.repo_id, query=payload.question)
    response = _chat_response_from_state(payload.repo_id, state)
    await _store_chat_history(payload.repo_id, payload.question, response, cache)
    return response


@router.get("/history/{repo_id}")
async def get_chat_history(repo_id: str, cache: RedisCacheDep) -> dict[str, list[dict]]:
    """Return the last 20 Q&A pairs for a repository."""
    return {"history": await cache.list_range_json(f"chat:{repo_id}:history", 0, 19)}


async def _ensure_indexed(repo_id: str, cache: RedisCacheDep) -> None:
    meta = await cache.get_json(f"repo:{repo_id}:meta")
    if meta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository is not indexed yet.",
        )
    meta["last_accessed_at"] = datetime.now(UTC).isoformat()
    await cache.set_json_persistent(f"repo:{repo_id}:meta", meta)


async def _stream_workflow(payload: ChatRequest, cache: RedisCacheDep) -> AsyncIterator[str]:
    state = await run_workflow(repo_id=payload.repo_id, query=payload.question)
    response = _chat_response_from_state(payload.repo_id, state)
    await _store_chat_history(payload.repo_id, payload.question, response, cache)
    for token in response.answer.split():
        yield f"{token} "
    yield "\n"


def _chat_response_from_state(repo_id: str, state: dict) -> ChatResponse:
    return ChatResponse(
        repo_id=repo_id,
        answer=str(state.get("final_answer") or state.get("code_analysis") or ""),
        citations=list(state.get("citations", [])),
        confidence=int(state.get("confidence", 0)),
        intent=str(state.get("intent", "unknown")),
        active_agents=list(state.get("active_agents", [])),
        agent_trace=list(state.get("completed_steps", [])),
    )


async def _store_chat_history(
    repo_id: str,
    question: str,
    response: ChatResponse,
    cache: RedisCacheDep,
) -> None:
    await cache.list_push_json(
        f"chat:{repo_id}:history",
        {
            "question": question,
            "answer": response.answer,
            "confidence": response.confidence,
            "intent": response.intent,
            "created_at": datetime.now(UTC).isoformat(),
            "citations": [json.loads(item.model_dump_json()) for item in response.citations],
        },
        max_length=20,
    )


__all__ = ["router"]
