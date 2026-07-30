from beyo_manager.config import settings
from beyo_manager.services.infra.redis.async_client import get_async_redis


async def is_token_blocklisted(jti: str) -> bool:
    redis = get_async_redis()
    key = f"{settings.redis_key_prefix}:auth:blocklist:{jti}"
    return await redis.exists(key) == 1
