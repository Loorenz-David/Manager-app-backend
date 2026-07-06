from pydantic import (
    BaseModel,
    ValidationError as PydanticValidationError,
    field_validator,
    model_validator,
)

from beyo_manager.domain.emails.enums import EmailTemplateTopicEnum, EmailTemplateTypeEnum
from beyo_manager.errors.validation import ValidationError


class UpdateEmailTemplateRequest(BaseModel):
    template_client_id: str
    name: str | None = None
    subject: str | None = None
    content: str | None = None
    topic: EmailTemplateTopicEnum | None = None
    template_type: EmailTemplateTypeEnum | None = None

    @field_validator("template_client_id", mode="before")
    @classmethod
    def normalize_template_client_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("template_client_id must not be blank.")
        return normalized

    @field_validator("name", "subject", "content", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank.")
        return normalized

    @model_validator(mode="after")
    def require_at_least_one_mutation(self):
        if all(
            value is None
            for value in (
                self.name,
                self.subject,
                self.content,
                self.topic,
                self.template_type,
            )
        ):
            raise ValueError("At least one field must be provided for update.")
        return self


def parse_update_email_template_request(data: dict) -> UpdateEmailTemplateRequest:
    try:
        return UpdateEmailTemplateRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
