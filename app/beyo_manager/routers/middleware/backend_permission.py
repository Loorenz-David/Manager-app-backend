import re

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from beyo_manager.config import settings


_KNOWN_ROLE_NAMES = {"admin", "manager", "seller", "worker"}


class BackendPermissionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Public or self-service notification endpoints should remain accessible
        # even when a worker token is present.
        if request.url.path in {
            "/api/v1/notifications/vapid-public-key",
            "/api/v1/notifications/push-subscription",
        }:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return await call_next(request)

        try:
            claims = jwt.decode(
                auth_header.removeprefix("Bearer "),
                settings.jwt_secret_key,
                algorithms=["HS256"],
            )
        except jwt.PyJWTError:
            return await call_next(request)

        if claims.get("app_scope") == "admin":
            return await call_next(request)

        # Prefer role-based gating to match router-level `require_roles(...)` checks.
        # If token includes a known role name, defer authorization to route dependencies.
        role_name = str(claims.get("role_name", "")).lower()
        if role_name in _KNOWN_ROLE_NAMES:
            return await call_next(request)

        # Backward-compatibility fallback for tokens that only contain granular permissions.
        allowed = set(claims.get("backend_permissions", []))
        normalized = _normalize_api_path(f"{request.method}:{request.url.path}")
        if normalized not in allowed:
            return JSONResponse(
                status_code=403,
                content={"error": "Your role does not have access to this endpoint."},
            )
        return await call_next(request)


def _normalize_api_path(key: str) -> str:
    return re.sub(r"/[a-z]{2,5}_[A-Z0-9]{10,}", "/<client_id>", key)
