"""FastAPI dependency helpers."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.cache.redis_client import RedisCache
from app.config import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_redis_cache(settings: SettingsDep) -> AsyncIterator[RedisCache]:
    """Provide a Redis cache client for request-scoped dependencies."""
    cache = RedisCache.from_url(settings.redis_url)
    try:
        yield cache
    finally:
        await cache.close()


RedisCacheDep = Annotated[RedisCache, Depends(get_redis_cache)]

__all__ = ["RedisCacheDep", "SettingsDep", "get_redis_cache"]
