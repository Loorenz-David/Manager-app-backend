from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware

from beyo_manager.core.logging.config import log_event
from beyo_manager.core.logging.context import bind_request_context, clear_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        corr = request.headers.get("x-correlation-id")
        _, request_id = bind_request_context(correlation_id=corr)
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            log_event(
                "http.request.error",
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
                error=str(exc),
            )
            clear_context()
            raise

        duration_ms = int((time.perf_counter() - started) * 1000)
        response.headers["x-request-id"] = request_id
        if corr:
            response.headers["x-correlation-id"] = corr

        log_event(
            "http.request.completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        clear_context()
        return response
