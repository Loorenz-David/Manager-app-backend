from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.domain.emails.enums import EmailTemplateTopicEnum, EmailTemplateTypeEnum
from beyo_manager.errors.validation import ValidationError


class CreateEmailTemplateRequest(BaseModel):
    name: str
    subject: str
    content: str
    topic: EmailTemplateTopicEnum
    template_type: EmailTemplateTypeEnum

    @field_validator("name", "subject", "content", mode="before")
    @classmethod
    def require_non_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank.")
        return normalized


def parse_create_email_template_request(data: dict) -> CreateEmailTemplateRequest:
    try:
        return CreateEmailTemplateRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
