# CANONICAL REFERENCE — copy this file for every new request parser.
#
# Rules (enforced by contract 06_commands):
#   1. @field_validator handles blank checks and normalization — raises ValueError only.
#   2. parse_<name>_request calls model_validate directly — no intermediate classmethod.
#   3. The parse function is the ONLY place PydanticValidationError → ValidationError.
#   4. Never add a validate_fields classmethod — that creates a second entry point.
from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.errors.validation import ValidationError


class RecordCreateRequest(BaseModel):
    name: str
    category_id: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank.")
        return v

    @field_validator("category_id")
    @classmethod
    def category_id_must_not_be_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("category_id cannot be blank if provided.")
        return v


def parse_create_record_request(data: dict) -> RecordCreateRequest:
    try:
        return RecordCreateRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
