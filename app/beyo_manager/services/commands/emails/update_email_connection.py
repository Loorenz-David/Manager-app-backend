from sqlalchemy import select

from beyo_manager.domain.emails.serializers import serialize_email_connection
from beyo_manager.domain.emails.guards import assert_can_access_connection
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.services.commands.emails.requests.update_email_connection_request import (
    UpdateEmailConnectionRequest,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.audit.write_audit import write_audit
from beyo_manager.services.infra.crypto.field_encryption import encrypt_field


async def update_email_connection(ctx: ServiceContext) -> dict:
    request = UpdateEmailConnectionRequest.model_validate(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(EmailConnection).where(
                EmailConnection.workspace_id == ctx.workspace_id,
                EmailConnection.client_id == request.connection_client_id,
                EmailConnection.deleted_at.is_(None),
            )
        )
        connection = result.scalar_one_or_none()
        if connection is None:
            raise NotFound("Email connection not found.")

        assert_can_access_connection(ctx.user_id, ctx.role_name, connection.owner_user_id)
        for field in (
            "display_name",
            "smtp_host",
            "smtp_port",
            "smtp_username",
            "imap_host",
            "imap_port",
            "imap_username",
            "inbox_folder",
        ):
            value = getattr(request, field)
            if value is not None:
                setattr(connection, field, value)

        if request.smtp_security is not None:
            connection.smtp_security = request.smtp_security.value
        if request.imap_security is not None:
            connection.imap_security = request.imap_security.value
        if request.smtp_password is not None:
            connection.smtp_password_encrypted = encrypt_field(request.smtp_password)
        if request.imap_password is not None:
            connection.imap_password_encrypted = encrypt_field(request.imap_password)

        await write_audit(
            session=ctx.session,
            event="email_connection.updated",
            workspace_id=ctx.workspace_id,
            actor_user_id=ctx.user_id,
            resource_type="email_connection",
            resource_client_id=connection.client_id,
            detail={"email_address": connection.email_address},
        )

    return {"email_connection": serialize_email_connection(connection)}
