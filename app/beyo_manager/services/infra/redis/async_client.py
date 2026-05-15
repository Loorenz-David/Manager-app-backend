from redis.asyncio import Redis as AsyncRedis

from beyo_manager.config import settings

_async_client: AsyncRedis | None = None


def get_async_redis() -> AsyncRedis:
    global _async_client
    if _async_client is None:
        _async_client = AsyncRedis.from_url(settings.redis_url, decode_responses=True)
    return _async_client
