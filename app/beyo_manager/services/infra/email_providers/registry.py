from beyo_manager.domain.emails.enums import EmailProviderTypeEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.services.infra.crypto.field_encryption import decrypt_field
from beyo_manager.services.infra.email_providers.base import EmailProviderProtocol
from beyo_manager.services.infra.email_providers.smtp_imap.adapter import SmtpImapEmailProvider


def get_email_provider(connection: EmailConnection) -> EmailProviderProtocol:
    if connection.provider_type == EmailProviderTypeEnum.SMTP_IMAP.value:
        return SmtpImapEmailProvider(
            smtp_host=connection.smtp_host,
            smtp_port=connection.smtp_port,
            smtp_security=connection.smtp_security,
            smtp_username=connection.smtp_username,
            smtp_password=decrypt_field(connection.smtp_password_encrypted),
            imap_host=connection.imap_host,
            imap_port=connection.imap_port,
            imap_security=connection.imap_security,
            imap_username=connection.imap_username,
            imap_password=decrypt_field(connection.imap_password_encrypted),
        )
    allowed = ", ".join(item.value for item in EmailProviderTypeEnum)
    raise ValidationError(
        f"Unsupported email provider type '{connection.provider_type}'. Allowed: {allowed}"
    )
