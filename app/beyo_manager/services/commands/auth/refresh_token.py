from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from beyo_manager.config import settings
from beyo_manager.errors.permissions import RefreshTokenRejected
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.auth import is_token_blocklisted


async def refresh_token(ctx: ServiceContext) -> dict:
    raw_refresh = ctx.incoming_data.get("refresh_token")
    requested_scope = ctx.incoming_data.get("scope")
    if not requested_scope:
        raise RefreshTokenRejected("Refresh scope missing.", reason="refresh_scope_missing")
    if requested_scope == "floor":
        raise RefreshTokenRejected(
            "Floor sessions cannot be refreshed.",
            reason="floor_scope_not_refreshable",
        )
    if not raw_refresh:
        raise RefreshTokenRejected("Refresh token missing.", reason="refresh_cookie_missing")
    try:
        claims = jwt.decode(raw_refresh, settings.jwt_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise RefreshTokenRejected("Invalid refresh token.", reason="refresh_token_invalid") from exc
    if "exp" not in claims:
        raise RefreshTokenRejected(
            "Invalid refresh token.",
            reason="refresh_token_invalid",
        )
    token_type = claims.get("token_type")
    if token_type not in (None, "refresh"):
        raise RefreshTokenRejected(
            "Invalid refresh token.",
            reason="refresh_token_invalid",
        )
    if claims.get("app_scope") != requested_scope:
        raise RefreshTokenRejected("Refresh token scope mismatch.", reason="scope_mismatch")
    jti = claims.get("jti")
    if not jti:
        raise RefreshTokenRejected(
            "Invalid refresh token.",
            reason="refresh_token_invalid",
        )
    try:
        revoked = await is_token_blocklisted(jti)
    except Exception as exc:
        raise RefreshTokenRejected(
            "Refresh token verification unavailable.",
            reason="refresh_blocklist_unavailable",
        ) from exc
    if revoked:
        raise RefreshTokenRejected(
            "Refresh token has been revoked.",
            reason="refresh_token_revoked",
        )

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
    claims["token_type"] = "access"
    access_token = jwt.encode(
        {**claims, "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes)},
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    return {"access_token": access_token}
