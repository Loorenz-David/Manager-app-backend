from datetime import datetime

from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.domain.app_update_presentations.enums import (
    AudienceModeEnum,
    PresentationCategoryEnum,
    PresentationTypeEnum,
)
from beyo_manager.errors.validation import ValidationError


def _raise_validation_error(exc: PydanticValidationError) -> None:
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"])
    raise ValidationError(f"{field}: {first_error['msg']}") from exc


class CreatePresentationRequest(BaseModel):
    client_id: str | None = None
    title: str
    summary: str | None = None
    presentation_type: PresentationTypeEnum | None = None
    category: PresentationCategoryEnum | None = None
    audience_mode: AudienceModeEnum | None = None
    display_priority: int | None = None
    is_dismissible: bool | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("title must not be blank.")
        return v.strip()


class UpdatePresentationRequest(BaseModel):
    client_id: str
    title: str | None = None
    summary: str | None = None
    presentation_type: PresentationTypeEnum | None = None
    category: PresentationCategoryEnum | None = None
    audience_mode: AudienceModeEnum | None = None
    display_priority: int | None = None
    is_dismissible: bool | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("title must not be blank.")
        return v.strip() if v is not None else v


class PresentationRefRequest(BaseModel):
    client_id: str


def parse_create_presentation_request(data: dict) -> CreatePresentationRequest:
    try:
        return CreatePresentationRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_update_presentation_request(data: dict) -> UpdatePresentationRequest:
    try:
        return UpdatePresentationRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_presentation_ref_request(data: dict) -> PresentationRefRequest:
    try:
        return PresentationRefRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)
