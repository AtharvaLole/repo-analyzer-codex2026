"""CrewAI repository Q&A crew."""

from __future__ import annotations

import asyncio
import hashlib
import re
from typing import Any

from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.crews.cache import CrewCache
from app.rag.retriever import HybridRetriever, SearchResult

QA_CACHE_TTL_SECONDS = 3_600


class Citation(BaseModel):
    """Code citation returned by Q&A runs."""

    file_path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    snippet: str
    relevance: str


class QAResult(BaseModel):
    """Repository Q&A result."""

    answer: str
    citations: list[Citation]
    confidence: int = Field(ge=0, le=100)


class QACrew:
    """Sequential CrewAI workflow for repository question answering."""

    def __init__(self, settings: Settings | None = None, cache: CrewCache | None = None) -> None:
        self.settings = settings or get_settings()
        self.cache = cache

    async def run(self, repo_id: str, question: str) -> QAResult:
        """Answer a repository question using retrieval, analysis, and review agents."""
        cache = self.cache or CrewCache(settings=self.settings)
        try:
            cache_key = f"qa:{repo_id}:{hashlib.sha256(question.encode('utf-8')).hexdigest()[:16]}"
            cached = await cache.get_model(cache_key, QAResult)
            if cached is not None:
                return cached

            crew = self._build_crew(repo_id=repo_id, question=question)
            citation_results_task = asyncio.create_task(
                self._candidate_citations(repo_id=repo_id, question=question),
            )
            output = await asyncio.to_thread(crew.kickoff)
            answer = _crew_output_to_text(output)
            citations = await citation_results_task
            if not citations:
                citations = _extract_inline_citations(answer)

            result = QAResult(
                answer=answer,
                citations=citations,
                confidence=_extract_confidence(answer),
            )
            await cache.set_model(cache_key, result, ttl_seconds=QA_CACHE_TTL_SECONDS)
            return result
        finally:
            if self.cache is None:
                await cache.close()

    async def _candidate_citations(self, repo_id: str, question: str) -> list[Citation]:
        try:
            results = await HybridRetriever(settings=self.settings).hybrid_search(
                repo_id=repo_id,
                query=question,
                top_k=6,
            )
        except Exception:
            return []
        return [_citation_from_search_result(result) for result in results]

    def _build_crew(self, repo_id: str, question: str) -> Any:
        from crewai import Crew, Process, Task

        from app.agents import (
            create_code_analysis_agent,
            create_retrieval_agent,
            create_review_agent,
        )

        retrieval_agent = create_retrieval_agent(repo_id)
        code_analysis_agent = create_code_analysis_agent(repo_id)
        review_agent = create_review_agent(repo_id)

        retrieval_task = Task(
            description=(
                f"Find all code relevant to this question: '{question}' in repo {repo_id}. "
                "Return file paths, line numbers, and content."
            ),
            expected_output="Relevant code snippets with file paths and line numbers.",
            agent=retrieval_agent,
        )
        answer_task = Task(
            description=(
                f"Using the retrieved code, answer this question with precision: '{question}'. "
                "Cite every claim with file:line references."
            ),
            expected_output="Precise answer with file:line citations.",
            agent=code_analysis_agent,
            context=[retrieval_task],
        )
        review_task = Task(
            description=(
                "Verify the answer is grounded in the actual code. Add a confidence score "
                "and flag any uncertain claims."
            ),
            expected_output="Reviewed answer with confidence score and uncertainty notes.",
            agent=review_agent,
            context=[retrieval_task, answer_task],
        )

        return Crew(
            agents=[retrieval_agent, code_analysis_agent, review_agent],
            tasks=[retrieval_task, answer_task, review_task],
            process=Process.sequential,
            verbose=False,
        )


def build_qa_crew(repo_id: str, question: str) -> Any:
    """Build the underlying sequential CrewAI Q&A crew."""
    return QACrew()._build_crew(repo_id=repo_id, question=question)


def _crew_output_to_text(output: Any) -> str:
    for attribute in ("raw", "result", "output"):
        value = getattr(output, attribute, None)
        if isinstance(value, str) and value.strip():
            return value
    return str(output)


def _citation_from_search_result(result: SearchResult) -> Citation:
    return Citation(
        file_path=result.file_path,
        start_line=result.start_line,
        end_line=result.end_line,
        snippet=result.content[:1_500],
        relevance=f"{result.search_type}:{result.score:.4f}",
    )


def _extract_inline_citations(answer: str) -> list[Citation]:
    pattern = re.compile(r"(?P<path>[\w./\\-]+\.\w+):(?P<line>\d+)(?:-(?P<end>\d+))?")
    citations: list[Citation] = []
    for match in pattern.finditer(answer):
        start_line = int(match.group("line"))
        end_line = int(match.group("end") or start_line)
        citations.append(
            Citation(
                file_path=match.group("path"),
                start_line=start_line,
                end_line=end_line,
                snippet="",
                relevance="mentioned in reviewed answer",
            ),
        )
    return citations


def _extract_confidence(content: str) -> int:
    match = re.search(r"confidence(?:\s+score)?\D{0,20}(\d{1,3})", content, flags=re.IGNORECASE)
    if match is None:
        return 70
    return max(0, min(100, int(match.group(1))))


__all__ = ["QA_CACHE_TTL_SECONDS", "Citation", "QACrew", "QAResult", "build_qa_crew"]
