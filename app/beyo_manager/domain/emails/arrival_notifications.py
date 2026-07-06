from __future__ import annotations

import asyncio
from dataclasses import asdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.emails.enums import (
    EmailMessageDirectionEnum,
    EmailThreadEntityTypeEnum,
)
from beyo_manager.domain.emails.notification_targets import resolve_email_notification_targets
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.services.infra.email_providers.message_processor import ProcessResult
from beyo_manager.services.infra.execution.task_factory import create_instant_task
from beyo_manager.sockets.worker_emitter import emit_to_user_room

EMAIL_THREADS_UPDATED_EVENT = "email.entity_threads.updated"


@dataclass(frozen=True)
class EmailArrivalRealtimeEvent:
    user_id: str
    payload: dict


async def enqueue_arrival_notifications(
    *,
    session: AsyncSession,
    workspace_id: str,
    connection: EmailConnection,
    process_result: ProcessResult,
) -> list[EmailArrivalRealtimeEvent]:
    if not process_result.created_messages:
        return []

    thread_ids = {message.thread_id for message in process_result.created_messages}
    thread_result = await session.execute(
        select(EmailThread).where(
            EmailThread.workspace_id == workspace_id,
            EmailThread.client_id.in_(thread_ids),
        )
    )
    thread_map = {thread.client_id: thread for thread in thread_result.scalars().all()}
    event_state_by_user_id: dict[str, dict[str, set[str] | str | None]] = {}

    for message in process_result.created_messages:
        if message.direction != EmailMessageDirectionEnum.INBOUND.value:
            continue
        thread = thread_map.get(message.thread_id)
        if thread is None or not should_notify_for_inbound_email(thread):
            continue

        target_user_ids = sorted(
            await resolve_email_notification_targets(
                session,
                workspace_id=workspace_id,
                thread=thread,
                connection=connection,
            )
        )
        if not target_user_ids:
            continue

        title = message.subject or f"New email from {message.from_address}"
        body = message.body_preview or message.from_address
        exclude_viewing = []
        if thread.entity_type and thread.entity_client_id:
            exclude_viewing.append({
                "entity_type": thread.entity_type,
                "entity_client_id": thread.entity_client_id,
            })

        await create_instant_task(
            session=session,
            task_type=TaskType.CREATE_NOTIFICATIONS,
            payload=asdict(NotificationPayload(
                notification_type="email_inbound_received",
                user_ids=target_user_ids,
                title=title[:255],
                body=body[:255],
                entity_type=EmailThreadEntityTypeEnum.TASK.value,
                entity_client_id=_resolve_task_client_id(thread),
                exclude_viewing=_resolve_exclude_viewing(thread, exclude_viewing),
            )),
        )
        _accumulate_realtime_event_state(
            event_state_by_user_id=event_state_by_user_id,
            user_ids=target_user_ids,
            thread=thread,
            connection=connection,
            workspace_id=workspace_id,
        )

    return _build_realtime_events(event_state_by_user_id)


async def emit_arrival_realtime_events(events: list[EmailArrivalRealtimeEvent]) -> None:
    if not events:
        return
    await asyncio.gather(*[
        emit_to_user_room(
            user_id=event.user_id,
            event=EMAIL_THREADS_UPDATED_EVENT,
            payload=event.payload,
        )
        for event in events
    ])


def should_notify_for_inbound_email(thread: EmailThread) -> bool:
    return thread.entity_type == EmailThreadEntityTypeEnum.TASK_CUSTOMER_COORDINATION.value


def _resolve_task_client_id(thread: EmailThread) -> str | None:
    if thread.major_entity_type != EmailThreadEntityTypeEnum.TASK.value:
        return None
    return thread.major_entity_client_id


def _resolve_exclude_viewing(thread: EmailThread, fallback: list[dict]) -> list[dict]:
    task_client_id = _resolve_task_client_id(thread)
    if task_client_id:
        return [{
            "entity_type": EmailThreadEntityTypeEnum.TASK.value,
            "entity_client_id": task_client_id,
        }]
    return fallback


def _accumulate_realtime_event_state(
    *,
    event_state_by_user_id: dict[str, dict[str, set[str] | str | None]],
    user_ids: list[str],
    thread: EmailThread,
    connection: EmailConnection,
    workspace_id: str,
) -> None:
    for user_id in user_ids:
        state = event_state_by_user_id.setdefault(user_id, {
            "workspace_id": workspace_id,
            "connection_client_id": connection.client_id,
            "entity_type": thread.entity_type,
            "major_entity_type": thread.major_entity_type,
            "entity_client_ids": set(),
            "major_entity_client_ids": set(),
            "thread_client_ids": set(),
        })
        if thread.entity_client_id:
            state["entity_client_ids"].add(thread.entity_client_id)
        if thread.major_entity_client_id:
            state["major_entity_client_ids"].add(thread.major_entity_client_id)
        state["thread_client_ids"].add(thread.client_id)


def _build_realtime_events(
    event_state_by_user_id: dict[str, dict[str, set[str] | str | None]],
) -> list[EmailArrivalRealtimeEvent]:
    events: list[EmailArrivalRealtimeEvent] = []
    for user_id, state in event_state_by_user_id.items():
        events.append(EmailArrivalRealtimeEvent(
            user_id=user_id,
            payload={
                "workspace_id": state["workspace_id"],
                "connection_client_id": state["connection_client_id"],
                "entity_type": state["entity_type"],
                "entity_client_ids": sorted(state["entity_client_ids"]),
                "major_entity_type": state["major_entity_type"],
                "major_entity_client_ids": sorted(state["major_entity_client_ids"]),
                "thread_client_ids": sorted(state["thread_client_ids"]),
            },
        ))
    return events
