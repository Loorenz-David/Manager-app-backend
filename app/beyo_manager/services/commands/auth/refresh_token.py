from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from beyo_manager.config import settings
from beyo_manager.errors.permissions import RefreshTokenRejected
from beyo_manager.services.context import ServiceContext


async def refresh_token(ctx: ServiceContext) -> dict:
    raw_refresh = ctx.incoming_data.get("refresh_token")
    requested_scope = ctx.incoming_data.get("scope")
    if not requested_scope:
        raise RefreshTokenRejected("Refresh scope missing.", reason="refresh_scope_missing")
    if not raw_refresh:
        raise RefreshTokenRejected("Refresh token missing.", reason="refresh_cookie_missing")
    try:
        claims = jwt.decode(raw_refresh, settings.jwt_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise RefreshTokenRejected("Invalid refresh token.", reason="refresh_token_invalid") from exc
    if claims.get("app_scope") != requested_scope:
        raise RefreshTokenRejected("Refresh token scope mismatch.", reason="scope_mismatch")

    now = datetime.now(timezone.utc)
    claims.pop("exp", None)
    if "workspace_specialization" not in claims:
        workspace_role_name = claims.get("workspace_role_name")
        role_name = claims.get("role_name")
        claims["workspace_specialization"] = (
            workspace_role_name
            if workspace_role_name and workspace_role_name != role_name
            else None
        )
    claims["jti"] = str(uuid4())
    access_token = jwt.encode(
        {**claims, "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes)},
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    return {"access_token": access_token}
