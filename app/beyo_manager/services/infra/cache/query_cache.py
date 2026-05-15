import json

from beyo_manager.services.infra.redis.async_client import get_async_redis

_DEFAULT_TTL = 300


async def get_cached(cache_key: str) -> dict | None:
    raw = await get_async_redis().get(cache_key)
    return json.loads(raw) if raw else None


async def set_cached(cache_key: str, data: dict, ttl: int = _DEFAULT_TTL) -> None:
    await get_async_redis().set(cache_key, json.dumps(data), ex=ttl)


async def invalidate(cache_key: str) -> None:
    await get_async_redis().delete(cache_key)


async def invalidate_prefix(pattern: str) -> None:
    redis = get_async_redis()
    keys = await redis.keys(pattern)
    if keys:
        await redis.delete(*keys)
