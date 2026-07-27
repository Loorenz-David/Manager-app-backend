from pydantic import BaseModel, ValidationError as PydanticValidationError

from beyo_manager.errors.validation import ValidationError


def _raise_validation_error(exc: PydanticValidationError) -> None:
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"])
    raise ValidationError(f"{field}: {first_error['msg']}") from exc


class RecordPresentationViewRequest(BaseModel):
    presentation_id: str
    version: int
    action: str
    last_slide_index: int | None = None


def parse_record_presentation_view_request(data: dict) -> RecordPresentationViewRequest:
    try:
        return RecordPresentationViewRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)
