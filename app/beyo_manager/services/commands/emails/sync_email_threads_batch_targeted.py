from __future__ import annotations

from dataclasses import asdict

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.sync_email_threads_targeted import (
    SyncEmailThreadsTargetedPayload,
)
from beyo_manager.domain.emails.guards import assert_can_access_connection
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.routers.utils.roles import SELLER
from beyo_manager.services.commands.emails._connection_resolver import resolve_email_connection
from beyo_manager.services.commands.emails.requests.sync_thread_targeted_request import (
    SyncThreadsBatchTargetedRequest,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.audit.write_audit import write_audit
from beyo_manager.services.infra.execution.task_factory import create_instant_task


async def sync_email_threads_batch_targeted(ctx: ServiceContext) -> dict:
    request = SyncThreadsBatchTargetedRequest.model_validate(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        resolved_connection: EmailConnection | None = None
        if request.connection_client_id or ctx.role_name == SELLER:
            resolved_connection = await resolve_email_connection(ctx, request.connection_client_id)
            assert_can_access_connection(ctx.user_id, ctx.role_name, resolved_connection.owner_user_id)

        payload = SyncEmailThreadsTargetedPayload(
            workspace_id=ctx.workspace_id,
            requested_by_user_id=ctx.user_id,
            role_name=ctx.role_name,
            connection_client_id=resolved_connection.client_id if resolved_connection else request.connection_client_id,
            thread_client_ids=request.thread_client_ids,
            entity_type=request.entity_type,
            entity_client_ids=request.entity_client_ids,
            major_entity_type=request.major_entity_type,
            major_entity_client_id=request.major_entity_client_id,
            max_threads=request.max_threads,
        )
        task = await create_instant_task(
            session=ctx.session,
            task_type=TaskType.EMAIL_SYNC_TARGETED,
            payload=asdict(payload),
            max_try=3,
        )

        await write_audit(
            session=ctx.session,
            event="email.threads.sync_targeted_enqueued",
            workspace_id=ctx.workspace_id,
            actor_user_id=ctx.user_id,
            resource_type="email_connection",
            resource_client_id=(
                resolved_connection.client_id if resolved_connection is not None else request.connection_client_id
            ),
            detail={
                "enqueued": True,
                "task_client_id": task.client_id,
                **asdict(payload),
            },
        )

    return {
        "enqueued": True,
        "task_client_id": task.client_id,
        "connection_client_id": payload.connection_client_id,
    }
