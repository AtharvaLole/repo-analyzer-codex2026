"""CrewAI tool registry for repository analysis agents."""

from __future__ import annotations

import asyncio
import json
import subprocess
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, TypeVar

from langchain_core.tools import tool

from app.config import Settings, get_settings
from app.rag.chunker import CodeChunker
from app.rag.indexer import RepoIndexer
from app.rag.retriever import HybridRetriever, SearchResult

T = TypeVar("T")

MAX_FILE_CHARS = 8_000
MAX_FINDINGS = 30
SCANNER_TIMEOUT_SECONDS = 180
TREE_MAX_DEPTH = 3
EXCLUDED_TREE_DIRS = {".git", "__pycache__", ".venv", "build", "dist", "node_modules"}


@tool
def search_codebase(query: str, repo_id: str) -> str:
    """Search indexed code for a repository and return cited code snippets."""
    settings = get_settings()
    retriever = HybridRetriever(settings=settings)
    try:
        results = _run_async(retriever.hybrid_search(repo_id=repo_id, query=query, top_k=8))
    except Exception as exc:
        return f"Codebase search failed: {exc}"

    if not results:
        return "No indexed code results found."
    return "\n\n---\n\n".join(_format_search_result(result) for result in results)


@tool
def read_file(file_path: str, repo_id: str) -> str:
    """Read a repository file and return line-numbered content."""
    try:
        target_path = _resolve_repo_file(repo_id=repo_id, file_path=file_path)
    except ValueError as exc:
        return str(exc)

    if not target_path.exists() or not target_path.is_file():
        return f"File not found: {file_path}"

    content = target_path.read_text(encoding="utf-8", errors="replace")
    numbered = "\n".join(
        f"{line_number:>5} | {line}"
        for line_number, line in enumerate(content.splitlines(), start=1)
    )
    return _truncate(numbered, MAX_FILE_CHARS)


@tool
def run_semgrep(repo_id: str) -> str:
    """Run Semgrep with auto configuration and return formatted findings."""
    try:
        repo_path = _resolve_repo_path(repo_id)
    except ValueError as exc:
        return str(exc)
    return _run_json_scanner(
        command=["semgrep", "--config=auto", "--json", str(repo_path)],
        scanner_name="semgrep",
        formatter=_format_semgrep_findings,
    )


@tool
def run_bandit(repo_id: str) -> str:
    """Run Bandit against a repository and return formatted findings."""
    try:
        repo_path = _resolve_repo_path(repo_id)
    except ValueError as exc:
        return str(exc)
    return _run_json_scanner(
        command=["bandit", "-r", str(repo_path), "-f", "json"],
        scanner_name="bandit",
        formatter=_format_bandit_findings,
    )


@tool
def list_repo_files(repo_id: str) -> str:
    """List indexed repository files with detected language and file size."""
    settings = get_settings()
    try:
        repo_path = _resolve_repo_path(repo_id, settings=settings)
        files = RepoIndexer(settings=settings).list_files(repo_path)
    except Exception as exc:
        return f"Could not list repository files: {exc}"

    if not files:
        return "No indexable files found."

    chunker = CodeChunker()
    lines: list[str] = []
    for file_path in files:
        relative_path = file_path.relative_to(repo_path).as_posix()
        language = chunker.detect_language(file_path)
        size = _format_size(file_path.stat().st_size)
        lines.append(f"{relative_path}\t{language}\t{size}")
    return "\n".join(lines)


@tool
def get_repo_structure(repo_id: str) -> str:
    """Return an ASCII directory tree up to three levels deep."""
    try:
        repo_path = _resolve_repo_path(repo_id)
    except ValueError as exc:
        return str(exc)

    if not repo_path.exists():
        return f"Repository not found: {repo_id}"

    lines = [f"{repo_id}/"]
    lines.extend(_tree_lines(repo_path, prefix="", depth=0, max_depth=TREE_MAX_DEPTH))
    return "\n".join(lines)


def _run_async(coroutine: Coroutine[Any, Any, T]) -> T:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(coroutine)).result()


def _format_search_result(result: SearchResult) -> str:
    return (
        f"FILE: {result.file_path} (lines {result.start_line}-{result.end_line})\n"
        f"{result.content}"
    )


def _resolve_repo_path(repo_id: str, settings: Settings | None = None) -> Path:
    active_settings = settings or get_settings()
    base_path = active_settings.repos_base_dir.resolve()
    repo_path = (base_path / repo_id).resolve()
    if repo_path != base_path and base_path not in repo_path.parents:
        raise ValueError("Invalid repository identifier.")
    return repo_path


