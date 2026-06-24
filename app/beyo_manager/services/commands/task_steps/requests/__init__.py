from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.domain.task_steps.enums import StepEventReasonEnum, TaskStepStateEnum
from beyo_manager.errors.validation import ValidationError


class StepInputItem(BaseModel):
    client_id: str | None = None
    working_section_id: str
    sequence_order: int | None = None
    worker_id: str | None = None


class AddTaskStepsRequest(BaseModel):
    task_id: str
    steps: list[StepInputItem]


class AssignWorkerToStepRequest(BaseModel):
    step_id: str
    task_id: str
    worker_id: str


def parse_add_task_steps_request(data: dict) -> AddTaskStepsRequest:
    try:
        return AddTaskStepsRequest(**data)
    except PydanticValidationError as e:
        raise ValidationError(str(e)) from e


def parse_assign_worker_to_step_request(data: dict) -> AssignWorkerToStepRequest:
    try:
        return AssignWorkerToStepRequest(**data)
    except PydanticValidationError as e:
        raise ValidationError(str(e)) from e


class AddStepDependencyRequest(BaseModel):
    task_id: str
    step_id: str
    prerequisite_step_id: str


class RemoveStepDependencyRequest(BaseModel):
    task_id: str
    step_id: str
    dependency_id: str


class RemoveTaskStepRequest(BaseModel):
    task_id: str
    step_id: str


class RemoveTaskStepsRequest(BaseModel):
    task_id: str
    step_ids: list[str]

    @field_validator("step_ids")
    @classmethod
    def validate_step_ids(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("step_ids must not be empty.")
        return value


def parse_add_step_dependency_request(data: dict) -> AddStepDependencyRequest:
    try:
        return AddStepDependencyRequest(**data)
    except PydanticValidationError as e:
        raise ValidationError(str(e)) from e


def parse_remove_step_dependency_request(data: dict) -> RemoveStepDependencyRequest:
    try:
        return RemoveStepDependencyRequest(**data)
    except PydanticValidationError as e:
        raise ValidationError(str(e)) from e


def parse_remove_task_step_request(data: dict) -> RemoveTaskStepRequest:
    try:
        return RemoveTaskStepRequest(**data)
    except PydanticValidationError as e:
        raise ValidationError(str(e)) from e


def parse_remove_task_steps_request(data: dict) -> RemoveTaskStepsRequest:
    try:
        return RemoveTaskStepsRequest.model_validate(data)
    except PydanticValidationError as e:
        raise ValidationError(str(e)) from e


class TransitionStepStateRequest(BaseModel):
    step_id: str
    task_id: str
    new_state: TaskStepStateEnum
    credited_user_id: str | None = None
    reason: StepEventReasonEnum | None = None
    description: str | None = None
    mark_closing_record_inaccurate: bool = False


def parse_transition_step_state_request(data: dict) -> TransitionStepStateRequest:
    try:
        return TransitionStepStateRequest(**data)
    except PydanticValidationError as e:
        raise ValidationError(str(e)) from e


class MarkStepTimeInaccurateRequest(BaseModel):
    task_id: str
    step_id: str
    record_id: str


def parse_mark_step_time_inaccurate_request(data: dict) -> MarkStepTimeInaccurateRequest:
    try:
        return MarkStepTimeInaccurateRequest(**data)
    except PydanticValidationError as e:
        raise ValidationError(str(e)) from e


_MAX_BATCH_TRANSITION_ITEMS = 100


class BatchTransitionItem(BaseModel):
    task_id: str
    step_id: str
    mark_closing_record_inaccurate: bool = False


class BatchTransitionStepStateRequest(BaseModel):
    items: list[BatchTransitionItem]
    new_state: TaskStepStateEnum
    reason: StepEventReasonEnum | None = None
    description: str | None = None

    @field_validator("items")
    @classmethod
    def validate_items(cls, value: list[BatchTransitionItem]) -> list[BatchTransitionItem]:
        if not value:
            raise ValueError("items must not be empty.")
        if len(value) > _MAX_BATCH_TRANSITION_ITEMS:
            raise ValueError(f"items must not exceed {_MAX_BATCH_TRANSITION_ITEMS} entries.")
        step_ids = [item.step_id for item in value]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("Duplicate step_id values are not allowed.")
        return value


def parse_batch_transition_step_state_request(data: dict) -> BatchTransitionStepStateRequest:
    try:
        return BatchTransitionStepStateRequest.model_validate(data)
    except PydanticValidationError as e:
        raise ValidationError(str(e)) from e
