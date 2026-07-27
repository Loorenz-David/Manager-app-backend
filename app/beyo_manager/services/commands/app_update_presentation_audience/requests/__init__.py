from pydantic import BaseModel, ValidationError as PydanticValidationError

from beyo_manager.domain.app_update_presentations.enums import (
    AppKeyEnum,
    AudienceModeEnum,
)
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.errors.validation import ValidationError


def _raise_validation_error(exc: PydanticValidationError) -> None:
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"])
    raise ValidationError(f"{field}: {first_error['msg']}") from exc


class ReplaceAudienceRequest(BaseModel):
    presentation_id: str
    audience_mode: AudienceModeEnum
    app_keys: list[AppKeyEnum] = []
    role_keys: list[RoleNameEnum] = []
    workspace_ids: list[str] = []
    user_ids: list[str] = []


def parse_replace_audience_request(data: dict) -> ReplaceAudienceRequest:
    try:
        return ReplaceAudienceRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)
