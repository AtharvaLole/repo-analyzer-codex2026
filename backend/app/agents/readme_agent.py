"""README generation agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.agents import llm_powerful, make_agent
from app.agents.tools import get_repo_structure, list_repo_files, read_file, search_codebase
from app.config import Settings
from app.models.request import ReadmeRequest

if TYPE_CHECKING:
    from crewai import Agent


@dataclass(slots=True)
class ReadmeAgent:
    """Generate a practical README draft."""

    name: str = "readme"

    async def run(self, request: ReadmeRequest, settings: Settings) -> str:
        sections = [
            f"# Repository {request.repo_id}",
            "",
            "## Overview",
            f"This README draft is tailored for the {request.audience}.",
        ]
        if request.include_setup:
            sections.extend(["", "## Setup", "Document local environment variables, install steps, and run commands."])
        if request.include_architecture:
            sections.extend(
                ["", "## Architecture", "Summarize services, workflows, data stores, and agent responsibilities."],
            )
        return "\n".join(sections)


def create_readme_agent(repo_id: str) -> Agent:
    """Create the technical documentation agent."""
    return make_agent(
        role="Technical Documentation Writer",
        goal=(
            "Generate a production-quality README with architecture overview, setup guide, "
            "API reference, and usage examples"
        ),
        backstory=(
            "Has written docs for open-source projects with 10k+ GitHub stars. "
            "Makes complex projects approachable."
        ),
        tools=[search_codebase, read_file, get_repo_structure, list_repo_files],
        llm=llm_powerful,
    )


__all__ = ["ReadmeAgent", "create_readme_agent"]
