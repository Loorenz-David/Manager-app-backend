from pydantic import BaseModel, field_validator

from beyo_manager.domain.emails.enums import EmailProviderTypeEnum, EmailSecurityEnum


class CreateEmailConnectionRequest(BaseModel):
    email_address: str
    display_name: str | None = None
    provider_type: EmailProviderTypeEnum = EmailProviderTypeEnum.SMTP_IMAP
    smtp_host: str
    smtp_port: int
    smtp_security: EmailSecurityEnum
    smtp_username: str
    smtp_password: str
    imap_host: str
    imap_port: int
    imap_security: EmailSecurityEnum
    imap_username: str
    imap_password: str
    inbox_folder: str = "INBOX"

    @field_validator("smtp_port", "imap_port")
    @classmethod
    def validate_port(cls, value: int) -> int:
        if not (1 <= value <= 65535):
            raise ValueError("Port must be between 1 and 65535.")
        return value

    @field_validator("email_address")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value:
            raise ValueError("email_address must be a valid email.")
        return value
