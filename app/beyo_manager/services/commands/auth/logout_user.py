import logging
import time

import jwt

from beyo_manager.config import settings
from beyo_manager.services.context import ServiceContext


logger = logging.getLogger(__name__)


async def logout_user(ctx: ServiceContext) -> dict:
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
    raw_refresh = ctx.incoming_data.get("refresh_token")
    if raw_refresh:
        try:
            refresh_claims = jwt.decode(
                raw_refresh,
                settings.jwt_secret_key,
                algorithms=["HS256"],
                options={"verify_exp": False},
            )
            await _blocklist_token(refresh_claims)
        except Exception:
            pass
    return {"logged_out": True}


async def _blocklist_token(claims: dict) -> None:
    jti = claims.get("jti")
    if not jti:
        return

    exp = claims.get("exp")
    from beyo_manager.services.infra.redis.async_client import get_async_redis

    redis = get_async_redis()
    key = f"{settings.redis_key_prefix}:auth:blocklist:{jti}"
    if "exp" not in claims:
        await redis.set(key, "1")
        return
    if not exp:
        return

    ttl = max(int(exp - time.time()) + 60, 1)
    await redis.set(key, "1", ex=ttl)
