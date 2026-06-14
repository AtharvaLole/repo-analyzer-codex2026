"""Semantic, BM25, and hybrid retrieval over repo-scoped Chroma collections."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.config import Settings
from app.rag.embedder import CodeEmbedder

HYBRID_CACHE_TTL_SECONDS = 3_600
RRF_K = 60


class SearchResult(BaseModel):
    """Single retrieval result."""

    chunk_id: str
    content: str
    file_path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    chunk_type: str
    language: str
    name: str
    score: float
    search_type: Literal["semantic", "bm25", "hybrid"]


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """Backward-compatible ranked retrieval result."""

    id: str
    repo_id: str
    file_path: str
    start_line: int
    end_line: int
    content: str
    score: float
    chunk_type: str = "module"
    language: str = "text"
    name: str = ""


class HybridRetriever:
    """Retrieve code context with semantic search, BM25, and Reciprocal Rank Fusion."""

    def __init__(
        self,
        settings: Settings,
        embedder: CodeEmbedder | None = None,
        redis_client: Any | None = None,
        chroma_client: Any | None = None,
    ) -> None:
        self.settings = settings
        self.embedder = embedder or CodeEmbedder(
            settings=settings,
            redis_client=redis_client,
            chroma_client=chroma_client,
        )
        self.redis_client = redis_client
        self.chroma_client = chroma_client

    async def semantic_search(self, repo_id: str, query: str, top_k: int = 10) -> list[SearchResult]:
        """Run vector search against a repo-scoped ChromaDB collection."""
        embeddings = await self.embedder.embed_texts([query])
        if not embeddings:
            return []
        return await asyncio.to_thread(
            self._semantic_search_sync,
            repo_id,
            embeddings[0],
            top_k,
        )

    async def bm25_search(self, repo_id: str, query: str, top_k: int = 10) -> list[SearchResult]:
        """Run BM25 keyword search over all documents in a repo-scoped ChromaDB collection."""
        return await asyncio.to_thread(self._bm25_search_sync, repo_id, query, top_k)

    async def hybrid_search(self, repo_id: str, query: str, top_k: int = 8) -> list[SearchResult]:
        """Merge semantic and BM25 search with Reciprocal Rank Fusion."""
        cache_key = self._hybrid_cache_key(repo_id, query)
        cached_results = await self._get_cached_results(cache_key)
        if cached_results is not None:
            return cached_results[:top_k]

        semantic_results, bm25_results = await asyncio.gather(
            self.semantic_search(repo_id=repo_id, query=query, top_k=top_k),
            self.bm25_search(repo_id=repo_id, query=query, top_k=top_k),
        )
        merged_results = self._reciprocal_rank_fusion(semantic_results, bm25_results, top_k=top_k)
        await self._set_cached_results(cache_key, merged_results)
        return merged_results

    async def search(self, repo_id: str, query: str, top_k: int = 6) -> list[RetrievedChunk]:
        """Backward-compatible adapter used by the agent orchestrator."""
        results = await self.hybrid_search(repo_id=repo_id, query=query, top_k=top_k)
        return [
            RetrievedChunk(
                id=result.chunk_id,
                repo_id=repo_id,
                file_path=result.file_path,
                start_line=result.start_line,
                end_line=result.end_line,
                content=result.content,
                score=result.score,
                chunk_type=result.chunk_type,
                language=result.language,
                name=result.name,
            )
            for result in results
        ]

    def _semantic_search_sync(
        self,
        repo_id: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[SearchResult]:
        collection = self._get_collection(repo_id)
        if collection is None:
            return []

        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        search_results: list[SearchResult] = []
        for chunk_id, document, metadata, distance in zip(
            ids,
            documents,
            metadatas,
            distances,
            strict=False,
        ):
            search_results.append(
                self._build_search_result(
                    chunk_id=str(chunk_id),
                    content=str(document),
                    metadata=metadata or {},
                    score=1.0 / (1.0 + float(distance)),
                    search_type="semantic",
                ),
            )
        return search_results

    def _bm25_search_sync(self, repo_id: str, query: str, top_k: int) -> list[SearchResult]:
        from rank_bm25 import BM25Okapi

        records = self._load_records(repo_id)
        if not records:
            return []

        corpus = [self._tokenize(record["content"]) for record in records]
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        bm25 = BM25Okapi(corpus)
        scores = [float(score) for score in bm25.get_scores(query_tokens)]
        ranked = sorted(
            zip(records, scores, strict=False),
            key=lambda item: item[1],
            reverse=True,
        )[:top_k]
        max_score = max((score for _record, score in ranked), default=0.0)
        if max_score <= 0:
            max_score = 1.0

        return [
            self._build_search_result(
                chunk_id=str(record["id"]),
                content=str(record["content"]),
                metadata=record["metadata"],
                score=score / max_score,
                search_type="bm25",
            )
            for record, score in ranked
            if score > 0
        ]

    def _reciprocal_rank_fusion(
        self,
        semantic_results: list[SearchResult],
        bm25_results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        by_chunk_id: dict[str, SearchResult] = {}
        scores: dict[str, float] = {}
        for result_set in (semantic_results, bm25_results):
            for rank, result in enumerate(result_set, start=1):
                by_chunk_id.setdefault(result.chunk_id, result)
                scores[result.chunk_id] = scores.get(result.chunk_id, 0.0) + (1.0 / (RRF_K + rank))

        ranked_ids = sorted(scores, key=scores.get, reverse=True)
        return [
            by_chunk_id[chunk_id].model_copy(
                update={"score": scores[chunk_id], "search_type": "hybrid"},
            )
            for chunk_id in ranked_ids[:top_k]
        ]

    def _load_records(self, repo_id: str) -> list[dict[str, Any]]:
        collection = self._get_collection(repo_id)
        if collection is None:
            return []

        result = collection.get(include=["documents", "metadatas"])
        ids = result.get("ids", [])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        return [
            {
                "id": chunk_id,
                "content": document,
                "metadata": metadata or {},
            }
            for chunk_id, document, metadata in zip(ids, documents, metadatas, strict=False)
        ]

    def _build_search_result(
        self,
        chunk_id: str,
        content: str,
        metadata: dict[str, Any],
        score: float,
        search_type: Literal["semantic", "bm25", "hybrid"],
    ) -> SearchResult:
        return SearchResult(
            chunk_id=chunk_id,
            content=content,
            file_path=str(metadata.get("file_path", "")),
            start_line=int(metadata.get("start_line", 1)),
            end_line=int(metadata.get("end_line", metadata.get("start_line", 1))),
            chunk_type=str(metadata.get("chunk_type", "module")),
            language=str(metadata.get("language", "text")),
            name=str(metadata.get("name", "")),
            score=score,
            search_type=search_type,
        )

    async def _get_cached_results(self, cache_key: str) -> list[SearchResult] | None:
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
            return [SearchResult.model_validate(item) for item in parsed]
        except Exception:
            return None

    async def _set_cached_results(self, cache_key: str, results: list[SearchResult]) -> None:
        payload = json.dumps([result.model_dump() for result in results])
        await self._set_string(cache_key, payload, ttl_seconds=HYBRID_CACHE_TTL_SECONDS)

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

    async def _set_string(self, key: str, value: str, ttl_seconds: int) -> None:
        client = self._get_redis_client()
        if client is None:
            return
        try:
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

    def _get_collection(self, repo_id: str) -> Any | None:
        try:
            return self.embedder._get_collection(repo_id=repo_id, create=False)
        except Exception:
            return None

    def _hybrid_cache_key(self, repo_id: str, query: str) -> str:
        digest = hashlib.sha256(query.encode("utf-8")).hexdigest()[:12]
        return f"hybrid:{repo_id}:{digest}"

    def _tokenize(self, text: str) -> list[str]:
        return [token.lower() for token in re.findall(r"[A-Za-z0-9_]+", text)]


__all__ = [
    "HYBRID_CACHE_TTL_SECONDS",
    "HybridRetriever",
    "RRF_K",
    "RetrievedChunk",
    "SearchResult",
]
