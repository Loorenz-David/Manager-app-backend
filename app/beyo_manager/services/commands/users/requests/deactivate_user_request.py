from pydantic import BaseModel, ValidationError as PydanticValidationError

from beyo_manager.errors.validation import ValidationError


class DeactivateUserRequest(BaseModel):
    user_client_id: str


def parse_deactivate_user_request(data: dict) -> DeactivateUserRequest:
    try:
        return DeactivateUserRequest.model_validate(data)
    except PydanticValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(loc) for loc in first["loc"])
        raise ValidationError(f"{field}: {first['msg']}") from exc
