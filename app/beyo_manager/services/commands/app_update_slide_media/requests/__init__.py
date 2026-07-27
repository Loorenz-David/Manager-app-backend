from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.domain.app_update_presentations.enums import SlideMediaTypeEnum
from beyo_manager.errors.validation import ValidationError


def _raise_validation_error(exc: PydanticValidationError) -> None:
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"])
    raise ValidationError(f"{field}: {first_error['msg']}") from exc


class GenerateMediaUploadUrlRequest(BaseModel):
    presentation_id: str
    slide_id: str
    media_type: SlideMediaTypeEnum
    content_type: str
    file_name: str = ""
    file_size_bytes: int | None = None


class AddSlideMediaRequest(BaseModel):
    presentation_id: str
    slide_id: str
    media_type: SlideMediaTypeEnum
    pending_upload_client_id: str | None = None
    storage_key: str | None = None
    poster_storage_key: str | None = None
    fallback_storage_key: str | None = None
    alt_text: str | None = None
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None
    is_looping: bool | None = None

    @field_validator("storage_key")
    @classmethod
    def key_not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("storage_key cannot be blank.")
        return v


class UpdateSlideMediaRequest(BaseModel):
    presentation_id: str
    slide_id: str
    media_id: str
    poster_storage_key: str | None = None
    fallback_storage_key: str | None = None
    alt_text: str | None = None
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None
    is_looping: bool | None = None


class DeleteSlideMediaRequest(BaseModel):
    presentation_id: str
    slide_id: str
    media_id: str


class ReorderSlideMediaRequest(BaseModel):
    presentation_id: str
    slide_id: str
    ordered_media_ids: list[str]

    @field_validator("ordered_media_ids")
    @classmethod
    def not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("ordered_media_ids must not be empty.")
        return v


def parse_generate_media_upload_url_request(data: dict) -> GenerateMediaUploadUrlRequest:
    try:
        return GenerateMediaUploadUrlRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_add_slide_media_request(data: dict) -> AddSlideMediaRequest:
    try:
        return AddSlideMediaRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_update_slide_media_request(data: dict) -> UpdateSlideMediaRequest:
    try:
        return UpdateSlideMediaRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_delete_slide_media_request(data: dict) -> DeleteSlideMediaRequest:
    try:
        return DeleteSlideMediaRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_reorder_slide_media_request(data: dict) -> ReorderSlideMediaRequest:
    try:
        return ReorderSlideMediaRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)
