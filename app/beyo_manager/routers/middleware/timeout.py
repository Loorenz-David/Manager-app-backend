import asyncio

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from beyo_manager.config import settings


class TimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, timeout: int = None):
        super().__init__(app)
        self.timeout = timeout or settings.request_timeout_seconds

    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            return JSONResponse({"detail": "Request timed out."}, status_code=504)
