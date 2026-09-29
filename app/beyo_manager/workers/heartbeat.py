"""Heartbeat file for long-running background processes.

When WORKER_HEARTBEAT_FILE is set, the process touches that file every few seconds
from its event loop; the container health check fails when the file goes stale.
That catches a process that is alive but wedged, which a restart policy cannot see.

It proves the event loop is running, not that a given task is progressing: stuck
tasks are recovered by the task router (stale IN_PROGRESS) and handler timeouts.
It reads and writes nothing in Redis, so it does not affect sleep mode.

Unset (the default, e.g. on the legacy server) it does nothing.
"""

import asyncio
import logging
from pathlib import Path

from beyo_manager.config import settings

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_SECONDS = 10

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
