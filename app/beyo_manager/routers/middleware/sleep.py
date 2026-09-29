from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from beyo_manager.services.infra.sleep.activity_tracker import ActivityTracker


def _is_health_check(path: str) -> bool:
    return path == "/health" or path.startswith("/health/")


class SleepMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Health checks are not activity: counting them would keep the system awake
        # forever, and would turn a Redis outage into a 500 before /health can
        # report it as a 503.
        if not _is_health_check(request.url.path):
            ActivityTracker.touch()
        return await call_next(request)
