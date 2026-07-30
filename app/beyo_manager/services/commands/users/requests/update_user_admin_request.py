from decimal import Decimal

from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.errors.validation import ValidationError


CLOCK_IN_CODE_MIN_LENGTH = 4
CLOCK_IN_CODE_MAX_LENGTH = 16


class UpdateUserAdminRequest(BaseModel):
    user_client_id: str
    email: str | None = None
    phone_number: str | None = None
    profile_picture: str | None = None
    salary_per_hour_before_tax: Decimal | None = None
    salary_per_hour_after_tax: Decimal | None = None
    clock_in_code: str | None = None

    @field_validator("clock_in_code")
    @classmethod
    def validate_clock_in_code(cls, value: str | None) -> str | None:
        # Explicit null clears the code; any supplied value must be a usable one
        # after trimming (an empty string is a validation error, not a clear).
        if value is None:
            return None
        value = value.strip()
        if not (CLOCK_IN_CODE_MIN_LENGTH <= len(value) <= CLOCK_IN_CODE_MAX_LENGTH):
            raise ValueError(
                f"clock_in_code must be {CLOCK_IN_CODE_MIN_LENGTH}-"
                f"{CLOCK_IN_CODE_MAX_LENGTH} characters."
            )
        return value


def parse_update_user_admin_request(data: dict) -> UpdateUserAdminRequest:
    try:
        return UpdateUserAdminRequest.model_validate(data)
    except PydanticValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(loc) for loc in first["loc"])
        raise ValidationError(f"{field}: {first['msg']}") from exc
