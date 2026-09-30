"""Human activity: the signal that decides whether production may be stopped.

Infrastructure stops production when nobody has *used* it for a while. Requests alone
are not that signal — the frontend polls, refetches on focus and fires automatic
mutations — so this module records only events that stand for a person:

* an authenticated HTTP request the client marks as human (``X-Beyo-Activity: user``),
  or an unmarked non-GET (see :func:`counts_as_human`) — recorded by
  ``routers.middleware.activity.ActivityMiddleware`` (source ``http``);
* a successful ``POST /auth/refresh`` not marked ``background`` (source ``refresh``);
* a socket ``view_entity`` / ``leave_entity`` (source ``socket``).

Storage — one Redis hash, **no TTL** (a missing key means "never recorded", which the
eligibility check must not confuse with "idle"; it falls back to the API heartbeat's
``started_at``)::

    {prefix}:activity:human
        last_at              epoch seconds (float, time.time()) of the latest event, any scope
        last_at:<app_scope>  epoch seconds of the latest event in that scope
        last_source          "http" | "socket" | "refresh" — source of the latest write

All three fields are written by one HSET, so they are always consistent with each other.

Throttle — at most one write per ``app_scope`` per :data:`THROTTLE_SECONDS`, kept in
process (there is exactly one API process). The slot is claimed when the write is
*attempted*, not when it succeeds, so a Redis outage costs one failed attempt per scope
per window, never one per request. Consequence: a stored timestamp may lag the real
last event by up to the window, which is far below any idle threshold.

Failure — recording never raises. A write is bounded by :data:`WRITE_TIMEOUT_SECONDS`;
any error (timeout, connection, anything) is swallowed and logged at most once per
:data:`ERROR_LOG_INTERVAL_SECONDS`.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from beyo_manager.services.infra.redis import async_client
from beyo_manager.services.infra.redis.keys import make_key

logger = logging.getLogger(__name__)

ACTIVITY_HEADER = "X-Beyo-Activity"

SOURCE_HTTP = "http"
SOURCE_SOCKET = "socket"
SOURCE_REFRESH = "refresh"

THROTTLE_SECONDS = 30.0
WRITE_TIMEOUT_SECONDS = 0.5
ERROR_LOG_INTERVAL_SECONDS = 60.0

_UNKNOWN_SCOPE = "unknown"
# The throttle's clock (a module attribute so a test can move it without touching the
# event loop's own time.monotonic).
_monotonic = time.monotonic
_READ_METHODS = frozenset({"GET", "HEAD"})

# app_scope -> time.monotonic() of the last write *attempt*. Mutated only from the event
# loop with no await between check and set, so it needs no lock.
_last_write_by_scope: dict[str, float] = {}
_last_error_log_at: float | None = None


def human_activity_key() -> str:
    # Resolved at call time: the prefix is a setting (and tests isolate it per run).
    return make_key("activity", "human")


def counts_as_human(method: str, header_value: str | None) -> bool:
    """Whether a request's intent marks it as a human event.

    ``user`` (any case, surrounding space ignored) → yes, whatever the method.
    Header absent → yes unless the method is a read (GET, or HEAD, which is a GET
    without a body). ``background`` or any other value → no: an unrecognised
    marking is never promoted to human.

    Authentication, OPTIONS and the response status are the caller's checks.
    """
    if header_value is None:
        return method.upper() not in _READ_METHODS
    return header_value.strip().lower() == "user"


def _claim_slot(app_scope: str, now: float) -> bool:
    last = _last_write_by_scope.get(app_scope)
    if last is not None and now - last < THROTTLE_SECONDS:
        return False
    _last_write_by_scope[app_scope] = now
    return True


def _log_failure(exc: BaseException) -> None:
    global _last_error_log_at
    now = _monotonic()
    if _last_error_log_at is not None and now - _last_error_log_at < ERROR_LOG_INTERVAL_SECONDS:
        return
    _last_error_log_at = now
    # The exception type only: a connection error's message can carry the Redis URL.
    logger.warning(
        "human_activity.record_failed | exc_type=%s",
        type(exc).__name__,
        extra={"event_type": "human_activity.record_failed", "service": "activity"},
    )


async def record_human_activity(
    *,
    app_scope: str | None,
    source: str,
    user_id: str | None = None,
) -> bool:
    """Record one human event, throttled per scope. Never raises.

    Returns True when a write reached Redis, False when throttled or failed.
    ``user_id`` is not stored — the stop decision needs only *when* and *which app*;
    it is logged at debug level on an actual write.
    """
    try:
        scope = str(app_scope) if app_scope else _UNKNOWN_SCOPE
        if not _claim_slot(scope, _monotonic()):
            return False
        at = time.time()
        redis = async_client.get_async_redis()
        await asyncio.wait_for(
            redis.hset(
                human_activity_key(),
                mapping={
                    "last_at": repr(at),
                    f"last_at:{scope}": repr(at),
                    "last_source": source,
                },
            ),
            timeout=WRITE_TIMEOUT_SECONDS,
        )
        logger.debug(
            "human_activity.recorded | scope=%s source=%s user_id=%s", scope, source, user_id
        )
        return True
    except Exception as exc:  # recording must never fail its caller
        _log_failure(exc)
        return False


@dataclass(frozen=True)
class HumanActivity:
    """What :func:`read_human_activity` found. ``last_at`` is None when never recorded."""

    last_at: float | None
    by_scope: dict[str, float] = field(default_factory=dict)
    last_source: str | None = None


async def read_human_activity() -> HumanActivity:
    """Read the human-activity hash, for the stop-eligibility CLI.

    Async, on the shared async client: a CLI run inside the API container calls it once
    under ``asyncio.run(...)`` — a fresh process, so the client binds to that loop.
    Unlike recording, errors **propagate**: "Redis unreachable" must not read as
    "nobody active". A missing key returns ``HumanActivity(last_at=None)``.
    """
    raw = await async_client.get_async_redis().hgetall(human_activity_key())
    by_scope: dict[str, float] = {}
    for name, value in raw.items():
        if name.startswith("last_at:"):
            parsed = _as_float(value)
            if parsed is not None:
                by_scope[name.removeprefix("last_at:")] = parsed
    return HumanActivity(
        last_at=_as_float(raw.get("last_at")),
        by_scope=by_scope,
        last_source=raw.get("last_source"),
    )


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def reset_for_tests() -> None:
    """Forget the in-process throttle and error-log state."""
    global _last_error_log_at
    _last_write_by_scope.clear()
    _last_error_log_at = None
