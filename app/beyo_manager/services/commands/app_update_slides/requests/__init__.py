from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.domain.app_update_presentations.enums import (
    SlideLayoutEnum,
    SlidePlaybackModeEnum,
)
from beyo_manager.errors.validation import ValidationError


def _raise_validation_error(exc: PydanticValidationError) -> None:
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"])
    raise ValidationError(f"{field}: {first_error['msg']}") from exc


class CreateSlideRequest(BaseModel):
    presentation_id: str
    title: str | None = None
    description: str | None = None
    layout_type: SlideLayoutEnum | None = None
    action_label: str | None = None
    action_route: str | None = None
    playback_mode: SlidePlaybackModeEnum | None = None
    duration_ms: int | None = None
    composition_schema_version: int | None = None
    background_color: str | None = None


class UpdateSlideRequest(BaseModel):
    presentation_id: str
    slide_id: str
    title: str | None = None
    description: str | None = None
    layout_type: SlideLayoutEnum | None = None
    action_label: str | None = None
    action_route: str | None = None
    playback_mode: SlidePlaybackModeEnum | None = None
    duration_ms: int | None = None
    composition_schema_version: int | None = None
    background_color: str | None = None


class DeleteSlideRequest(BaseModel):
    presentation_id: str
    slide_id: str


class ReorderSlidesRequest(BaseModel):
    presentation_id: str
    ordered_slide_ids: list[str]

    @field_validator("ordered_slide_ids")
    @classmethod
    def not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("ordered_slide_ids must not be empty.")
        return v


def parse_create_slide_request(data: dict) -> CreateSlideRequest:
    try:
        return CreateSlideRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_update_slide_request(data: dict) -> UpdateSlideRequest:
    try:
        return UpdateSlideRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_delete_slide_request(data: dict) -> DeleteSlideRequest:
    try:
        return DeleteSlideRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_reorder_slides_request(data: dict) -> ReorderSlidesRequest:
    try:
        return ReorderSlidesRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)
