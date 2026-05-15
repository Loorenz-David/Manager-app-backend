from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_execution_id: ContextVar[str | None] = ContextVar("execution_id", default=None)
_worker_id: ContextVar[str | None] = ContextVar("worker_id", default=None)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


def ensure_correlation_id() -> str:
    value = _correlation_id.get()
    if value:
        return value
    value = _new_id("corr")
    _correlation_id.set(value)
    return value


def bind_request_context(*, correlation_id: str | None = None, request_id: str | None = None) -> tuple[str, str]:
    corr = correlation_id or ensure_correlation_id()
    req = request_id or _new_id("req")
    _correlation_id.set(corr)
    _request_id.set(req)
    return corr, req


def bind_execution_context(execution_id: str | None = None, worker_id: str | None = None) -> tuple[str, str]:
    eid = execution_id or _new_id("exec")
    wid = worker_id or _new_id("wrk")
    _execution_id.set(eid)
    _worker_id.set(wid)
    return eid, wid


def clear_context() -> None:
    _correlation_id.set(None)
    _request_id.set(None)
    _execution_id.set(None)
    _worker_id.set(None)


def get_log_context() -> dict[str, str | None]:
    return {
        "correlation_id": _correlation_id.get(),
        "request_id": _request_id.get(),
        "execution_id": _execution_id.get(),
        "worker_id": _worker_id.get(),
    }
