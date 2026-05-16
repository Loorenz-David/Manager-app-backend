from decimal import Decimal

from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator, model_validator

from beyo_manager.errors.validation import ValidationError


class RegisterUserRequest(BaseModel):
    username: str
    email: str
    password: str
    phone_number: str | None = None
    role_id: str | None = None
    role_name: str | None = None
    working_section_ids: list[str] = []
    salary_per_hour_before_tax: Decimal | None = None
    salary_per_hour_after_tax: Decimal | None = None

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("username must not be blank.")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("email must not be blank.")
        return v

    @field_validator("password", mode="before")
    @classmethod
    def password_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("password must not be blank.")
        return v

    @field_validator("role_id", mode="before")
    @classmethod
    def role_id_must_not_be_blank(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("role_id must not be blank.")
        return v

    @field_validator("role_name", mode="before")
    @classmethod
    def role_name_must_not_be_blank(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().lower()
        if not v:
            raise ValueError("role_name must not be blank.")
        return v

    @model_validator(mode="after")
    def require_role_identifier(self):
        if self.role_id is None and self.role_name is None:
            raise ValueError("Either role_id or role_name must be provided.")
        return self

    @field_validator("salary_per_hour_before_tax", "salary_per_hour_after_tax", mode="before")
    @classmethod
    def salary_must_be_non_negative(cls, v):
        if v is not None and Decimal(str(v)) < 0:
            raise ValueError("Salary values must be non-negative.")
        return v


def parse_register_user_request(data: dict) -> RegisterUserRequest:
    try:
        return RegisterUserRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
