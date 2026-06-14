"""Retrieval agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.agents import llm_fast, make_agent
from app.agents.tools import list_repo_files, search_codebase
from app.rag.retriever import HybridRetriever, RetrievedChunk

if TYPE_CHECKING:
    from crewai import Agent


@dataclass(slots=True)
class RetrievalAgent:
    """Retrieve code context for downstream agents."""

    retriever: HybridRetriever

    async def run(self, repo_id: str, query: str, top_k: int) -> list[RetrievedChunk]:
        return await self.retriever.search(repo_id=repo_id, query=query, top_k=top_k)


def create_retrieval_agent(repo_id: str) -> Agent:
    """Create the repository retrieval specialist agent."""
    return make_agent(
        role="Senior Codebase Retrieval Specialist",
        goal="Find the most relevant code chunks for any query using hybrid search",
        backstory=(
            "Expert at semantic and keyword search over large codebases. "
            "Always cites exact file paths and line numbers."
        ),
        tools=[search_codebase, list_repo_files],
        llm=llm_fast,
    )


__all__ = ["RetrievalAgent", "create_retrieval_agent"]
