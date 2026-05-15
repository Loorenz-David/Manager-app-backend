import time

import jwt

from beyo_manager.config import settings
from beyo_manager.services.context import ServiceContext


async def logout_user(ctx: ServiceContext) -> dict:
    await _blocklist_token(ctx.identity)
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
    exp = claims.get("exp")
    if not jti or not exp:
        return
    from beyo_manager.services.infra.redis.async_client import get_async_redis
    ttl = max(int(exp - time.time()) + 60, 1)
    await get_async_redis().set(f"{settings.redis_key_prefix}:auth:blocklist:{jti}", "1", ex=ttl)
