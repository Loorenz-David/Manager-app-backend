from pydantic import BaseModel, field_validator


class SendEmailRequest(BaseModel):
    connection_client_id: str | None = None
    thread_client_id: str | None = None
    to_addresses: list[str]
    cc_addresses: list[str] = []
    bcc_addresses: list[str] = []
    subject: str
    text_body: str | None = None
    html_body: str | None = None
    entity_type: str | None = None
    entity_client_id: str | None = None
    major_entity_type: str | None = None
    major_entity_client_id: str | None = None
    topic: str | None = None

    @field_validator("to_addresses")
    @classmethod
    def validate_recipients(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("to_addresses must contain at least one recipient.")
        return value
