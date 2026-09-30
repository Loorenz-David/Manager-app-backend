"""API heartbeat: proof that the API process is up, and what it holds.

While the API process runs, a lifespan task writes one JSON string, with a TTL::

    {prefix}:system:api_heartbeat = {
        "at":         epoch seconds (float) of this write,
        "started_at": epoch seconds (float) when this API process started serving,
        "sockets":    live socket connections held by this process,
        "users":      distinct users among them
    }

every :data:`HEARTBEAT_INTERVAL_SECONDS`, expiring after :data:`HEARTBEAT_TTL_SECONDS`
(three missed beats). The stop-eligibility check reads it: ``started_at`` is the
fallback when the human-activity key is missing (a fresh wake must not look idle
forever), and the socket counts are informational.

Errors are swallowed and logged at most once per :data:`ERROR_LOG_INTERVAL_SECONDS`;
the loop keeps beating. It ends only by cancellation (lifespan shutdown).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable

from beyo_manager.services.infra.redis import async_client
from beyo_manager.services.infra.redis.keys import make_key

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_SECONDS = 15.0
HEARTBEAT_TTL_SECONDS = 45
WRITE_TIMEOUT_SECONDS = 2.0
ERROR_LOG_INTERVAL_SECONDS = 60.0

# () -> (socket connection count, distinct user count)
SocketCounts = Callable[[], tuple[int, int]]


def api_heartbeat_key() -> str:
    return make_key("system", "api_heartbeat")


def build_heartbeat(*, started_at: float, socket_counts: SocketCounts) -> dict:
    sockets, users = socket_counts()
    return {"at": time.time(), "started_at": started_at, "sockets": sockets, "users": users}


async def write_heartbeat(*, started_at: float, socket_counts: SocketCounts) -> None:
    """One beat. Raises on failure — the loop decides what to do with it."""
    payload = build_heartbeat(started_at=started_at, socket_counts=socket_counts)
    await asyncio.wait_for(
        async_client.get_async_redis().set(
            api_heartbeat_key(), json.dumps(payload), ex=HEARTBEAT_TTL_SECONDS
        ),
        timeout=WRITE_TIMEOUT_SECONDS,
    )


async def run_api_heartbeat(
    *,
    started_at: float,
    socket_counts: SocketCounts,
    interval_seconds: float = HEARTBEAT_INTERVAL_SECONDS,
) -> None:
    """Beat now, then every ``interval_seconds``, until cancelled."""
    last_error_log_at: float | None = None
    while True:
        try:
            await write_heartbeat(started_at=started_at, socket_counts=socket_counts)
        except Exception as exc:  # a missed beat must not end the loop
            now = time.monotonic()
            if last_error_log_at is None or now - last_error_log_at >= ERROR_LOG_INTERVAL_SECONDS:
                last_error_log_at = now
                logger.warning(
                    "api_heartbeat.write_failed | exc_type=%s",
                    type(exc).__name__,
                    extra={"event_type": "api_heartbeat.write_failed", "service": "activity"},
                )
        await asyncio.sleep(interval_seconds)


async def read_api_heartbeat() -> dict | None:
    """The latest heartbeat, or None when absent (API down for > TTL, or never up).

    Async on the shared async client, like ``read_human_activity`` — a CLI calls it
    under ``asyncio.run(...)``. Redis errors propagate; a value that is not valid JSON
    reads as None.
    """
    raw = await async_client.get_async_redis().get(api_heartbeat_key())
    if raw is None:
        return None
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None
