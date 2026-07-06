from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.emails.enums import EmailConnectionStatusEnum
from beyo_manager.domain.emails.serializers import serialize_email_connection
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_sync_state import EmailSyncState
from beyo_manager.services.commands.emails.requests.create_email_connection_request import (
    CreateEmailConnectionRequest,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.audit.write_audit import write_audit
from beyo_manager.services.infra.crypto.field_encryption import encrypt_field


async def create_email_connection(ctx: ServiceContext) -> dict:
    request = CreateEmailConnectionRequest.model_validate(ctx.incoming_data)

    try:
        async with maybe_begin(ctx.session):
            connection = EmailConnection(
                workspace_id=ctx.workspace_id,
                owner_user_id=ctx.user_id,
                email_address=request.email_address,
                display_name=request.display_name,
                provider_type=request.provider_type.value,
                status=EmailConnectionStatusEnum.ACTIVE.value,
                smtp_host=request.smtp_host,
                smtp_port=request.smtp_port,
                smtp_security=request.smtp_security.value,
                smtp_username=request.smtp_username,
                smtp_password_encrypted=encrypt_field(request.smtp_password),
                imap_host=request.imap_host,
                imap_port=request.imap_port,
                imap_security=request.imap_security.value,
                imap_username=request.imap_username,
                imap_password_encrypted=encrypt_field(request.imap_password),
                inbox_folder=request.inbox_folder,
            )
            ctx.session.add(connection)
            await ctx.session.flush()

            ctx.session.add(
                EmailSyncState(
                    connection_id=connection.client_id,
                    folder=request.inbox_folder,
                    last_seen_uid=0,
                )
            )

            await write_audit(
                session=ctx.session,
                event="email_connection.created",
                workspace_id=ctx.workspace_id,
                actor_user_id=ctx.user_id,
                resource_type="email_connection",
                resource_client_id=connection.client_id,
                detail={
                    "email_address": connection.email_address,
                    "provider_type": connection.provider_type,
                },
            )
        return {"email_connection": serialize_email_connection(connection)}
    except IntegrityError as exc:
        raise ConflictError("Email connection could not be created.") from exc
