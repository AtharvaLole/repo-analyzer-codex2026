"""Agent orchestration tests."""

import pytest

from app.agents.orchestrator import SoftwareEngineeringOrchestrator
from app.config import get_settings
from app.models.request import ChatRequest
from app.rag.retriever import RetrievedChunk


class FakeRetriever:
    async def search(self, repo_id: str, query: str, top_k: int) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                id="demo:app.py:1-3",
                repo_id=repo_id,
                file_path="app.py",
                start_line=1,
                end_line=3,
                content="def main() -> None: ...",
                score=1.0,
            ),
        ]


@pytest.mark.asyncio
async def test_orchestrator_returns_citations() -> None:
    orchestrator = SoftwareEngineeringOrchestrator(retriever=FakeRetriever())
    request = ChatRequest(repo_id="demo", message="Where is the entry point?")

    response = await orchestrator.answer(request, get_settings())

    assert response.repo_id == "demo"
    assert response.citations[0].file_path == "app.py"
