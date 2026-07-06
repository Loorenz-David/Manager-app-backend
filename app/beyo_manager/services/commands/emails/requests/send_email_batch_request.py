from pydantic import BaseModel, Field, field_validator


class BatchEmailTarget(BaseModel):
    to_addresses: list[str]
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


class SendEmailBatchRequest(BaseModel):
    connection_client_id: str | None = None
    targets: list[BatchEmailTarget] = Field(..., min_length=1, max_length=200)
    cc_addresses: list[str] = Field(default_factory=list)
    bcc_addresses: list[str] = Field(default_factory=list)
    subject: str
    text_body: str | None = None
    html_body: str | None = None
