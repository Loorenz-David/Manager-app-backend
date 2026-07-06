from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.emails.enums import EmailConnectionStatusEnum, EmailProviderTypeEnum, EmailSecurityEnum
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_sync_state import EmailSyncState
from beyo_manager.services.infra.crypto.field_encryption import encrypt_field

# ---------------------------------------------------------------------------
# Fill in the Gmail App Password for Stina's connection before running
# bootstrap. Leave empty to skip the seed.
# ---------------------------------------------------------------------------
_APP_PASSWORD = "hktrdsogubjavaak"

_OWNER_WORKER_NAME = "Stina"

_EMAIL_ADDRESS = "loorenz.david@gmail.com"
_DISPLAY_NAME = "Test Beyo Vintage"

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 587
_SMTP_SECURITY = EmailSecurityEnum.STARTTLS

_IMAP_HOST = "imap.gmail.com"
_IMAP_PORT = 993
_IMAP_SECURITY = EmailSecurityEnum.SSL

_INBOX_FOLDER = "INBOX"


async def seed_email_connection(
    session: AsyncSession,
    workspace_result: dict[str, str],
    worker_name_to_user_id: dict[str, str],
) -> dict | None:
    if not _APP_PASSWORD:
        return None

    workspace_id = workspace_result["workspace_id"]
    owner_user_id = worker_name_to_user_id.get(_OWNER_WORKER_NAME)
    if owner_user_id is None:
        return None

    existing = await session.scalar(
        select(EmailConnection).where(
            EmailConnection.workspace_id == workspace_id,
            EmailConnection.owner_user_id == owner_user_id,
            EmailConnection.email_address == _EMAIL_ADDRESS,
            EmailConnection.deleted_at.is_(None),
        )
    )
    if existing is not None:
        return {"email_connection_id": existing.client_id, "seeded": False}

    connection = EmailConnection(
        workspace_id=workspace_id,
        owner_user_id=owner_user_id,
        email_address=_EMAIL_ADDRESS,
        display_name=_DISPLAY_NAME,
        provider_type=EmailProviderTypeEnum.SMTP_IMAP.value,
        status=EmailConnectionStatusEnum.ACTIVE.value,
        smtp_host=_SMTP_HOST,
        smtp_port=_SMTP_PORT,
        smtp_security=_SMTP_SECURITY.value,
        smtp_username=_EMAIL_ADDRESS,
        smtp_password_encrypted=encrypt_field(_APP_PASSWORD),
        imap_host=_IMAP_HOST,
        imap_port=_IMAP_PORT,
        imap_security=_IMAP_SECURITY.value,
        imap_username=_EMAIL_ADDRESS,
        imap_password_encrypted=encrypt_field(_APP_PASSWORD),
        inbox_folder=_INBOX_FOLDER,
    )
    session.add(connection)
    await session.flush()

    session.add(
        EmailSyncState(
            connection_id=connection.client_id,
            folder=_INBOX_FOLDER,
            last_seen_uid=0,
        )
    )
    await session.flush()

    return {"email_connection_id": connection.client_id, "seeded": True}
