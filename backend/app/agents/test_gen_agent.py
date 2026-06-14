"""Test generation agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.agents import llm_powerful, make_agent
from app.agents.tools import read_file, search_codebase
from app.rag.retriever import RetrievedChunk

if TYPE_CHECKING:
    from crewai import Agent


@dataclass(slots=True)
class TestGenerationAgent:
    """Draft focused tests from retrieved code context."""

    name: str = "test_generation"

    async def run(self, chunks: list[RetrievedChunk]) -> list[str]:
        return [
            f"Add regression coverage around {chunk.file_path}:{chunk.start_line}."
            for chunk in chunks
        ]


def create_test_generation_agent(repo_id: str) -> Agent:
    """Create the test generation agent."""
    return make_agent(
        role="Senior QA Engineer",
        goal="Generate comprehensive unit and integration tests with edge cases",
        backstory=(
            "Writes tests that actually catch bugs. Understands pytest, Jest, and JUnit "
            "idioms deeply."
        ),
        tools=[search_codebase, read_file],
        llm=llm_powerful,
    )


__all__ = ["TestGenerationAgent", "create_test_generation_agent"]
