"""Code analysis agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.agents import llm_powerful, make_agent
from app.agents.tools import get_repo_structure, read_file, search_codebase
from app.rag.retriever import RetrievedChunk

if TYPE_CHECKING:
    from crewai import Agent


@dataclass(slots=True)
class CodeAnalysisAgent:
    """Summarize code responsibilities and implementation details."""

    name: str = "code_analysis"

    async def run(self, chunks: list[RetrievedChunk]) -> list[str]:
        return [
            f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line} appears relevant."
            for chunk in chunks
        ]


def create_code_analysis_agent(repo_id: str) -> Agent:
    """Create the deep code analysis agent."""
    return make_agent(
        role="Senior Software Engineer",
        goal="Deeply understand code logic, architecture patterns, and implementation details",
        backstory=(
            "10+ years reading production code. Explains complex systems simply. "
            "Always references the actual code, never makes assumptions."
        ),
        tools=[search_codebase, read_file, get_repo_structure],
        llm=llm_powerful,
    )


__all__ = ["CodeAnalysisAgent", "create_code_analysis_agent"]
