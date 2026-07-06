from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.emails.arrival_notifications import (
    EmailArrivalRealtimeEvent,
    enqueue_arrival_notifications,
)
from beyo_manager.domain.emails.enums import EmailMessageDirectionEnum
from beyo_manager.domain.emails.guards import assert_can_access_connection
from beyo_manager.errors.base import DomainError
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.models.tables.emails.email_sync_state import EmailSyncState
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.routers.utils.roles import SELLER
from beyo_manager.services.commands.emails._actor_role_resolver import resolve_live_role_name
from beyo_manager.services.commands.emails._connection_resolver import (
    resolve_email_connection_for_actor,
)
from beyo_manager.services.commands.emails.requests.sync_thread_targeted_request import (
    SyncThreadsBatchTargetedRequest,
)
from beyo_manager.services.infra.email_providers.message_processor import process_inbound_messages
from beyo_manager.services.infra.email_providers.registry import get_email_provider

MAX_RFC_MESSAGE_IDS_PER_THREAD = 10


async def execute_targeted_threads_sync(
    *,
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
    request: SyncThreadsBatchTargetedRequest,
) -> dict:
    live_role_name = await resolve_live_role_name(
        session,
        user_id=user_id,
        workspace_id=workspace_id,
    )
    resolved_connection: EmailConnection | None = None
    if request.connection_client_id or live_role_name == SELLER:
        resolved_connection = await resolve_email_connection_for_actor(
            session,
            workspace_id,
            user_id,
            request.connection_client_id,
        )
        assert_can_access_connection(user_id, live_role_name, resolved_connection.owner_user_id)

    threads = await _load_threads(session, workspace_id, request, resolved_connection)
    if not threads:
        return _build_empty_response()

    by_connection: dict[str, list[EmailThread]] = defaultdict(list)
    for thread in threads:
        by_connection[thread.connection_id].append(thread)

    connection_map: dict[str, EmailConnection] = {}
    for connection_id in by_connection:
        if resolved_connection is not None:
            connection = resolved_connection
            if connection.client_id != connection_id:
                raise DomainError(f"Email connection {connection_id} not found.")
        else:
            connection_result = await session.execute(
                select(EmailConnection).where(
                    EmailConnection.client_id == connection_id,
                    EmailConnection.deleted_at.is_(None),
                )
            )
            connection = connection_result.scalar_one_or_none()
            if connection is None:
                raise DomainError(f"Email connection {connection_id} not found.")
            assert_can_access_connection(user_id, live_role_name, connection.owner_user_id)
        connection_map[connection_id] = connection

    total_searched_rfc_count = 0
    total_matched_uid_count = 0
    total_fetched_count = 0
    total_created_count = 0
    total_existing_count = 0
    synced_thread_count = 0
    all_new_thread_ids: set[str] = set()
    thread_errors: dict[str, str] = {}
    sync_error: str | None = None
    realtime_events: list[EmailArrivalRealtimeEvent] = []

    for connection_id, connection_threads in by_connection.items():
        connection = connection_map[connection_id]
        thread_rfc_ids: dict[str, list[str]] = {}
        union_ids: list[str] = []
        seen_ids: set[str] = set()

        for thread in connection_threads:
            rfc_ids = await _load_thread_rfc_ids(session, thread.client_id)
            thread_rfc_ids[thread.client_id] = rfc_ids
            for rfc_id in rfc_ids:
                if rfc_id not in seen_ids:
                    union_ids.append(rfc_id)
                    seen_ids.add(rfc_id)

        searchable_threads = [
            thread for thread in connection_threads if thread_rfc_ids[thread.client_id]
        ]
        if not searchable_threads:
            continue

        total_searched_rfc_count += len(union_ids)
        sync_state_result = await session.execute(
            select(EmailSyncState).where(EmailSyncState.connection_id == connection.client_id)
        )
        sync_state = sync_state_result.scalar_one_or_none()
        if sync_state is None:
            error_message = "Email sync state not found."
            for thread in searchable_threads:
                thread_errors[thread.client_id] = error_message
            sync_error = error_message
            continue

        targeted_result = await get_email_provider(connection).search_by_header_ids(
            folder=sync_state.folder,
            rfc_message_ids=union_ids,
        )
        if not targeted_result.success:
            error_message = targeted_result.error or "Targeted sync failed."
            for thread in searchable_threads:
                thread_errors[thread.client_id] = error_message
            sync_error = error_message
            continue

        total_matched_uid_count += targeted_result.matched_uid_count
        total_fetched_count += len(targeted_result.messages)

        try:
            process_result = await process_inbound_messages(
                session=session,
                workspace_id=workspace_id,
                connection=connection,
                inbound_messages=targeted_result.messages,
            )
            realtime_events.extend(await enqueue_arrival_notifications(
                session=session,
                workspace_id=workspace_id,
                connection=connection,
                process_result=process_result,
            ))
            total_created_count += process_result.saved_count
            total_existing_count += process_result.skipped_count
            all_new_thread_ids |= process_result.new_thread_ids
        except Exception as exc:
            error_message = str(exc)
            for thread in searchable_threads:
                thread_errors[thread.client_id] = error_message
            sync_error = error_message
            continue

        synced_thread_count += len(searchable_threads)

    connection_ids = sorted(by_connection.keys())
    threads_with_new_messages = sorted(all_new_thread_ids)
    return {
        "requested_thread_count": len(threads),
        "synced_thread_count": synced_thread_count,
        "searched_rfc_message_id_count": total_searched_rfc_count,
        "matched_uid_count": total_matched_uid_count,
        "fetched_message_count": total_fetched_count,
        "created_message_count": total_created_count,
        "existing_message_count": total_existing_count,
        "threads_with_new_messages": threads_with_new_messages,
        "thread_ids_with_new_messages": threads_with_new_messages,
        "thread_errors": thread_errors,
        "sync_success": not bool(thread_errors),
        "sync_error": sync_error,
        "connection_client_id": connection_ids[0] if len(connection_ids) == 1 else None,
        "connection_client_ids": connection_ids,
        "realtime_events": realtime_events,
    }


