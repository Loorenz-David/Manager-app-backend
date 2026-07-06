from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class SendCustomerCoordinationReplyRequest(BaseModel):
    task_id: str
    thread_client_id: str = Field(..., min_length=1)
    connection_client_id: str | None = None
    subject: str | None = Field(default=None, min_length=1, max_length=255)
    text_body: str | None = None
    html_body: str | None = None

    @model_validator(mode="after")
    def require_at_least_one_body(self) -> "SendCustomerCoordinationReplyRequest":
        if self.text_body is None and self.html_body is None:
            raise ValueError("text_body or html_body is required")
        return self
