from beyo_manager.config import settings
from beyo_manager.services.infra.redis import async_client


async def is_token_blocklisted(jti: str) -> bool:
    redis = async_client.get_async_redis()
    key = f"{settings.redis_key_prefix}:auth:blocklist:{jti}"
    return await redis.exists(key) == 1
