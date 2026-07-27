from pydantic import BaseModel, ConfigDict

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.pause_reasons.validators import validate_pause_reason_fields
from beyo_manager.errors.validation import ValidationError


class PauseReasonCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    image_url: str | None = None
    pause_type: PauseTypeEnum
    description: str | None = None
    requires_description: bool = False


class PauseReasonUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str
    name: str | None = None
    image_url: str | None = None
    pause_type: PauseTypeEnum | None = None
    description: str | None = None
    requires_description: bool | None = None


class PauseReasonDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str


def _convert_parse_error(exc: Exception) -> ValidationError:
    if hasattr(exc, "errors"):
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        return ValidationError(f"{field}: {first_error['msg']}")
    return ValidationError(str(exc))


def parse_create_pause_reason_request(data: dict) -> PauseReasonCreateRequest:
    try:
        request = PauseReasonCreateRequest.model_validate(data)
        validate_pause_reason_fields(request.name, request.description)
        request.name = request.name.strip()
        return request
    except Exception as exc:
        if isinstance(exc, ValidationError):
            raise
        raise _convert_parse_error(exc) from exc


def parse_update_pause_reason_request(data: dict) -> PauseReasonUpdateRequest:
    try:
        request = PauseReasonUpdateRequest.model_validate(data)
        if request.name is not None:
            validate_pause_reason_fields(request.name, request.description)
            request.name = request.name.strip()
        elif request.description is not None and len(request.description) > 1024:
            raise ValueError("description must be at most 1024 characters.")
        return request
    except Exception as exc:
        if isinstance(exc, ValidationError):
            raise
        raise _convert_parse_error(exc) from exc


def parse_delete_pause_reason_request(data: dict) -> PauseReasonDeleteRequest:
    try:
        return PauseReasonDeleteRequest.model_validate(data)
    except Exception as exc:
        raise _convert_parse_error(exc) from exc
