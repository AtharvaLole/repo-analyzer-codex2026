"""CrewAI README generation crew."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.crews.cache import CrewCache

README_CACHE_TTL_SECONDS = 604_800


class ReadmeResult(BaseModel):
    """README generation result."""

    content: str
    confidence: int = Field(ge=0, le=100)
    sections: list[str]


class ReadmeCrew:
    """Sequential CrewAI workflow for repository README generation."""

    def __init__(self, settings: Settings | None = None, cache: CrewCache | None = None) -> None:
        self.settings = settings or get_settings()
        self.cache = cache

    async def run(self, repo_id: str) -> ReadmeResult:
        """Generate or return a cached README for the repository's current commit."""
        cache = self.cache or CrewCache(settings=self.settings)
        try:
            commit_sha = await self._commit_sha(cache=cache, repo_id=repo_id)
            cache_key = f"readme:{repo_id}:{commit_sha}"
            cached = await cache.get_model(cache_key, ReadmeResult)
            if cached is not None:
                return cached

            crew = self._build_crew(repo_id)
            output = await asyncio.to_thread(crew.kickoff)
            content = _crew_output_to_text(output)
            result = ReadmeResult(
                content=content,
                confidence=_extract_confidence(content),
                sections=_extract_markdown_sections(content),
            )
            await cache.set_model(cache_key, result, ttl_seconds=README_CACHE_TTL_SECONDS)
            return result
        finally:
            if self.cache is None:
                await cache.close()

    async def _commit_sha(self, cache: CrewCache, repo_id: str) -> str:
        commit_sha = await cache.get_string(f"repo:{repo_id}:commit_sha")
        if commit_sha:
            return commit_sha

        metadata = await cache.get_json(f"repo:{repo_id}:meta")
        if metadata is not None:
            cached_sha = metadata.get("commit_sha")
            if isinstance(cached_sha, str) and cached_sha:
                return cached_sha
        return "unknown"

    def _build_crew(self, repo_id: str) -> Any:
        from crewai import Crew, Process, Task

        from app.agents import (
            create_code_analysis_agent,
            create_dependency_agent,
            create_readme_agent,
            create_review_agent,
        )

        code_analysis_agent = create_code_analysis_agent(repo_id)
        dependency_agent = create_dependency_agent(repo_id)
        readme_agent = create_readme_agent(repo_id)
        review_agent = create_review_agent(repo_id)

        architecture_task = Task(
            description=(
                f"Analyse the overall architecture, key modules, tech stack, and entry points "
                f"of repo {repo_id}. List every major component with its file path."
            ),
            expected_output="Architecture analysis with cited file paths.",
            agent=code_analysis_agent,
        )
        dependency_task = Task(
            description=(
                "Map the dependency graph and main data flows. Describe the request lifecycle "
                "from entry point to response."
            ),
            expected_output="Dependency graph and request lifecycle analysis.",
            agent=dependency_agent,
            context=[architecture_task],
        )
        readme_task = Task(
            description=(
                "Using the analysis, generate a complete README.md with these sections: "
                "Project Title, Description, Architecture Overview (with mermaid diagram), "
                "Tech Stack, Prerequisites, Installation, Configuration, Usage, API Reference, "
                "Project Structure, Contributing, License"
            ),
            expected_output="Complete README.md markdown content.",
            agent=readme_agent,
            context=[architecture_task, dependency_task],
        )
        review_task = Task(
            description=(
                "Review the README for accuracy against the actual code. Fix any incorrect "
                "claims. Add a confidence score (0-100)."
            ),
            expected_output="Reviewed README markdown with confidence score.",
            agent=review_agent,
            context=[architecture_task, dependency_task, readme_task],
        )

        return Crew(
            agents=[code_analysis_agent, dependency_agent, readme_agent, review_agent],
            tasks=[architecture_task, dependency_task, readme_task, review_task],
            process=Process.sequential,
            verbose=False,
        )


def build_readme_crew(repo_id: str) -> Any:
    """Build the underlying sequential CrewAI README crew."""
    return ReadmeCrew()._build_crew(repo_id)


def _crew_output_to_text(output: Any) -> str:
    for attribute in ("raw", "result", "output"):
        value = getattr(output, attribute, None)
        if isinstance(value, str) and value.strip():
            return value
    return str(output)


def _extract_confidence(content: str) -> int:
    match = re.search(r"confidence(?:\s+score)?\D{0,20}(\d{1,3})", content, flags=re.IGNORECASE)
    if match is None:
        return 75
    return max(0, min(100, int(match.group(1))))


def _extract_markdown_sections(content: str) -> list[str]:
    sections = re.findall(r"^#{1,3}\s+(.+?)\s*$", content, flags=re.MULTILINE)
    return [section.strip() for section in sections]


__all__ = ["README_CACHE_TTL_SECONDS", "ReadmeCrew", "ReadmeResult", "build_readme_crew"]
