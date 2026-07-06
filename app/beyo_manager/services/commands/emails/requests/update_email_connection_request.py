from pydantic import BaseModel

from beyo_manager.domain.emails.enums import EmailSecurityEnum


class UpdateEmailConnectionRequest(BaseModel):
    connection_client_id: str
    display_name: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_security: EmailSecurityEnum | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    imap_host: str | None = None
    imap_port: int | None = None
    imap_security: EmailSecurityEnum | None = None
    imap_username: str | None = None
    imap_password: str | None = None
    inbox_folder: str | None = None
