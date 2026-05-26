import json
from typing import Any, Optional

import redis.asyncio as aioredis

from src.core.config import settings

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def cache_get(key: str) -> Optional[Any]:
    try:
        redis = await get_redis()
        value = await redis.get(key)
        if value is not None:
            return json.loads(value)
    except Exception:
        pass
    return None


async def cache_set(key: str, value: Any, ttl: int = settings.CACHE_TTL_SECONDS) -> None:
    try:
        redis = await get_redis()
        await redis.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


async def cache_delete(key: str) -> None:
    try:
        redis = await get_redis()
        await redis.delete(key)
    except Exception:
        pass


async def cache_delete_pattern(pattern: str) -> None:
    try:
        redis = await get_redis()
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
    except Exception:
        pass
