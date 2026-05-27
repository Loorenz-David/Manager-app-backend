from pydantic import BaseModel, ValidationError as PydanticValidationError

from beyo_manager.domain.task_steps.enums import StepEventReasonEnum, TaskStepStateEnum
from beyo_manager.errors.validation import ValidationError


class AddTaskStepRequest(BaseModel):
    client_id: str | None = None
    task_id: str
    working_section_id: str
    sequence_order: int | None = None
    worker_id: str | None = None


class AssignWorkerToStepRequest(BaseModel):
    step_id: str
    task_id: str
    worker_id: str


def parse_add_task_step_request(data: dict) -> AddTaskStepRequest:
    try:
        return AddTaskStepRequest(**data)
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


class TransitionStepStateRequest(BaseModel):
    step_id: str
    task_id: str
    new_state: TaskStepStateEnum
    credited_user_id: str | None = None
    reason: StepEventReasonEnum | None = None
    description: str | None = None


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
