"""OpenAI embedding and ChromaDB indexing helpers."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from app.config import Settings
from app.rag.chunker import CodeChunk

EMBEDDING_CACHE_TTL_SECONDS = 86_400
EMBEDDING_BATCH_SIZE = 100
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class EmbeddingError(RuntimeError):
    """Raised when embeddings or vector index writes fail."""


class CodeEmbedder:
    """Embed code chunks with OpenAI and persist them in repo-scoped Chroma collections."""

    def __init__(
        self,
        settings: Settings,
        redis_client: Any | None = None,
        chroma_client: Any | None = None,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ) -> None:
        self.settings = settings
        self.redis_client = redis_client
        self.chroma_client = chroma_client
        self.embedding_model = embedding_model
        self._embeddings_client: Any | None = None
        self._owns_redis_client = redis_client is None

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed text inputs, using Redis as a 24-hour cache."""
        if not texts:
            return []

        embeddings: list[list[float] | None] = [None] * len(texts)
        missing: list[tuple[int, str, str]] = []
        for index, text in enumerate(texts):
            cache_key = self._embedding_cache_key(text)
            cached_embedding = await self._get_embedding_from_cache(cache_key)
            if cached_embedding is None:
                missing.append((index, text, cache_key))
            else:
                embeddings[index] = cached_embedding

        for batch in self._batched(missing, EMBEDDING_BATCH_SIZE):
            batch_texts = [item[1] for item in batch]
            batch_embeddings = await self._embed_batch(batch_texts)
            for (index, _text, cache_key), embedding in zip(batch, batch_embeddings, strict=True):
                vector = [float(value) for value in embedding]
                embeddings[index] = vector
                await self._set_embedding_cache(cache_key, vector)

        return [embedding if embedding is not None else [] for embedding in embeddings]

    async def index_chunks(
        self,
        repo_id: str,
        chunks: list[dict[str, Any] | CodeChunk],
        commit_sha: str,
    ) -> None:
        """Embed and upsert chunks into a repo-scoped ChromaDB collection."""
        if not chunks:
            await self._set_string(f"repo:{repo_id}:commit_sha", commit_sha)
            return

        records = [self._chunk_to_record(repo_id=repo_id, chunk=chunk, commit_sha=commit_sha) for chunk in chunks]
        embeddings = await self.embed_texts([record["content"] for record in records])
        await asyncio.to_thread(self._upsert_records, repo_id, records, embeddings)
        await self._set_string(f"repo:{repo_id}:commit_sha", commit_sha)

    async def delete_repo_index(self, repo_id: str) -> None:
        """Delete a repo-scoped ChromaDB collection."""
        await asyncio.to_thread(self._delete_collection, repo_id)

    async def close(self) -> None:
        """Close owned network clients."""
        if self._owns_redis_client and self.redis_client is not None:
            close = getattr(self.redis_client, "aclose", None)
            if close is not None:
                await close()

    def _upsert_records(
        self,
        repo_id: str,
        records: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        collection = self._get_collection(repo_id=repo_id, create=True)
        collection.upsert(
            ids=[str(record["id"]) for record in records],
            documents=[str(record["content"]) for record in records],
            embeddings=embeddings,
            metadatas=[dict(record["metadata"]) for record in records],
        )

    def _delete_collection(self, repo_id: str) -> None:
        client = self._get_chroma_client()
        try:
            client.delete_collection(self._collection_name(repo_id))
        except Exception:
            return

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        if self.settings.openai_api_key is None:
            raise EmbeddingError("OPENAI_API_KEY is required to generate embeddings.")

        embeddings_client = self._get_embeddings_client()
        async_embed = getattr(embeddings_client, "aembed_documents", None)
        if async_embed is not None:
            vectors = await async_embed(texts)
        else:
            vectors = await asyncio.to_thread(embeddings_client.embed_documents, texts)
        return [[float(value) for value in vector] for vector in vectors]

    def _get_embeddings_client(self) -> Any:
        if self._embeddings_client is not None:
            return self._embeddings_client

        from langchain_openai import OpenAIEmbeddings

        if self.settings.openai_api_key is None:
            raise EmbeddingError("OPENAI_API_KEY is required to initialize OpenAI embeddings.")

        self._embeddings_client = OpenAIEmbeddings(
            api_key=self.settings.openai_api_key.get_secret_value(),
            model=self.embedding_model,
        )
        return self._embeddings_client

    def _get_chroma_client(self) -> Any:
        if self.chroma_client is not None:
            return self.chroma_client

        import chromadb

        persist_dir = self._chroma_persist_dir()
        persist_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=str(persist_dir))
        return self.chroma_client

    def _get_collection(self, repo_id: str, create: bool) -> Any:
        client = self._get_chroma_client()
        collection_name = self._collection_name(repo_id)
        if create:
            return client.get_or_create_collection(collection_name)
        return client.get_collection(collection_name)

    def _chunk_to_record(
        self,
        repo_id: str,
        chunk: dict[str, Any] | CodeChunk,
        commit_sha: str,
    ) -> dict[str, Any]:
        data = self._chunk_to_mapping(chunk)
        file_path = str(data["file_path"])
        start_line = int(data["start_line"])
        end_line = int(data["end_line"])
        chunk_type = str(data["chunk_type"])
        language = str(data["language"])
        name = str(data["name"])
        content = str(data["content"])
        return {
            "id": f"{repo_id}:{file_path}:{start_line}",
            "content": content,
            "metadata": {
                "file_path": file_path,
                "start_line": start_line,
                "end_line": end_line,
                "chunk_type": chunk_type,
                "language": language,
                "name": name,
                "commit_sha": commit_sha,
            },
        }

    def _chunk_to_mapping(self, chunk: dict[str, Any] | CodeChunk) -> Mapping[str, Any]:
        if isinstance(chunk, CodeChunk):
            return {
                "content": chunk.content,
                "file_path": chunk.file_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "chunk_type": chunk.chunk_type,
                "language": chunk.language,
                "name": chunk.name,
            }
        return chunk

    async def _get_embedding_from_cache(self, cache_key: str) -> list[float] | None:
        raw_value = await self._get_string(cache_key)
        if raw_value is None:
            return None
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, list):
            return None
        try:
            return [float(value) for value in parsed]
        except (TypeError, ValueError):
            return None

    async def _set_embedding_cache(self, cache_key: str, embedding: list[float]) -> None:
        await self._set_string(cache_key, json.dumps(embedding), ttl_seconds=EMBEDDING_CACHE_TTL_SECONDS)

    async def _get_string(self, key: str) -> str | None:
        client = self._get_redis_client()
        if client is None:
            return None
        try:
            value = await client.get(key)
        except Exception:
            return None
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    async def _set_string(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        client = self._get_redis_client()
        if client is None:
            return
        try:
            if ttl_seconds is None:
                await client.set(key, value)
            else:
                await client.set(key, value, ex=ttl_seconds)
        except Exception:
            return

    def _get_redis_client(self) -> Any | None:
        if self.redis_client is not None:
            return self.redis_client

        try:
            from redis.asyncio import Redis
        except ImportError:
            return None

        self.redis_client = Redis.from_url(self.settings.redis_url, decode_responses=True)
        return self.redis_client

    def _embedding_cache_key(self, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        return f"emb:{digest}"

    def _collection_name(self, repo_id: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", repo_id).strip("_-")
        if not normalized:
            normalized = hashlib.sha256(repo_id.encode("utf-8")).hexdigest()[:16]
        name = f"repo_{normalized}"
        if len(name) <= 63:
            return name
        suffix = hashlib.sha256(repo_id.encode("utf-8")).hexdigest()[:12]
        return f"{name[:50].rstrip('_-')}_{suffix}"

    def _chroma_persist_dir(self) -> Path:
        return getattr(self.settings, "CHROMA_PERSIST_DIR", self.settings.chroma_path)

    def _batched(
        self,
        items: list[tuple[int, str, str]],
        batch_size: int,
    ) -> list[list[tuple[int, str, str]]]:
        return [items[index : index + batch_size] for index in range(0, len(items), batch_size)]


class ChromaEmbedder(CodeEmbedder):
    """Backward-compatible Chroma writer used by earlier scaffold code."""

    async def upsert_chunks(self, chunks: Sequence[CodeChunk]) -> int:
        chunk_list = list(chunks)
        if not chunk_list:
            return 0
        repo_id = chunk_list[0].repo_id
        commit_sha = str(dict(chunk_list[0].metadata).get("commit_sha", "unknown"))
        await self.index_chunks(repo_id=repo_id, chunks=chunk_list, commit_sha=commit_sha)
        return len(chunk_list)


__all__ = [
    "ChromaEmbedder",
    "CodeEmbedder",
    "DEFAULT_EMBEDDING_MODEL",
    "EMBEDDING_BATCH_SIZE",
    "EMBEDDING_CACHE_TTL_SECONDS",
    "EmbeddingError",
]
