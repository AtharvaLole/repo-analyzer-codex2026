"""Chat endpoints for repository question answering."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.dependencies import RedisCacheDep
from app.models.request import ChatRequest
from app.models.response import ChatResponse, Citation
from app.rag.retriever import HybridRetriever, SearchResult
from app.config import get_settings

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

    response = await _run_retrieval_chat(repo_id=payload.repo_id, question=payload.question)
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
    response = await _run_retrieval_chat(repo_id=payload.repo_id, question=payload.question)
    await _store_chat_history(payload.repo_id, payload.question, response, cache)
    for token in response.answer.split():
        yield f"{token} "
    yield "\n"


async def _run_retrieval_chat(repo_id: str, question: str) -> ChatResponse:
    settings = get_settings()
    targeted_results = _targeted_repo_context(repo_id=repo_id, question=question, repo_base=settings.repos_base_dir)
    search_query = _expand_query(question)
    retrieved_results = await HybridRetriever(settings=settings).hybrid_search(
        repo_id=repo_id,
        query=search_query,
        top_k=16,
    )
    results = _dedupe_results([*targeted_results, *retrieved_results])
    filtered = _prefer_source_files(results)
    citations = [_citation_from_result(result) for result in filtered[:6]]
    answer = await _generate_answer(question=question, results=filtered[:6])
    return ChatResponse(
        repo_id=repo_id,
        answer=answer,
        citations=citations,
        confidence=78 if citations else 35,
        intent="qa",
        active_agents=["retrieval", "code_analysis"],
        agent_trace=["intent", "retrieval", "local_analysis"],
    )


def _expand_query(question: str) -> str:
    lowered = question.lower()
    extra_terms: list[str] = []
    if any(term in lowered for term in ("auth", "login", "jwt", "token", "password", "role")):
        extra_terms.extend(
            [
                "auth",
                "authentication",
                "login",
                "register",
                "jwt",
                "token",
                "middleware",
                "role",
                "user",
                "controller",
                "routes",
                "generateToken",
            ],
        )
    if any(term in lowered for term in ("api", "endpoint", "route")):
        extra_terms.extend(["routes", "controller", "server", "app"])
    if any(term in lowered for term in ("database", "model", "schema", "mongo")):
        extra_terms.extend(["model", "schema", "mongoose", "database"])
    if not extra_terms:
        return question
    return f"{question} {' '.join(extra_terms)}"


def _targeted_repo_context(repo_id: str, question: str, repo_base: Path) -> list[SearchResult]:
    repo_path = (repo_base / repo_id).resolve()
    if not repo_path.exists():
        return []

    lowered = question.lower()
    target_terms = _target_terms_for_question(lowered)
    if not target_terms:
        return []

    matches: list[Path] = []
    for file_path in repo_path.rglob("*"):
        if not file_path.is_file() or _is_noisy_path(file_path):
            continue
        relative = file_path.relative_to(repo_path).as_posix().lower()
        if any(term in relative for term in target_terms):
            matches.append(file_path)

    results: list[SearchResult] = []
    for index, file_path in enumerate(matches[:8]):
        content = _read_text_preview(file_path)
        if not content.strip():
            continue
        relative_path = file_path.relative_to(repo_path).as_posix()
        results.append(
            SearchResult(
                chunk_id=f"{repo_id}:{relative_path}:1:targeted",
                content=content,
                file_path=relative_path,
                start_line=1,
                end_line=min(160, max(1, content.count("\n") + 1)),
                chunk_type="module",
                language=_language_from_path(relative_path),
                name=file_path.name,
                score=2.0 - (index * 0.01),
                search_type="hybrid",
            ),
        )
    return results


def _target_terms_for_question(lowered: str) -> list[str]:
    if any(term in lowered for term in ("entry", "start", "main", "bootstrap")):
        return ["server.", "app.", "main.", "package.json", "layout.", "page."]
    if any(term in lowered for term in ("request", "lifecycle", "flow", "api", "endpoint", "route")):
        return ["routes/", "controllers/", "middleware/", "services/", "server.", "app."]
    if any(term in lowered for term in ("auth", "login", "jwt", "token", "password", "role")):
        return ["auth", "token", "role", "user.model", "middleware"]
    if any(term in lowered for term in ("security", "risk", "secret", "injection", "vulnerab")):
        return ["auth", "middleware", "token", "user.model", "controller", ".env", "credentials"]
    if any(term in lowered for term in ("run", "install", "setup", "local", "start")):
        return ["readme", "how_to_run", "package.json", "server.", "next.config"]
    if any(term in lowered for term in ("next", "frontend", "ui", "page", "component")):
        return ["frontend", "src/app", "components", "lib/api", "next.config"]
    if any(term in lowered for term in ("database", "schema", "model", "mongo", "mongoose")):
        return ["models/", "config/db", "mongoose", "record.model", "user.model"]
    if any(term in lowered for term in ("test", "coverage", "qa")):
        return ["test", "spec", "controllers/", "routes/", "models/"]
    return ["readme", "server.", "app.", "routes/", "controllers/"]


def _is_noisy_path(file_path: Path) -> bool:
    path = file_path.as_posix().lower()
    return any(
        part in path
        for part in (
            "node_modules/",
            ".git/",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            ".svg",
            ".ico",
        )
    )


def _read_text_preview(file_path: Path) -> str:
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    lines = text.splitlines()
    return "\n".join(lines[:160])


def _language_from_path(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".py": "python",
        ".json": "json",
        ".md": "markdown",
        ".css": "css",
    }.get(suffix, "text")


def _dedupe_results(results: list[SearchResult]) -> list[SearchResult]:
    seen: set[str] = set()
    deduped: list[SearchResult] = []
    for result in results:
        key = f"{result.file_path}:{result.start_line}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(result)
    return deduped


def _prefer_source_files(results: list[SearchResult]) -> list[SearchResult]:
    noisy_parts = (
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        ".svg",
        ".ico",
        "credentials",
        "deployment",
    )
    source_results = [
        result
        for result in results
        if not any(part in result.file_path.lower() for part in noisy_parts)
    ]
    return sorted(source_results or results, key=_result_priority)


def _result_priority(result: SearchResult) -> tuple[int, float]:
    path = result.file_path.lower()
    priority_terms = ("auth", "token", "middleware", "route", "controller", "model", "service", "readme")
    priority = 0 if any(term in path for term in priority_terms) else 1
    return (priority, -result.score)


def _citation_from_result(result: SearchResult) -> Citation:
    return Citation(
        file_path=result.file_path,
        start_line=result.start_line,
        end_line=result.end_line,
        snippet=result.content[:1_500],
        relevance=f"{result.search_type}:{result.score:.4f}",
    )


def _answer_from_results(question: str, results: list[SearchResult]) -> str:
    if not results:
        return (
            "I could not find matching indexed code for that question. "
            "Try asking about a route, file, function, dependency, or feature name."
        )

    lines = [
        "I found the most relevant indexed code for your question.",
        "",
        f"Question: {question}",
        "",
        "Key references:",
    ]
    for result in results:
        summary = _compact_snippet(result.content)
        lines.append(f"- `{result.file_path}:{result.start_line}-{result.end_line}` - {summary}")
    lines.extend(
        [
            "",
            "Open the citations below to inspect the exact snippets.",
        ],
    )
    return "\n".join(lines)


async def _generate_answer(question: str, results: list[SearchResult]) -> str:
    settings = get_settings()
    if settings.openai_api_key is None:
        return _answer_from_results(question=question, results=results[:5])

    context = "\n\n".join(
        (
            f"FILE: {result.file_path} lines {result.start_line}-{result.end_line}\n"
            f"{result.content[:2_000]}"
        )
        for result in results[:6]
    )
    prompt = (
        "You are a concise codebase analysis assistant. Answer using only the provided repository context. "
        "Cite file paths and line ranges for every concrete claim. Keep the answer under 350 words.\n\n"
        f"Question: {question}\n\n"
        f"Repository context:\n{context}"
    )
    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=700,
            timeout=12,
            max_retries=0,
        )
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=15)
        content = getattr(response, "content", response)
        if isinstance(content, list):
            return "\n".join(str(item) for item in content)
        text = str(content).strip()
        return text or _answer_from_results(question=question, results=results[:5])
    except Exception:
        return _answer_from_results(question=question, results=results[:5])


def _compact_snippet(content: str) -> str:
    stripped_lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not stripped_lines:
        return "Relevant indexed chunk."
    summary = " ".join(stripped_lines[:3])
    if len(summary) > 220:
        return f"{summary[:217]}..."
    return summary


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
