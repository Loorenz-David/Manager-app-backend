from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.emails.enums import EmailConnectionStatusEnum
from beyo_manager.domain.emails.guards import assert_can_access_connection
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.audit.write_audit import write_audit


async def delete_email_connection(ctx: ServiceContext) -> dict:
    connection_client_id = str(ctx.incoming_data.get("connection_client_id") or "").strip()
    if not connection_client_id:
        raise NotFound("Email connection not found.")

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(EmailConnection).where(
                EmailConnection.workspace_id == ctx.workspace_id,
                EmailConnection.client_id == connection_client_id,
                EmailConnection.deleted_at.is_(None),
            )
        )
        connection = result.scalar_one_or_none()
        if connection is None:
            raise NotFound("Email connection not found.")

        assert_can_access_connection(ctx.user_id, ctx.role_name, connection.owner_user_id)

        connection.deleted_at = datetime.now(timezone.utc)
        connection.status = EmailConnectionStatusEnum.DISABLED.value
        await write_audit(
            session=ctx.session,
            event="email_connection.deleted",
            workspace_id=ctx.workspace_id,
            actor_user_id=ctx.user_id,
            resource_type="email_connection",
            resource_client_id=connection.client_id,
            detail={"email_address": connection.email_address},
        )

    return {"deleted": True}
