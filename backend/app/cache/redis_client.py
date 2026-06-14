"""Redis connection and JSON helper methods."""

import json
from typing import Any

from redis.asyncio import Redis


class RedisCache:
    """Small async Redis cache wrapper."""

    def __init__(self, client: Redis) -> None:
        self.client = client

    @classmethod
    def from_url(cls, redis_url: str) -> "RedisCache":
        return cls(Redis.from_url(redis_url, decode_responses=True))

    async def get_json(self, key: str) -> dict[str, Any] | None:
        value = await self.client.get(key)
        if value is None:
            return None
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            return None
        return parsed

    async def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int = 3600) -> None:
        await self.client.set(key, json.dumps(value), ex=ttl_seconds)

    async def set_json_persistent(self, key: str, value: dict[str, Any]) -> None:
        await self.client.set(key, json.dumps(value))

    async def get_string(self, key: str) -> str | None:
        value = await self.client.get(key)
        return str(value) if value is not None else None

    async def set_string(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        if ttl_seconds is None:
            await self.client.set(key, value)
        else:
            await self.client.set(key, value, ex=ttl_seconds)

    async def delete(self, *keys: str) -> int:
        if not keys:
            return 0
        return int(await self.client.delete(*keys))

    async def delete_pattern(self, pattern: str) -> int:
        deleted = 0
        async for key in self.client.scan_iter(match=pattern):
            deleted += int(await self.client.delete(key))
        return deleted

    async def list_push_json(self, key: str, value: dict[str, Any], max_length: int) -> None:
        await self.client.lpush(key, json.dumps(value))
        await self.client.ltrim(key, 0, max_length - 1)

    async def list_range_json(self, key: str, start: int = 0, end: int = -1) -> list[dict[str, Any]]:
        values = await self.client.lrange(key, start, end)
        parsed_values: list[dict[str, Any]] = []
        for value in values:
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                parsed_values.append(parsed)
        return parsed_values

    async def close(self) -> None:
        await self.client.aclose()


__all__ = ["RedisCache"]
