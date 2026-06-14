"""Security scanning agent."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from app.agents import llm_powerful, make_agent
from app.agents.tools import read_file, run_bandit, run_semgrep, search_codebase

if TYPE_CHECKING:
    from crewai import Agent


@dataclass(slots=True)
class SecurityFinding:
    """Normalized security finding."""

    scanner: str
    severity: str
    message: str
    file_path: str | None = None


@dataclass(slots=True)
class SecurityAgent:
    """Run Semgrep and Bandit against checked-out repositories."""

    name: str = "security"

    async def run(self, repo_path: Path) -> list[SecurityFinding]:
        findings: list[SecurityFinding] = []
        findings.extend(await self._run_scanner("bandit", ["bandit", "-r", str(repo_path), "-f", "json"]))
        findings.extend(await self._run_scanner("semgrep", ["semgrep", "--config=auto", "--json", str(repo_path)]))
        return findings

    async def _run_scanner(self, scanner: str, command: list[str]) -> list[SecurityFinding]:
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await process.communicate()
        except FileNotFoundError:
            return [SecurityFinding(scanner=scanner, severity="info", message=f"{scanner} is not installed.")]

        if process.returncode in (0, 1):
            return []
        return [
            SecurityFinding(
                scanner=scanner,
                severity="warning",
                message=stderr.decode("utf-8", errors="replace").strip() or "Scanner failed.",
            ),
        ]


def create_security_agent(repo_id: str) -> Agent:
    """Create the application security review agent."""
    return make_agent(
        role="Application Security Engineer",
        goal=(
            "Identify security vulnerabilities, check OWASP Top 10, detect hardcoded secrets, "
            "SQL injection, XSS, insecure auth"
        ),
        backstory=(
            "Former penetration tester. Runs static analysis tools and reviews code logic "
            "for security flaws."
        ),
        tools=[run_semgrep, run_bandit, read_file, search_codebase],
        llm=llm_powerful,
    )


__all__ = ["SecurityAgent", "SecurityFinding", "create_security_agent"]
