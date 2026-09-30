import logging
import threading

import jwt
from cachetools import TTLCache
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from beyo_manager.config import settings
from beyo_manager.errors.availability import AuthUnavailableError
from beyo_manager.routers.http.response import auth_unavailable_http_exception
from beyo_manager.services.infra import auth

logger = logging.getLogger(__name__)

_bearer = HTTPBearer()

_claim_cache: TTLCache = TTLCache(maxsize=2000, ttl=60)
_cache_lock = threading.Lock()


async def get_jwt_claims(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    # FastAPI injects the Request by annotation (the default is ignored for routes);
    # the default keeps direct calls — get_jwt_claims(credentials) — working.
    request: Request = None,  # type: ignore[assignment]
) -> dict:
    token = credentials.credentials

    with _cache_lock:
        cached = _claim_cache.get(token)
    if cached is not None:
        _stamp_identity(request, cached)
        return cached

    try:
        claims = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    jti = claims.get("jti")
    if jti and await _is_blocklisted(jti):
        raise HTTPException(status_code=401, detail="Token has been revoked.")

    with _cache_lock:
        _claim_cache[token] = claims

    _stamp_identity(request, claims)
    return claims


def _stamp_identity(request: Request | None, claims: dict) -> None:
    """Mark the request as made by a validated identity, for ActivityMiddleware.

    Only ever called after validation succeeded, so anonymous, invalid, revoked and
    unverifiable (503) requests are never stamped. No I/O.
    """
    if request is None:
        return
    request.state.beyo_identity = {
        "user_id": claims.get("user_id"),
        "app_scope": claims.get("app_scope"),
    }


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
    # Unable to *check* revocation is not proof the token is bad: fail closed, but as
    # a 503 auth_unavailable (retry) — never a 401, which tells the client to sign out.
    try:
        return await auth.is_token_blocklisted(jti)
    except Exception as exc:
        logger.warning(
            "auth.blocklist_unavailable | where=jwt_dep exc_type=%s",
            type(exc).__name__,
            extra={"event_type": "auth.blocklist_unavailable", "service": "auth"},
        )
        raise auth_unavailable_http_exception(
            AuthUnavailableError(
                "Token verification is temporarily unavailable. Please retry.",
                reason="token_blocklist_unavailable",
            )
        ) from exc
