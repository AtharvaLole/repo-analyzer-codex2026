"""Dependency analysis agent."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from app.agents import llm_powerful, make_agent
from app.agents.tools import get_repo_structure, read_file, search_codebase

if TYPE_CHECKING:
    from crewai import Agent


@dataclass(slots=True)
class DependencyAgent:
    """Inspect dependency manifests in a repository."""

    name: str = "dependency"

    async def run(self, repo_path: Path) -> dict[str, list[str]]:
        manifests: dict[str, list[str]] = {"python": [], "node": []}
        if (repo_path / "requirements.txt").exists():
            manifests["python"].append("requirements.txt")
        if (repo_path / "pyproject.toml").exists():
            manifests["python"].append("pyproject.toml")
        if (repo_path / "package.json").exists():
            manifests["node"].append("package.json")
        return manifests


def create_dependency_agent(repo_id: str) -> Agent:
    """Create the dependency and data-flow analysis agent."""
    return make_agent(
        role="Systems Architect",
        goal="Map function call chains, module dependencies, and data flow through the codebase",
        backstory=(
            "Specialist in understanding how code flows from entry points through layers "
            "to the database."
        ),
        tools=[search_codebase, read_file, get_repo_structure],
        llm=llm_powerful,
    )


__all__ = ["DependencyAgent", "create_dependency_agent"]
