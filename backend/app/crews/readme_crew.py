"""CrewAI README generation crew."""

from __future__ import annotations

import asyncio
import json
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

            if self.settings.openai_api_key is None and self.settings.anthropic_api_key is None:
                result = await self._local_readme(cache=cache, repo_id=repo_id)
                await cache.set_model(cache_key, result, ttl_seconds=README_CACHE_TTL_SECONDS)
                return result

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

    async def _local_readme(self, cache: CrewCache, repo_id: str) -> ReadmeResult:
        metadata = await cache.get_json(f"repo:{repo_id}:meta") or {}
        raw_files = await cache.get_string(f"repo:{repo_id}:files")
        files: list[dict[str, Any]] = []
        if raw_files:
            try:
                parsed = json.loads(raw_files)
                if isinstance(parsed, dict) and isinstance(parsed.get("files"), list):
                    files = [item for item in parsed["files"] if isinstance(item, dict)]
            except json.JSONDecodeError:
                files = []

        project_name = str(metadata.get("url") or repo_id).rstrip("/").split("/")[-1] or repo_id
        top_files = files[:30]
        language_counts: dict[str, int] = {}
        for item in files:
            language = str(item.get("language") or "text")
            language_counts[language] = language_counts.get(language, 0) + 1

        tech_stack = ", ".join(
            f"{language} ({count})" for language, count in sorted(language_counts.items())
        ) or "Detected from indexed files"
        file_lines = "\n".join(
            f"- `{item.get('file_path', '')}` - {item.get('language', 'text')}, "
            f"{item.get('chunk_count', 0)} chunks"
            for item in top_files
        ) or "- No indexed files found."

        content = f"""# {project_name}

## Description
This README was generated in local demo mode from the repository index.

## Architecture Overview
```mermaid
flowchart TD
    Repo[Git repository] --> Indexer[Repo indexer]
    Indexer --> Chunks[Code chunks]
    Chunks --> Search[Hybrid search]
    Search --> UI[Analysis UI]
```

## Tech Stack
{tech_stack}

## Prerequisites
- Python 3.11
- Node.js
- Redis running on `localhost:6379`

## Installation
Install backend and frontend dependencies, then run the local API and frontend dev server.

## Configuration
Set `OPENAI_API_KEY` only if you want cloud LLM answers. Local demo indexing and search work without it.

## Usage
1. Paste a GitHub repository URL.
2. Wait for indexing to finish.
3. Ask questions in Chat or generate this README.

## API Reference
The local backend exposes repository indexing, chat, README, and task-status endpoints under `/api/v1`.

## Project Structure
{file_lines}

## Contributing
Use focused pull requests and include tests for behavior changes.

## License
Check the source repository for its license.

Confidence score: 70
"""
        return ReadmeResult(
            content=content,
            confidence=70,
            sections=_extract_markdown_sections(content),
        )

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
