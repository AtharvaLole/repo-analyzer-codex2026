"""Refactoring recommendation agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.agents import llm_powerful, make_agent
from app.agents.tools import read_file, search_codebase
from app.rag.retriever import RetrievedChunk

if TYPE_CHECKING:
    from crewai import Agent


@dataclass(slots=True)
class RefactorAgent:
    """Produce focused refactoring recommendations from code context."""

    name: str = "refactor"

    async def run(self, chunks: list[RetrievedChunk]) -> list[str]:
        return [
            f"Inspect {chunk.file_path}:{chunk.start_line}-{chunk.end_line} for duplication and design smells."
            for chunk in chunks
        ]


def create_refactor_agent(repo_id: str) -> Agent:
    """Create the code quality and refactoring agent."""
    return make_agent(
        role="Code Quality Engineer",
        goal="Identify code smells, duplicate logic, and suggest concrete refactoring improvements",
        backstory=(
            "Deep knowledge of SOLID principles, design patterns, and clean code. "
            "Always shows before/after."
        ),
        tools=[search_codebase, read_file],
        llm=llm_powerful,
    )


__all__ = ["RefactorAgent", "create_refactor_agent"]
