from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import select

from beyo_manager.domain.emails.arrival_notifications import emit_arrival_realtime_events
from beyo_manager.domain.execution.payloads.sync_email_threads_targeted import (
    SyncEmailThreadsTargetedPayload,
)
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.execution.execution_task import ExecutionTask
from beyo_manager.services.commands.emails._sync_email_threads_targeted_core import (
    execute_targeted_threads_sync,
)
from beyo_manager.services.commands.emails.requests.sync_thread_targeted_request import (
    SyncThreadsBatchTargetedRequest,
)
from beyo_manager.services.infra.audit.write_audit import write_audit
from beyo_manager.sockets.worker_emitter import emit_to_user_room

EMAIL_THREADS_SYNCED_EVENT = "email.threads.synced"


async def handle_sync_email_threads_targeted(payload: dict, task_client_id: str) -> None:
    task_payload = SyncEmailThreadsTargetedPayload(**payload)
    task_payload_dict = asdict(task_payload)
    request = SyncThreadsBatchTargetedRequest(
        connection_client_id=task_payload.connection_client_id,
        thread_client_ids=task_payload.thread_client_ids,
        entity_type=task_payload.entity_type,
        entity_client_ids=task_payload.entity_client_ids,
        major_entity_type=task_payload.major_entity_type,
        major_entity_client_id=task_payload.major_entity_client_id,
        max_threads=task_payload.max_threads,
    )

    result: dict
    async for session in get_db_session():
        is_final_attempt = False

        try:
            async with session.begin():
                task_result = await session.execute(
                    select(ExecutionTask).where(ExecutionTask.client_id == task_client_id)
                )
                task = task_result.scalar_one_or_none()
                is_final_attempt = task is not None and (task.try_count + 1) >= task.max_try
                result = await execute_targeted_threads_sync(
                    session=session,
                    workspace_id=task_payload.workspace_id,
                    user_id=task_payload.requested_by_user_id,
                    request=request,
                )
                await write_audit(
                    session=session,
                    event="email.threads.sync_targeted_batch",
                    workspace_id=task_payload.workspace_id,
                    actor_user_id=task_payload.requested_by_user_id,
                    resource_type="email_connection",
                    resource_client_id=(
                        result["connection_client_id"] or task_payload.connection_client_id
                    ),
                    detail={
                        "task_client_id": task_client_id,
                        **result,
                    },
                )
        except Exception as exc:
            if is_final_attempt:
                failure_payload = {
                    **task_payload_dict,
                    "task_client_id": task_client_id,
                    "connection_client_id": task_payload.connection_client_id,
                    "sync_success": False,
                    "sync_error": str(exc),
                }
                await emit_to_user_room(
                    user_id=task_payload.requested_by_user_id,
                    event=EMAIL_THREADS_SYNCED_EVENT,
                    payload=failure_payload,
                )
            raise
        break

    success_payload = {
        **task_payload_dict,
        "task_client_id": task_client_id,
        "connection_client_id": result["connection_client_id"],
        "requested_thread_count": result["requested_thread_count"],
        "synced_thread_count": result["synced_thread_count"],
        "searched_rfc_message_id_count": result["searched_rfc_message_id_count"],
        "matched_uid_count": result["matched_uid_count"],
        "fetched_message_count": result["fetched_message_count"],
        "created_message_count": result["created_message_count"],
        "existing_message_count": result["existing_message_count"],
        "threads_with_new_messages": result["threads_with_new_messages"],
        "thread_ids_with_new_messages": result["thread_ids_with_new_messages"],
        "thread_errors": result["thread_errors"],
        "sync_success": result["sync_success"],
        "sync_error": result["sync_error"],
        "connection_client_ids": result["connection_client_ids"],
    }
    await emit_to_user_room(
        user_id=task_payload.requested_by_user_id,
        event=EMAIL_THREADS_SYNCED_EVENT,
        payload=success_payload,
    )
    await emit_arrival_realtime_events(result["realtime_events"])
