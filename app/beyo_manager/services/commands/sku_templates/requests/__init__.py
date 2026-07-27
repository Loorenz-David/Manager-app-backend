from pydantic import BaseModel, ConfigDict, Field, ValidationError as PydanticValidationError, field_validator

from beyo_manager.domain.tasks.enums import TaskTypeEnum
from beyo_manager.errors.validation import ValidationError


class SkuTemplateCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: TaskTypeEnum
    prefix: str
    separator: str = "-"
    pad_width: int = Field(default=0, ge=0)
    initial_scalar: int = Field(default=0, ge=0)

    @field_validator("prefix", mode="before")
    @classmethod
    def normalize_prefix(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("prefix must not be blank.")
        if len(value) > 32:
            raise ValueError("prefix must be at most 32 characters.")
        return value

    @field_validator("separator", mode="before")
    @classmethod
    def normalize_separator(cls, value: str) -> str:
        value = value.strip()
        if len(value) > 8:
            raise ValueError("separator must be at most 8 characters.")
        return value


class SkuTemplateUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str
    prefix: str | None = None
    separator: str | None = None
    pad_width: int | None = Field(default=None, ge=0)
    last_scalar: int | None = Field(default=None, ge=0)

    @field_validator("client_id", mode="before")
    @classmethod
    def client_id_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("client_id must not be blank.")
        return value

    @field_validator("prefix", mode="before")
    @classmethod
    def normalize_update_prefix(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip().upper()
        if not value:
            raise ValueError("prefix must not be blank.")
        if len(value) > 32:
            raise ValueError("prefix must be at most 32 characters.")
        return value

    @field_validator("separator", mode="before")
    @classmethod
    def normalize_update_separator(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if len(value) > 8:
            raise ValueError("separator must be at most 8 characters.")
        return value


class SkuTemplateTaskTypeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: TaskTypeEnum


def _convert_parse_error(exc: PydanticValidationError) -> ValidationError:
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"])
    return ValidationError(f"{field}: {first_error['msg']}")


def parse_create_sku_template_request(data: dict) -> SkuTemplateCreateRequest:
    try:
        return SkuTemplateCreateRequest.model_validate(data)
    except PydanticValidationError as exc:
        raise _convert_parse_error(exc) from exc


def parse_update_sku_template_request(data: dict) -> SkuTemplateUpdateRequest:
    try:
        return SkuTemplateUpdateRequest.model_validate(data)
    except PydanticValidationError as exc:
        raise _convert_parse_error(exc) from exc


def parse_sku_template_task_type(data: dict) -> TaskTypeEnum:
    try:
        return SkuTemplateTaskTypeRequest.model_validate(data).task_type
    except PydanticValidationError as exc:
        raise _convert_parse_error(exc) from exc
