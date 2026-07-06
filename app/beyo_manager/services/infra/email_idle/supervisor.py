from __future__ import annotations

import asyncio
import hashlib
import logging
import signal
from dataclasses import dataclass

from sqlalchemy import select

from beyo_manager.config import settings
from beyo_manager.domain.emails.enums import EmailConnectionStatusEnum
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.services.infra.email_idle.connection_watcher import EmailConnectionWatcher
from beyo_manager.services.infra.sleep.activity_tracker import ActivityTracker

logger = logging.getLogger(__name__)

_shutdown_event: asyncio.Event = asyncio.Event()


@dataclass(slots=True)
class WatchHandle:
    connection_id: str
    task: asyncio.Task[None]


async def run_email_idle_watcher() -> None:
    settings.validate_email_idle_settings()
    if not settings.email_idle_enabled:
        logger.info("email_idle_watcher_disabled")
        return

    _register_shutdown_handler()
    active: dict[str, WatchHandle] = {}
    logger.info(
        "email_idle_watcher_started | shard_index=%d shard_count=%d reconcile_seconds=%d",
        settings.email_idle_shard_index,
        settings.email_idle_shard_count,
        settings.email_idle_reconcile_seconds,
    )

    try:
        while not _shutdown_event.is_set():
            if ActivityTracker.is_sleeping():
                await _cancel_all(active, reason="sleep")
                await _wait_until_awake()
                continue
            await _reconcile(active)
            await _sleep_or_shutdown(settings.email_idle_reconcile_seconds)
    finally:
        await _cancel_all(active, reason="shutdown")
        logger.info("email_idle_watcher_stopped")


def owns_connection(client_id: str) -> bool:
    digest = hashlib.sha256(client_id.encode("utf-8")).digest()
    shard = int.from_bytes(digest[:8], "big") % settings.email_idle_shard_count
    return shard == settings.email_idle_shard_index


def _register_shutdown_handler() -> None:
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _shutdown_event.set)


async def _reconcile(active: dict[str, WatchHandle]) -> None:
    finished_ids = [
        connection_id
        for connection_id, handle in active.items()
        if handle.task.done()
    ]
    for connection_id in finished_ids:
        handle = active.pop(connection_id)
        try:
            exc = handle.task.exception()
        except asyncio.CancelledError:
            exc = None
        if exc is not None:
            logger.error(
                "email_idle_watch_failed | connection_id=%s error=%s",
                connection_id,
                str(exc)[:200],
                exc_info=exc,
            )
        else:
            logger.warning(
                "email_idle_watch_exited | connection_id=%s",
                connection_id,
            )

    owned_connections = await _load_owned_connections()
    desired_ids = {connection.client_id for connection in owned_connections}
    current_ids = set(active.keys())

    to_stop = current_ids - desired_ids
    to_start = [connection for connection in owned_connections if connection.client_id not in current_ids]

    for connection_id in to_stop:
        handle = active.pop(connection_id)
        handle.task.cancel()
        try:
            await handle.task
        except asyncio.CancelledError:
            pass
        logger.info("email_idle_watch_stopped | connection_id=%s reason=reconcile", connection_id)

    for connection in to_start:
        watcher = EmailConnectionWatcher(connection, _shutdown_event)
        task = asyncio.create_task(watcher.run(), name=f"email-idle:{connection.client_id}")
        active[connection.client_id] = WatchHandle(connection_id=connection.client_id, task=task)
        logger.info(
            "email_idle_watch_starting | connection_id=%s email=%s owner_user_id=%s folder=%s",
            connection.client_id,
            connection.email_address,
            connection.owner_user_id,
            connection.inbox_folder,
        )

    logger.debug(
        "email_idle_reconcile | desired=%d active=%d started=%d stopped=%d",
        len(desired_ids),
        len(active),
        len(to_start),
        len(to_stop),
    )


async def _load_owned_connections() -> list[EmailConnection]:
    async for session in get_db_session():
        result = await session.execute(
            select(EmailConnection).where(
                EmailConnection.status == EmailConnectionStatusEnum.ACTIVE.value,
                EmailConnection.deleted_at.is_(None),
            )
        )
        connections = result.scalars().all()
        return [connection for connection in connections if owns_connection(connection.client_id)]
    return []


async def _cancel_all(active: dict[str, WatchHandle], *, reason: str) -> None:
    handles = list(active.values())
    active.clear()
    for handle in handles:
        handle.task.cancel()
    for handle in handles:
        try:
            await handle.task
        except asyncio.CancelledError:
            pass
        logger.info("email_idle_watch_stopped | connection_id=%s reason=%s", handle.connection_id, reason)


async def _wait_until_awake() -> None:
    while ActivityTracker.is_sleeping() and not _shutdown_event.is_set():
        await _sleep_or_shutdown(2)


async def _sleep_or_shutdown(seconds: int) -> None:
    try:
        await asyncio.wait_for(_shutdown_event.wait(), timeout=seconds)
    except asyncio.TimeoutError:
        return
