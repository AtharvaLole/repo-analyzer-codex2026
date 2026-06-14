"""Small Redis cache helper for crew orchestration."""

from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel

from app.config import Settings

ModelT = TypeVar("ModelT", bound=BaseModel)


class CrewCache:
    """Async Redis string and Pydantic-model cache wrapper."""

    def __init__(self, settings: Settings, redis_client: Any | None = None) -> None:
        self.settings = settings
        self.redis_client = redis_client
        self._owns_redis_client = redis_client is None

    async def get_string(self, key: str) -> str | None:
        client = self._get_client()
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

    async def set_string(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        client = self._get_client()
        if client is None:
            return
        try:
            if ttl_seconds is None:
                await client.set(key, value)
            else:
                await client.set(key, value, ex=ttl_seconds)
        except Exception:
            return

    async def get_json(self, key: str) -> dict[str, Any] | None:
        value = await self.get_string(key)
        if value is None:
            return None
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    async def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int | None = None) -> None:
        await self.set_string(key, json.dumps(value), ttl_seconds=ttl_seconds)

    async def get_model(self, key: str, model_type: type[ModelT]) -> ModelT | None:
        value = await self.get_string(key)
        if value is None:
            return None
        try:
            return model_type.model_validate_json(value)
        except Exception:
            return None

    async def set_model(self, key: str, value: BaseModel, ttl_seconds: int) -> None:
        await self.set_string(key, value.model_dump_json(), ttl_seconds=ttl_seconds)

    async def close(self) -> None:
        if self._owns_redis_client and self.redis_client is not None:
            close = getattr(self.redis_client, "aclose", None)
            if close is not None:
                await close()

    def _get_client(self) -> Any | None:
        if self.redis_client is not None:
            return self.redis_client
        try:
            from redis.asyncio import Redis
        except ImportError:
            return None
        self.redis_client = Redis.from_url(self.settings.redis_url, decode_responses=True)
        return self.redis_client


__all__ = ["CrewCache"]
