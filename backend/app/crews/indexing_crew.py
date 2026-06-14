"""Direct repository indexing pipeline."""

from __future__ import annotations

import asyncio
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from app.config import Settings, get_settings
from app.crews.cache import CrewCache
from app.rag.embedder import CodeEmbedder
from app.rag.indexer import IndexResult, RepoIndexer


class IndexingCrew:
    """Sequential indexing pipeline that does not invoke CrewAI agents."""

    def __init__(
        self,
        settings: Settings | None = None,
        repo_indexer: RepoIndexer | None = None,
        embedder: CodeEmbedder | None = None,
        cache: CrewCache | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.repo_indexer = repo_indexer or RepoIndexer(settings=self.settings)
        self.embedder = embedder
        self.cache = cache

    async def run(self, repo_id: str, github_url: str) -> IndexResult:
        """Clone, chunk, embed, store metadata, and return the index summary."""
        repo_path = await asyncio.to_thread(self.repo_indexer.clone_repo, github_url, repo_id)
        result, chunks = await asyncio.to_thread(
            self.repo_indexer.index_local_repo,
            repo_id,
            repo_path,
        )

        embedder = self.embedder or CodeEmbedder(settings=self.settings)
        try:
            await embedder.index_chunks(
                repo_id=repo_id,
                chunks=chunks,
                commit_sha=result.commit_sha,
            )
        finally:
            if self.embedder is None:
                await embedder.close()

        cache = self.cache or CrewCache(settings=self.settings)
        try:
            await cache.set_json(
                key=f"repo:{repo_id}:meta",
                value={
                    "url": github_url,
                    "commit_sha": result.commit_sha,
                    "indexed_at": datetime.now(UTC).isoformat(),
                    "file_count": result.total_files,
                    "chunk_count": result.total_chunks,
                },
            )
            await cache.set_json(
                key=f"repo:{repo_id}:files",
                value={"files": _file_summaries(chunks)},
            )
        finally:
            if self.cache is None:
                await cache.close()

        return result


def build_indexing_crew(repository_url: str) -> Any:
    """Compatibility helper that returns the direct indexing crew."""
    return IndexingCrew()


def _file_summaries(chunks: list[Any]) -> list[dict[str, Any]]:
    chunk_counts = Counter(str(chunk.file_path) for chunk in chunks)
    languages: dict[str, str] = {}
    for chunk in chunks:
        languages.setdefault(str(chunk.file_path), str(chunk.language))
    return [
        {
            "file_path": file_path,
            "language": languages.get(file_path, "text"),
            "chunk_count": count,
        }
        for file_path, count in sorted(chunk_counts.items())
    ]


__all__ = ["IndexingCrew", "build_indexing_crew"]
