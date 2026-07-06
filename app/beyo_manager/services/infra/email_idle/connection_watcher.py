from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from beyo_manager.config import settings
from beyo_manager.domain.emails.enums import EmailConnectionStatusEnum
from beyo_manager.domain.execution.enums import ExecutionTaskStateEnum, TaskType
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.execution.execution_payload import ExecutionPayload
from beyo_manager.models.tables.execution.execution_task import ExecutionTask
from beyo_manager.services.infra.crypto.field_encryption import decrypt_field
from beyo_manager.services.infra.email_idle.idle_client import (
    AioImapIdleClient,
    IdleNotSupportedError,
)
from beyo_manager.services.infra.execution.task_factory import create_instant_task

logger = logging.getLogger(__name__)

_ACTIVE_SYNC_STATES = (
    ExecutionTaskStateEnum.OPEN,
    ExecutionTaskStateEnum.PENDING,
    ExecutionTaskStateEnum.IN_PROGRESS,
    ExecutionTaskStateEnum.RETRYING,
    ExecutionTaskStateEnum.RETRY_SCHEDULED,
)


class EmailConnectionWatcher:
    def __init__(self, connection: EmailConnection, shutdown_event: asyncio.Event) -> None:
        self._connection = connection
        self._shutdown_event = shutdown_event
        self._enqueue_task: asyncio.Task[None] | None = None

    async def run(self) -> None:
        attempt = 0
        while not self._shutdown_event.is_set():
            client: AioImapIdleClient | None = None
            try:
                client = self._build_idle_client(self._connection)
                await client.connect_and_login()
                await client.select_folder(self._connection.inbox_folder)
                await client.ensure_idle_supported()
                await self._clear_connection_error()
                attempt = 0
                logger.info(
                    "email_idle_watch_started | connection_id=%s folder=%s",
                    self._connection.client_id,
                    self._connection.inbox_folder,
                )

                while not self._shutdown_event.is_set():
                    events = await client.idle_once(
                        renew_seconds=settings.email_idle_renew_seconds,
                        stop_event=self._shutdown_event,
                    )
                    logger.info(
                        "email_idle_renew | connection_id=%s events=%d",
                        self._connection.client_id,
                        len(events),
                    )
                    for event in events:
                        if event.indicates_new_mail:
                            await self._schedule_debounced_sync(event.raw)
            except asyncio.CancelledError:
                raise
            except IdleNotSupportedError as exc:
                logger.info(
                    "email_idle_not_supported | connection_id=%s error=%s",
                    self._connection.client_id,
                    str(exc),
                )
                await self._set_transient_error(str(exc))
                return
            except Exception as exc:
                if self._is_auth_error(exc):
                    logger.warning(
                        "email_idle_auth_failed | connection_id=%s error=%s",
                        self._connection.client_id,
                        str(exc)[:200],
                    )
                    await self._mark_auth_failed(str(exc))
                    return
                attempt += 1
                delay = min(2 ** max(attempt - 1, 0), settings.email_idle_backoff_max_seconds)
                logger.warning(
                    "email_idle_reconnect_backoff | connection_id=%s attempt=%d delay_seconds=%d error=%s",
                    self._connection.client_id,
                    attempt,
                    delay,
                    str(exc)[:200],
                )
                await self._set_transient_error(str(exc))
                await self._sleep_or_shutdown(delay)
            finally:
                if client is not None:
                    await client.logout()

        if self._enqueue_task is not None:
            self._enqueue_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._enqueue_task

    async def _schedule_debounced_sync(self, reason: str) -> None:
        if self._enqueue_task is not None and not self._enqueue_task.done():
            logger.info(
                "email_idle_signal_coalesced | connection_id=%s reason=%s",
                self._connection.client_id,
                reason[:200],
            )
            return
        self._enqueue_task = asyncio.create_task(self._debounced_enqueue(reason))

    async def _debounced_enqueue(self, reason: str) -> None:
        await self._sleep_or_shutdown(settings.email_idle_debounce_seconds)
        if self._shutdown_event.is_set():
            return
        if await self._has_active_sync():
            logger.info(
                "email_idle_sync_skip_existing | connection_id=%s reason=%s",
                self._connection.client_id,
                reason[:200],
            )
            return
        async for session in get_db_session():
            async with session.begin():
                await create_instant_task(
                    session=session,
                    task_type=TaskType.EMAIL_INBOX_SYNC,
                    payload={
                        "connection_client_id": self._connection.client_id,
                        "workspace_id": self._connection.workspace_id,
                        "requested_by_user_id": self._connection.owner_user_id,
                    },
                    max_try=3,
                )
            logger.info(
                "email_idle_sync_enqueued | connection_id=%s requested_by=%s",
                self._connection.client_id,
                self._connection.owner_user_id,
            )
            return

    async def _has_active_sync(self) -> bool:
        async for session in get_db_session():
            result = await session.execute(
                select(ExecutionTask.client_id)
                .join(ExecutionPayload, ExecutionPayload.execution_task_id == ExecutionTask.client_id)
                .where(
                    ExecutionTask.task_type == TaskType.EMAIL_INBOX_SYNC,
                    ExecutionTask.state.in_(_ACTIVE_SYNC_STATES),
                    ExecutionPayload.payload["connection_client_id"].as_string() == self._connection.client_id,
                )
                .limit(1)
            )
            return result.scalar_one_or_none() is not None
        return False

    async def _mark_auth_failed(self, error: str) -> None:
        await self._update_connection(
            status=EmailConnectionStatusEnum.AUTH_FAILED.value,
            last_error=error[:512],
        )

    async def _set_transient_error(self, error: str) -> None:
        await self._update_connection(last_error=error[:512])

    async def _clear_connection_error(self) -> None:
        await self._update_connection(
            status=EmailConnectionStatusEnum.ACTIVE.value,
            last_error=None,
        )

    async def _update_connection(
        self,
        *,
        status: str | None = None,
        last_error: str | None | Any = ...,
    ) -> None:
        async for session in get_db_session():
            async with session.begin():
                result = await session.execute(
                    select(EmailConnection).where(EmailConnection.client_id == self._connection.client_id)
                )
                connection = result.scalar_one_or_none()
                if connection is None:
                    return
                if status is not None:
                    connection.status = status
                    self._connection.status = status
                if last_error is not ...:
                    connection.last_error = last_error
                    self._connection.last_error = last_error
                connection.updated_at = datetime.now(timezone.utc)
            return

    async def _sleep_or_shutdown(self, seconds: int) -> None:
        try:
            await asyncio.wait_for(self._shutdown_event.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            return

    def _build_idle_client(self, connection: EmailConnection) -> AioImapIdleClient:
        return AioImapIdleClient(
            host=connection.imap_host,
            port=connection.imap_port,
            security=connection.imap_security,
            username=connection.imap_username,
            password=decrypt_field(connection.imap_password_encrypted),
        )

    def _is_auth_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return any(token in message for token in ("auth", "authentication", "login", "invalid credentials"))
