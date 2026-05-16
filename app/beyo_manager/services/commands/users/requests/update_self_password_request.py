from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.errors.validation import ValidationError


class UpdateSelfPasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password", mode="before")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("new_password must be at least 8 characters.")
        return v


def parse_update_self_password_request(data: dict) -> UpdateSelfPasswordRequest:
    try:
        return UpdateSelfPasswordRequest.model_validate(data)
    except PydanticValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(loc) for loc in first["loc"])
        raise ValidationError(f"{field}: {first['msg']}") from exc
