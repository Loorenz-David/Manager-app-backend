from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from beyo_manager.services.infra.sleep.activity_tracker import ActivityTracker


class SleepMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ActivityTracker.touch()
        return await call_next(request)
