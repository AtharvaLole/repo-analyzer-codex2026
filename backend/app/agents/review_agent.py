"""Code review agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.agents import llm_powerful, make_agent
from app.agents.tools import read_file, search_codebase
from app.rag.retriever import RetrievedChunk

if TYPE_CHECKING:
    from crewai import Agent


@dataclass(slots=True)
class ReviewAgent:
    """Produce review-oriented observations from code context."""

    name: str = "review"

    async def run(self, chunks: list[RetrievedChunk]) -> list[str]:
        return [
            f"Review {chunk.file_path}:{chunk.start_line}-{chunk.end_line} for edge cases and error handling."
            for chunk in chunks
        ]


def create_review_agent(repo_id: str) -> Agent:
    """Create the final principal engineer review agent."""
    return make_agent(
        role="Principal Engineer (Reviewer)",
        goal="Review all agent outputs for accuracy, correctness, and quality before delivery",
        backstory=(
            "Final quality gate. Checks that all claims are grounded in actual code, "
            "not hallucinations. Adds confidence scores."
        ),
        tools=[search_codebase, read_file],
        llm=llm_powerful,
    )


__all__ = ["ReviewAgent", "create_review_agent"]
