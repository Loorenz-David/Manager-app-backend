"""Heartbeat and progress files for long-running background processes.

Two files, each off unless its setting names a path (the default, e.g. on the legacy
server, where neither is set and nothing is written):

``WORKER_HEARTBEAT_FILE`` — liveness. Every background process touches it every few
seconds from its event loop; the container health check fails when it goes stale.
That catches a process that is alive but wedged, which a restart policy cannot see.
It proves the event loop is running, not that anything is progressing: a process
blocked on the database keeps it fresh.

``WORKER_PROGRESS_FILE`` — readiness. Only the task router and the two schedulers touch
it, and only from :func:`touch_progress` after a loop iteration whose database work
*succeeded* (a poll that found nothing counts). An iteration that raised does not
touch it, and a database call that hangs never reaches the touch, so the file goes
stale while the loop cannot reach the database. Those loops finish an iteration at
least every :data:`PROGRESS_MAX_IDLE_SECONDS`-ish (router: ``FALLBACK_POLL_SECONDS``;
schedulers: ``POLL_INTERVAL_SECONDS``, and while in-app sleeping they wake at least
that often when this file is set) so an idle process stays fresh. Queue workers do
not touch it: their loop blocks on Redis, not the database.

Neither reads or writes Redis, so neither affects sleep mode.
"""

import asyncio
import logging
from pathlib import Path

from beyo_manager.config import settings

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_SECONDS = 10

# The longest a progress-touching loop may go without a database poll while idle.
# A readiness check treats progress older than 60 s as not ready.
PROGRESS_MAX_IDLE_SECONDS = 20

# Pause after a failed loop iteration: 5 s, doubling, capped here. Reset on success.
ERROR_BACKOFF_BASE_SECONDS = 5.0
ERROR_BACKOFF_MAX_SECONDS = 30.0

_task: asyncio.Task | None = None


async def _beat(path: Path) -> None:
    while True:
        try:
            path.touch()
        except OSError:
            logger.exception("heartbeat_write_failed | path=%s", path)
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)


def start_heartbeat() -> None:
    """Start the heartbeat on the running event loop. Call once, from main()."""
    global _task
    if not settings.worker_heartbeat_file or _task is not None:
        return
    _task = asyncio.get_running_loop().create_task(_beat(Path(settings.worker_heartbeat_file)))


def progress_enabled() -> bool:
    return bool(settings.worker_progress_file)


def touch_progress() -> None:
    """Record one successful loop iteration. No-op when WORKER_PROGRESS_FILE is unset.

    Call it only after the iteration's database work returned; never from an
    exception handler.
    """
    path = settings.worker_progress_file
    if not path:
        return
    try:
        Path(path).touch()
    except OSError:
        logger.exception("progress_write_failed | path=%s", path)


def error_backoff_seconds(consecutive_errors: int) -> float:
    """Seconds to wait after the ``consecutive_errors``-th failed iteration in a row."""
    exponent = max(consecutive_errors - 1, 0)
    return min(ERROR_BACKOFF_BASE_SECONDS * (2 ** min(exponent, 10)), ERROR_BACKOFF_MAX_SECONDS)
