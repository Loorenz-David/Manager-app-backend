from sqlalchemy import select

from beyo_manager.domain.emails.guards import assert_can_access_connection
from beyo_manager.domain.emails.serializers import serialize_email_connection
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.services.context import ServiceContext


async def get_email_connection(ctx: ServiceContext) -> dict:
    connection_client_id = str(ctx.incoming_data.get("connection_client_id") or "").strip()
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
    return {"email_connection": serialize_email_connection(connection)}
