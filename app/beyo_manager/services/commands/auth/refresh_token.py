from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from beyo_manager.config import settings
from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.services.context import ServiceContext


async def refresh_token(ctx: ServiceContext) -> dict:
    raw_refresh = ctx.incoming_data.get("refresh_token")
    if not raw_refresh:
        raise PermissionDenied("Refresh token missing.")
    try:
        claims = jwt.decode(raw_refresh, settings.jwt_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise PermissionDenied("Invalid refresh token.") from exc

    now = datetime.now(timezone.utc)
    claims.pop("exp", None)
    claims["jti"] = str(uuid4())
    access_token = jwt.encode(
        {**claims, "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes)},
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    return {"access_token": access_token}
