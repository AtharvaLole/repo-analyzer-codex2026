"""CrewAI-oriented orchestration for repository engineering answers."""

from typing import Protocol

from app.config import Settings
from app.models.request import ChatRequest
from app.models.response import ChatResponse, CodeCitation
from app.rag.retriever import HybridRetriever, RetrievedChunk


class RetrieverProtocol(Protocol):
    """Retriever behavior required by the orchestrator."""

    async def search(self, repo_id: str, query: str, top_k: int) -> list[RetrievedChunk]:
        """Return relevant repository chunks."""


class SoftwareEngineeringOrchestrator:
    """Coordinate retrieval, analysis, and answer synthesis."""

    def __init__(self, retriever: RetrieverProtocol | None = None) -> None:
        self._retriever = retriever

    async def answer(self, request: ChatRequest, settings: Settings) -> ChatResponse:
        retriever = self._retriever or HybridRetriever(settings=settings)
        chunks = await retriever.search(
            repo_id=request.repo_id,
            query=request.message,
            top_k=request.top_k,
        )
        citations = [
            CodeCitation(
                repo_id=chunk.repo_id,
                file_path=chunk.file_path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                score=chunk.score,
                text=chunk.content,
            )
            for chunk in chunks
        ]
        answer = self._build_grounded_answer(request.message, chunks)
        return ChatResponse(
            repo_id=request.repo_id,
            answer=answer,
            citations=citations,
            agent_trace=["retrieval", "analysis", "synthesis"],
        )

    def _build_grounded_answer(self, question: str, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return (
                "I could not find indexed code context for this repository yet. "
                "Queue indexing first, then ask the question again."
            )
        files = ", ".join({chunk.file_path for chunk in chunks[:3]})
        return (
            f"Based on the retrieved repository context, the question was: {question}\n\n"
            f"The most relevant files are {files}. Use the returned citations for exact lines."
        )


__all__ = ["RetrieverProtocol", "SoftwareEngineeringOrchestrator"]
