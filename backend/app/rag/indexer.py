"""Repository cloning, file discovery, chunking, and indexing."""

from __future__ import annotations

import asyncio
import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field

from app.config import Settings
from app.models.request import RepositoryIndexRequest
from app.models.response import RepositoryIndexResponse
from app.rag.chunker import CodeChunk, CodeChunker
from app.rag.embedder import CodeEmbedder


class IndexingError(RuntimeError):
    """Base exception for repository indexing failures."""


class RepoTooLargeError(IndexingError):
    """Raised when a repository exceeds the configured size limit."""


class CloneFailedError(IndexingError):
    """Raised when GitPython cannot clone or update a repository."""


class IndexResult(BaseModel):
    """Summary returned after repository indexing."""

    repo_id: str = Field(min_length=1)
    commit_sha: str = Field(min_length=1)
    total_files: int = Field(ge=0)
    total_chunks: int = Field(ge=0)
    file_list: list[str] = Field(default_factory=list)


@dataclass(slots=True)
class RepoIndexer:
    """Clone repositories and produce code chunks."""

    settings: Settings
    chunker: CodeChunker = field(default_factory=CodeChunker)

    def clone_repo(self, github_url: str, repo_id: str) -> Path:
        """Clone a repository into REPOS_BASE_DIR/{repo_id}, or pull if it already exists."""
        from git import GitCommandError, InvalidGitRepositoryError, Repo

        repo_path = self._repos_base_dir / repo_id
        self._repos_base_dir.mkdir(parents=True, exist_ok=True)

        try:
            if repo_path.exists():
                repo = Repo(repo_path)
                repo.remotes.origin.pull()
            else:
                Repo.clone_from(github_url, repo_path)
        except (GitCommandError, InvalidGitRepositoryError, OSError) as exc:
            raise CloneFailedError(f"Failed to clone or update repository '{github_url}'.") from exc

        self._validate_repo_size(repo_path)
        return repo_path

    def get_commit_sha(self, repo_path: Path) -> str:
        """Return the current HEAD commit SHA."""
        from git import GitCommandError, InvalidGitRepositoryError, Repo

        try:
            repo = Repo(repo_path)
            return str(repo.head.commit.hexsha)
        except (GitCommandError, InvalidGitRepositoryError, ValueError) as exc:
            raise IndexingError(f"Could not read HEAD commit for '{repo_path}'.") from exc

    def list_files(self, repo_path: Path) -> list[Path]:
        """Return indexable files, excluding generated, binary, dependency, and VCS artifacts."""
        if not repo_path.exists():
            raise IndexingError(f"Repository path does not exist: {repo_path}")

        excluded_dirs = {".git", "node_modules", "__pycache__", ".venv", "dist", "build"}
        excluded_patterns = {
            "*.jpg",
            "*.jpeg",
            "*.lock",
            "*.min.js",
            "*.pdf",
            "*.png",
        }
        files: list[Path] = []
        for current_root, dir_names, file_names in os.walk(repo_path):
            dir_names[:] = [dirname for dirname in dir_names if dirname not in excluded_dirs]
            for file_name in file_names:
                if any(fnmatch.fnmatch(file_name, pattern) for pattern in excluded_patterns):
                    continue
                files.append(Path(current_root) / file_name)
        return sorted(files)

    def index_repo(self, repo_id: str, github_url: str) -> IndexResult:
        """Clone or pull a repository, chunk all indexable files, and return an indexing summary."""
        result, _chunks = self.index_repo_with_chunks(repo_id=repo_id, github_url=github_url)
        return result

    def index_repo_with_chunks(self, repo_id: str, github_url: str) -> tuple[IndexResult, list[CodeChunk]]:
        """Return an indexing summary plus the produced chunks for persistence layers."""
        try:
            repo_path = self.clone_repo(github_url=github_url, repo_id=repo_id)
            return self.index_local_repo(repo_id=repo_id, repo_path=repo_path)
        except (CloneFailedError, RepoTooLargeError):
            raise
        except IndexingError:
            raise
        except Exception as exc:
            raise IndexingError(f"Failed to index repository '{repo_id}'.") from exc

    def index_local_repo(self, repo_id: str, repo_path: Path) -> tuple[IndexResult, list[CodeChunk]]:
        """Chunk an already-cloned repository and return an index summary plus chunks."""
        try:
            commit_sha = self.get_commit_sha(repo_path)
            files = self.list_files(repo_path)
            chunks = self._chunk_files(repo_id=repo_id, repo_path=repo_path, files=files)
            result = IndexResult(
                repo_id=repo_id,
                commit_sha=commit_sha,
                total_files=len(files),
                total_chunks=len(chunks),
                file_list=[file_path.relative_to(repo_path).as_posix() for file_path in files],
            )
            return result, chunks
        except IndexingError:
            raise
        except Exception as exc:
            raise IndexingError(f"Failed to index local repository '{repo_path}'.") from exc

    def _chunk_files(self, repo_id: str, repo_path: Path, files: list[Path]) -> list[CodeChunk]:
        chunks: list[CodeChunk] = []
        for file_path in files:
            try:
                chunks.extend(self.chunker.chunk_file(repo_id=repo_id, root=repo_path, file_path=file_path))
            except OSError as exc:
                raise IndexingError(f"Could not read source file '{file_path}'.") from exc
        return chunks

    def _validate_repo_size(self, repo_path: Path) -> None:
        size_mb = self._repo_size_mb(repo_path)
        if size_mb > self._max_repo_size_mb:
            raise RepoTooLargeError(
                f"Repository '{repo_path}' is {size_mb:.2f} MB, "
                f"which exceeds the {self._max_repo_size_mb:.2f} MB limit.",
            )

    def _repo_size_mb(self, repo_path: Path) -> float:
        total_bytes = 0
        for file_path in repo_path.rglob("*"):
            if file_path.is_file():
                try:
                    total_bytes += file_path.stat().st_size
                except OSError as exc:
                    raise IndexingError(f"Could not stat file '{file_path}'.") from exc
        return total_bytes / (1024 * 1024)

    @property
    def _repos_base_dir(self) -> Path:
        return getattr(self.settings, "repos_base_dir", self.settings.repo_storage_path)

    @property
    def _max_repo_size_mb(self) -> float:
        return float(getattr(self.settings, "max_repo_size_mb", 250))


@dataclass(slots=True)
class RepositoryIndexer:
    """Backward-compatible async indexer that persists chunks to ChromaDB."""

    settings: Settings
    chunker: CodeChunker = field(default_factory=CodeChunker)

    async def index(self, repo_id: str, request: RepositoryIndexRequest) -> RepositoryIndexResponse:
        repo_indexer = RepoIndexer(settings=self.settings, chunker=self.chunker)
        result, chunks = await asyncio.to_thread(
            repo_indexer.index_repo_with_chunks,
            repo_id,
            str(request.repository_url),
        )
        embedder = CodeEmbedder(self.settings)
        try:
            await embedder.index_chunks(
                repo_id=result.repo_id,
                chunks=chunks,
                commit_sha=result.commit_sha,
            )
        finally:
            await embedder.close()
        return RepositoryIndexResponse(
            repo_id=result.repo_id,
            status="indexed",
            task_id=None,
            message=(
                f"Indexed {result.total_chunks} chunks from {result.total_files} files "
                f"at commit {result.commit_sha}."
            ),
        )


__all__ = [
    "CloneFailedError",
    "IndexResult",
    "IndexingError",
    "RepoIndexer",
    "RepoTooLargeError",
    "RepositoryIndexer",
]
