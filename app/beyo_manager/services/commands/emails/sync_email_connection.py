from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.emails.guards import assert_can_access_connection
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_sync_state import EmailSyncState
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.audit.write_audit import write_audit
from beyo_manager.services.infra.execution.task_factory import create_instant_task


def _serialize_sync_state(sync_state: EmailSyncState) -> dict:
    return {
        "client_id": sync_state.client_id,
        "connection_id": sync_state.connection_id,
        "folder": sync_state.folder,
        "uidvalidity": sync_state.uidvalidity,
        "last_seen_uid": sync_state.last_seen_uid,
        "last_sync_at": sync_state.last_sync_at.isoformat() if sync_state.last_sync_at else None,
        "last_successful_sync_at": (
            sync_state.last_successful_sync_at.isoformat()
            if sync_state.last_successful_sync_at
            else None
        ),
        "last_error": sync_state.last_error,
    }


async def sync_email_connection(ctx: ServiceContext) -> dict:
    connection_client_id = str(ctx.incoming_data.get("connection_client_id") or "").strip()

    async with maybe_begin(ctx.session):
        connection_result = await ctx.session.execute(
            select(EmailConnection).where(
                EmailConnection.workspace_id == ctx.workspace_id,
                EmailConnection.client_id == connection_client_id,
                EmailConnection.deleted_at.is_(None),
            )
        )
        connection = connection_result.scalar_one_or_none()
        if connection is None:
            raise NotFound("Email connection not found.")

        assert_can_access_connection(ctx.user_id, ctx.role_name, connection.owner_user_id)

        sync_state_result = await ctx.session.execute(
            select(EmailSyncState).where(EmailSyncState.connection_id == connection.client_id)
        )
        sync_state = sync_state_result.scalar_one_or_none()
        if sync_state is None:
            raise NotFound("Email sync state not found.")

        await create_instant_task(
            session=ctx.session,
            task_type=TaskType.EMAIL_INBOX_SYNC,
            payload={
                "connection_client_id": connection.client_id,
                "workspace_id": ctx.workspace_id,
                "requested_by_user_id": ctx.user_id,
            },
            max_try=3,
        )
        await write_audit(
            session=ctx.session,
            event="email_connection.sync_enqueued",
            workspace_id=ctx.workspace_id,
            actor_user_id=ctx.user_id,
            resource_type="email_connection",
            resource_client_id=connection.client_id,
            detail={"folder": sync_state.folder},
        )

    return {"sync_state": _serialize_sync_state(sync_state)}
