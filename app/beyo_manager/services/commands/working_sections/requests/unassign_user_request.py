from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.errors.validation import ValidationError


class UnassignUserRequest(BaseModel):
    user_id: str
    working_section_ids: list[str]

    @field_validator("user_id", mode="before")
    @classmethod
    def user_id_must_not_be_blank(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("user_id must not be blank.")
        return value

    @field_validator("working_section_ids", mode="before")
    @classmethod
    def section_ids_must_not_be_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("working_section_ids must contain at least one section ID.")
        return v


def parse_unassign_user_request(data: dict) -> UnassignUserRequest:
    try:
        return UnassignUserRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
