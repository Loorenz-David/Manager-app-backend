import threading

import jwt
from cachetools import TTLCache
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from beyo_manager.config import settings

_bearer = HTTPBearer()

_claim_cache: TTLCache = TTLCache(maxsize=2000, ttl=60)
_cache_lock = threading.Lock()


async def get_jwt_claims(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    token = credentials.credentials

    with _cache_lock:
        if token in _claim_cache:
            return _claim_cache[token]

    try:
        claims = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    jti = claims.get("jti")
    if jti and await _is_blocklisted(jti):
        raise HTTPException(status_code=401, detail="Token has been revoked.")

    with _cache_lock:
        _claim_cache[token] = claims

    return claims


def require_roles(allowed_roles: list[str]):
    allowed_set = set(allowed_roles)

    async def _check(claims: dict = Depends(get_jwt_claims)) -> dict:
        if claims.get("role_name") not in allowed_set:
            raise HTTPException(status_code=403, detail="Insufficient role permissions.")
        return claims

    return _check


def require_app_scope(required_scope: str | list[str]):
    allowed = {required_scope} if isinstance(required_scope, str) else set(required_scope)

    async def _check(claims: dict = Depends(get_jwt_claims)) -> dict:
        if claims.get("app_scope") not in allowed:
            raise HTTPException(status_code=403, detail="This session cannot access this resource.")
        return claims

    return _check


async def _is_blocklisted(jti: str) -> bool:
    try:
        from beyo_manager.services.infra.redis.async_client import get_async_redis
        redis = get_async_redis()
        return await redis.exists(f"{settings.redis_key_prefix}:auth:blocklist:{jti}") == 1
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Auth blocklist unavailable.") from exc