def _build_empty_response() -> dict:
    return {
        "requested_thread_count": 0,
        "synced_thread_count": 0,
        "searched_rfc_message_id_count": 0,
        "matched_uid_count": 0,
        "fetched_message_count": 0,
        "created_message_count": 0,
        "existing_message_count": 0,
        "threads_with_new_messages": [],
        "thread_ids_with_new_messages": [],
        "thread_errors": {},
        "sync_success": True,
        "sync_error": None,
        "connection_client_id": None,
        "connection_client_ids": [],
        "realtime_events": [],
    }


async def _load_threads(
    session: AsyncSession,
    workspace_id: str,
    request: SyncThreadsBatchTargetedRequest,
    resolved_connection: EmailConnection | None,
) -> list[EmailThread]:
    stmt = select(EmailThread).where(EmailThread.workspace_id == workspace_id)
    if resolved_connection is not None:
        stmt = stmt.where(EmailThread.connection_id == resolved_connection.client_id)
    elif request.connection_client_id:
        stmt = stmt.where(EmailThread.connection_id == request.connection_client_id)
    if request.thread_client_ids:
        stmt = stmt.where(EmailThread.client_id.in_(request.thread_client_ids))
    if request.entity_type and request.entity_client_ids:
        stmt = stmt.where(
            EmailThread.entity_type == request.entity_type,
            EmailThread.entity_client_id.in_(request.entity_client_ids),
        )
    if request.major_entity_type and request.major_entity_client_id:
        stmt = stmt.where(
            EmailThread.major_entity_type == request.major_entity_type,
            EmailThread.major_entity_client_id == request.major_entity_client_id,
        )
    result = await session.execute(
        stmt.order_by(EmailThread.last_message_at.desc().nullslast()).limit(request.max_threads)
    )
    return result.scalars().all()


async def _load_thread_rfc_ids(session: AsyncSession, thread_client_id: str) -> list[str]:
    result = await session.execute(
        select(EmailMessage.rfc_message_id)
        .where(
            EmailMessage.thread_id == thread_client_id,
            EmailMessage.direction == EmailMessageDirectionEnum.OUTBOUND.value,
            EmailMessage.rfc_message_id.is_not(None),
        )
        .order_by(EmailMessage.sent_or_received_at.desc(), EmailMessage.created_at.desc())
        .limit(MAX_RFC_MESSAGE_IDS_PER_THREAD)
    )
    return [item for item in result.scalars().all() if item]
