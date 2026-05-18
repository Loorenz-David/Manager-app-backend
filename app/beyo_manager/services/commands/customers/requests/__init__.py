"""Request models for customer commands."""

from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator, model_validator

from beyo_manager.domain.customers.enums import CustomerStatusEnum, CustomerTypeEnum
from beyo_manager.errors.validation import ValidationError


def _normalize_email(email: str | None) -> str | None:
    if email is None:
        return None
    normalized = email.strip().lower()
    return normalized if normalized else None


def _normalize_phone(phone: str | None) -> str | None:
    if phone is None:
        return None
    normalized = "".join(c for c in phone if c.isdigit() or c == "+").strip()
    return normalized if normalized else None


class CreateCustomerRequest(BaseModel):
    display_name: str
    customer_type: CustomerTypeEnum = CustomerTypeEnum.UNKNOWN
    primary_email: str | None = None
    primary_phone_number: str | None = None
    address: dict | None = None

    @field_validator("display_name", mode="before")
    @classmethod
    def strip_display_name(cls, v) -> str:
        value = str(v).strip()
        if not value:
            raise ValueError("display_name must not be blank.")
        return value

    @field_validator("primary_email", mode="before")
    @classmethod
    def normalize_email(cls, v) -> str | None:
        return _normalize_email(v)

    @field_validator("primary_phone_number", mode="before")
    @classmethod
    def normalize_phone(cls, v) -> str | None:
        return _normalize_phone(v)

    @model_validator(mode="after")
    def require_at_least_one_contact(self):
        if self.primary_email is None and self.primary_phone_number is None:
            raise ValueError("At least one of primary_email or primary_phone_number must be provided.")
        return self

    @property
    def primary_email_normalized(self) -> str | None:
        return self.primary_email

    @property
    def primary_phone_number_normalized(self) -> str | None:
        return self.primary_phone_number


class UpdateCustomerRequest(BaseModel):
    client_id: str
    display_name: str | None = None
    customer_type: CustomerTypeEnum | None = None
    status: CustomerStatusEnum | None = None
    primary_email: str | None = None
    primary_phone_number: str | None = None
    address: dict | None = None

    @field_validator("display_name", mode="before")
    @classmethod
    def strip_display_name(cls, v) -> str | None:
        if v is None:
            return None
        value = str(v).strip()
        return value if value else None

    @field_validator("primary_email", mode="before")
    @classmethod
    def normalize_email(cls, v) -> str | None:
        return _normalize_email(v)

    @field_validator("primary_phone_number", mode="before")
    @classmethod
    def normalize_phone(cls, v) -> str | None:
        return _normalize_phone(v)


class DeleteCustomerRequest(BaseModel):
    client_id: str


class FindOrCreateCustomerRequest(BaseModel):
    display_name: str
    primary_email: str | None = None
    primary_phone_number: str | None = None
    customer_type: CustomerTypeEnum = CustomerTypeEnum.UNKNOWN
    address: dict | None = None

    @field_validator("display_name", mode="before")
    @classmethod
    def strip_display_name(cls, v) -> str:
        value = str(v).strip()
        if not value:
            raise ValueError("display_name must not be blank.")
        return value

    @field_validator("primary_email", mode="before")
    @classmethod
    def normalize_email(cls, v) -> str | None:
        return _normalize_email(v)

    @field_validator("primary_phone_number", mode="before")
    @classmethod
    def normalize_phone(cls, v) -> str | None:
        return _normalize_phone(v)


def _raise_validation_error(exc: PydanticValidationError) -> None:
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"])
    raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_create_customer_request(data: dict) -> CreateCustomerRequest:
    try:
        return CreateCustomerRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_update_customer_request(data: dict) -> UpdateCustomerRequest:
    try:
        return UpdateCustomerRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_delete_customer_request(data: dict) -> DeleteCustomerRequest:
    try:
        return DeleteCustomerRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_find_or_create_customer_request(data: dict) -> FindOrCreateCustomerRequest:
    try:
        return FindOrCreateCustomerRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)
