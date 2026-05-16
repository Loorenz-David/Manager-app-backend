from decimal import Decimal

from pydantic import BaseModel, ValidationError as PydanticValidationError

from beyo_manager.errors.validation import ValidationError


class UpdateUserAdminRequest(BaseModel):
    user_client_id: str
    email: str | None = None
    phone_number: str | None = None
    profile_picture: str | None = None
    salary_per_hour_before_tax: Decimal | None = None
    salary_per_hour_after_tax: Decimal | None = None


def parse_update_user_admin_request(data: dict) -> UpdateUserAdminRequest:
    try:
        return UpdateUserAdminRequest.model_validate(data)
    except PydanticValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(loc) for loc in first["loc"])
        raise ValidationError(f"{field}: {first['msg']}") from exc
