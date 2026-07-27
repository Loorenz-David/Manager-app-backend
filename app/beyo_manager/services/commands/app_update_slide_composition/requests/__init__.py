from pydantic import BaseModel, ValidationError as PydanticValidationError

from beyo_manager.domain.app_update_presentations.enums import (
    SlideElementTypeEnum,
    SlidePlaybackModeEnum,
)
from beyo_manager.errors.validation import ValidationError


def _raise_validation_error(exc: PydanticValidationError) -> None:
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"])
    raise ValidationError(f"{field}: {first_error['msg']}") from exc


class CompositionElementInput(BaseModel):
    element_type: SlideElementTypeEnum
    layer_index: int = 0
    start_ms: int = 0
    end_ms: int | None = None
    media_id: str | None = None
    text_content: str | None = None
    # Raw config dicts — validated against the schemas in the command so domain
    # ValidationErrors surface with clear messages.
    layout: dict | None = None
    style: dict | None = None
    enter_animation: dict | None = None
    exit_animation: dict | None = None


class SlideCompositionReplaceRequest(BaseModel):
    presentation_id: str
    slide_id: str
    playback_mode: SlidePlaybackModeEnum
    duration_ms: int | None = None
    composition_schema_version: int | None = None
    background_color: str | None = None
    elements: list[CompositionElementInput] = []


def parse_slide_composition_replace_request(data: dict) -> SlideCompositionReplaceRequest:
    try:
        return SlideCompositionReplaceRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)
