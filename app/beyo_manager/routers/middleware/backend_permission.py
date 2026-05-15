import re

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from beyo_manager.config import settings


class BackendPermissionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/"):
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
