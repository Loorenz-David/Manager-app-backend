import logging
import time

import jwt

from beyo_manager.config import settings
from beyo_manager.errors.availability import AuthUnavailableError
from beyo_manager.services.context import ServiceContext


logger = logging.getLogger(__name__)


async def logout_user(ctx: ServiceContext) -> dict:
    # Refresh token first, access token second. If a blocklist write fails the whole
    # logout is refused (503) and the route keeps the cookies, so the client can
    # retry: with this order a failure on the refresh write leaves nothing revoked,
    # and a failure on the access write leaves the access token usable for the retry
    # (the refresh write is an idempotent SET).
    raw_refresh = ctx.incoming_data.get("refresh_token")
    if raw_refresh:
        refresh_claims = _decode_refresh(raw_refresh)
        if refresh_claims is not None:
            await _blocklist_token(refresh_claims)
    await _blocklist_token(ctx.identity)
    if ctx.identity.get("app_scope") == "floor":
        logger.info(
            "auth.floor_device_logout | user_id=%s workspace_id=%s jti=%s",
            ctx.identity.get("user_id"),
            ctx.identity.get("workspace_id"),
            ctx.identity.get("jti"),
            extra={
                "event_type": "auth.floor_device_logout",
                "service": "auth",
                "user_id": ctx.identity.get("user_id"),
                "workspace_id": ctx.identity.get("workspace_id"),
                "jti": ctx.identity.get("jti"),
            },
        )
    return {"logged_out": True}


def _decode_refresh(raw_refresh: str) -> dict | None:
    """An undecodable refresh cookie is garbage, not a session: nothing to revoke."""
    try:
        return jwt.decode(
            raw_refresh,
            settings.jwt_secret_key,
            algorithms=["HS256"],
            options={"verify_exp": False},
        )
    except jwt.PyJWTError:
        return None


async def _blocklist_token(claims: dict) -> None:
    jti = claims.get("jti")
    if not jti:
        return

    exp = claims.get("exp")
    key = f"{settings.redis_key_prefix}:auth:blocklist:{jti}"
    if "exp" in claims and not exp:
        return
    # No exp (a floor device token) → a permanent entry; otherwise outlive the token.
    ttl = None if "exp" not in claims else max(int(exp - time.time()) + 60, 1)

    try:
        from beyo_manager.services.infra.redis.async_client import get_async_redis

        redis = get_async_redis()
        if ttl is None:
            await redis.set(key, "1")
        else:
            await redis.set(key, "1", ex=ttl)
    except Exception as exc:
        # The token could not be revoked, so it stays valid server-side: this logout
        # did not happen, and must not be reported as one.
        raise AuthUnavailableError(
            "Logout could not be completed right now. Please retry.",
            reason="logout_blocklist_unavailable",
        ) from exc
