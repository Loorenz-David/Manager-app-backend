from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.errors.validation import ValidationError

_MAX_STEP_IDS = 200


class StepAcknowledgmentActionRequest(BaseModel):
    step_ids: list[str]

    @field_validator("step_ids")
    @classmethod
    def validate_step_ids(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("step_ids must not be empty.")
        if len(value) > _MAX_STEP_IDS:
            raise ValueError(f"step_ids must not exceed {_MAX_STEP_IDS} entries.")
        # De-duplicate while preserving determinism.
        return sorted(set(value))


def parse_step_acknowledgment_action_request(data: dict) -> StepAcknowledgmentActionRequest:
    try:
        return StepAcknowledgmentActionRequest.model_validate(data)
    except PydanticValidationError as e:
        raise ValidationError(str(e)) from e