def _resolve_repo_file(repo_id: str, file_path: str) -> Path:
    repo_path = _resolve_repo_path(repo_id)
    target_path = (repo_path / file_path).resolve()
    if target_path != repo_path and repo_path not in target_path.parents:
        raise ValueError("Invalid file path.")
    return target_path


def _run_json_scanner(
    command: list[str],
    scanner_name: str,
    formatter: Any,
) -> str:
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            check=False,
            encoding="utf-8",
            timeout=SCANNER_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return f"{scanner_name} is not installed."
    except subprocess.TimeoutExpired:
        return f"{scanner_name} timed out after {SCANNER_TIMEOUT_SECONDS} seconds."

    stdout = process.stdout.strip()
    stderr = process.stderr.strip()
    if process.returncode not in {0, 1} and not stdout:
        return f"{scanner_name} failed with exit code {process.returncode}:\n{stderr}"

    try:
        payload = json.loads(stdout or "{}")
    except json.JSONDecodeError:
        combined = "\n".join(part for part in (stdout, stderr) if part)
        return _truncate(combined or f"{scanner_name} produced no parseable output.", MAX_FILE_CHARS)

    return formatter(payload)


def _format_semgrep_findings(payload: dict[str, Any]) -> str:
    results = payload.get("results", [])
    if not isinstance(results, list) or not results:
        return "Semgrep found no issues."

    lines: list[str] = []
    for finding in results[:MAX_FINDINGS]:
        if not isinstance(finding, dict):
            continue
        extra = finding.get("extra", {})
        start = finding.get("start", {})
        severity = extra.get("severity", "UNKNOWN") if isinstance(extra, dict) else "UNKNOWN"
        message = extra.get("message", "") if isinstance(extra, dict) else ""
        line_number = start.get("line", "?") if isinstance(start, dict) else "?"
        lines.append(
            f"[{severity}] {finding.get('check_id', 'semgrep')} "
            f"{finding.get('path', '<unknown>')}:{line_number}\n{message}",
        )
    return "\n\n".join(lines) if lines else "Semgrep found no issues."


def _format_bandit_findings(payload: dict[str, Any]) -> str:
    results = payload.get("results", [])
    if not isinstance(results, list) or not results:
        return "Bandit found no issues."

    lines: list[str] = []
    for finding in results[:MAX_FINDINGS]:
        if not isinstance(finding, dict):
            continue
        lines.append(
            f"[{finding.get('issue_severity', 'UNKNOWN')}] {finding.get('test_id', 'bandit')} "
            f"{finding.get('filename', '<unknown>')}:{finding.get('line_number', '?')}\n"
            f"{finding.get('issue_text', '')}",
        )
    return "\n\n".join(lines) if lines else "Bandit found no issues."


def _tree_lines(path: Path, prefix: str, depth: int, max_depth: int) -> list[str]:
    if depth >= max_depth:
        return []

    entries = _visible_entries(path)
    lines: list[str] = []
    for index, entry in enumerate(entries):
        is_last = index == len(entries) - 1
        connector = "`-- " if is_last else "|-- "
        suffix = "/" if entry.is_dir() else ""
        lines.append(f"{prefix}{connector}{entry.name}{suffix}")
        if entry.is_dir():
            extension = "    " if is_last else "|   "
            lines.extend(_tree_lines(entry, prefix + extension, depth + 1, max_depth))
    return lines


def _visible_entries(path: Path) -> list[Path]:
    entries: list[Path] = []
    for entry in path.iterdir():
        if entry.name in EXCLUDED_TREE_DIRS:
            continue
        if entry.name.startswith(".") and entry.name not in {".env.example"}:
            continue
        entries.append(entry)
    return sorted(entries, key=lambda item: (not item.is_dir(), item.name.lower()))


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _truncate(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}\n... truncated ..."


AGENT_TOOLS = [
    search_codebase,
    read_file,
    run_semgrep,
    run_bandit,
    list_repo_files,
    get_repo_structure,
]
TOOL_REGISTRY = {tool_item.name: tool_item for tool_item in AGENT_TOOLS}

__all__ = [
    "AGENT_TOOLS",
    "TOOL_REGISTRY",
    "get_repo_structure",
    "list_repo_files",
    "read_file",
    "run_bandit",
    "run_semgrep",
    "search_codebase",
]
