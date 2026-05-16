from pydantic import BaseModel, ValidationError as PydanticValidationError

from beyo_manager.errors.validation import ValidationError


class UpdateSelfProfileRequest(BaseModel):
    email: str | None = None
    phone_number: str | None = None
    profile_picture: str | None = None


def parse_update_self_profile_request(data: dict) -> UpdateSelfProfileRequest:
    try:
        return UpdateSelfProfileRequest.model_validate(data)
    except PydanticValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(loc) for loc in first["loc"])
        raise ValidationError(f"{field}: {first['msg']}") from exc
