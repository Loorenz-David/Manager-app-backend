from fastapi import Depends, HTTPException, Request

from beyo_manager.config import settings
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims
from beyo_manager.services.infra.redis.async_client import get_async_redis


async def _apply_rate_limit(key: str, max_requests: int, window_seconds: int) -> None:
    if settings.environment in ("development", "testing"):
        return
    redis = get_async_redis()
    async with redis.pipeline(transaction=True) as pipe:
        await pipe.incr(key)
        await pipe.expire(key, window_seconds)
        results = await pipe.execute()
    if results[0] > max_requests:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait before retrying.")


def rate_limit(max_requests: int, window_seconds: int, key_prefix: str):
    """Rate limit for authenticated endpoints — keys by user_id from JWT."""
    async def _check(claims: dict = Depends(get_jwt_claims)) -> None:
        user_id = claims.get("user_id", "anonymous")
        key = f"{settings.redis_key_prefix}:ratelimit:{key_prefix}:{user_id}"
        await _apply_rate_limit(key, max_requests, window_seconds)
    return _check


def ip_rate_limit(max_requests: int, window_seconds: int, key_prefix: str):
    """Rate limit for unauthenticated endpoints — keys by client IP."""
    async def _check(request: Request) -> None:
        forwarded = request.headers.get("X-Forwarded-For")
        ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
        key = f"{settings.redis_key_prefix}:ratelimit:{key_prefix}:{ip}"
        await _apply_rate_limit(key, max_requests, window_seconds)
    return _check
