from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemUpholsterySourceEnum
from beyo_manager.domain.tasks.enums import (
	TaskFulfillmentMethodEnum,
	TaskItemLocationEnum,
	TaskItemRoleEnum,
	TaskNoteTypeEnum,
	TaskPriorityEnum,
	TaskReturnMethodEnum,
	TaskReturnSourceEnum,
	TaskStateEnum,
	TaskTypeEnum,
)
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.tasks.requests.send_customer_coordination_email_batch_request import (
	SendCustomerCoordinationEmailBatchRequest,
)
from beyo_manager.services.commands.tasks.requests.send_customer_coordination_reply_request import (
	SendCustomerCoordinationReplyRequest,
)


class FindOrCreateItemInput(BaseModel):
	client_id: str | None = None
	article_number: str | None = None
	sku: str | None = None
	item_category_id: str | None = None
	quantity: int = 1
	designer: str | None = None
	height_in_cm: int | None = None
	width_in_cm: int | None = None
	depth_in_cm: int | None = None
	item_value_minor: int | None = None
	item_cost_minor: int | None = None
	item_currency: ItemCurrencyEnum | None = None
	item_position: str | None = None
	item_zone: str | None = None
	external_id: str | None = None
	external_url: str | None = None
	external_source: str | None = None
	external_order_id: str | None = None


class ItemIssueInput(BaseModel):
	issue_type_id: str | None = None
	step_id: str
	worker_id: str
	working_section_id: str
	item_category_id: str
	issue_type_snapshot: str
	placement_of_issue_snapshot: str | None = None
	intensity: int

	@field_validator("intensity")
	@classmethod
	def intensity_must_be_positive(cls, v: int) -> int:
		if v < 1:
			raise ValueError("intensity must be >= 1.")
		return v


class ItemUpholsteryInput(BaseModel):
	client_id: str | None = None
	upholstery_id: str | None = None
	source: ItemUpholsterySourceEnum
	name: str | None = None
	code: str | None = None
	amount_meters: Decimal | None = None
	time_to_fix_in_seconds: int | None = None


class TaskNoteInput(BaseModel):
	client_id: str | None = None
	note_type: TaskNoteTypeEnum
	content: list
	plain_text: str = ""
	users_read_list: list[str] | None = None


class TaskStepInput(BaseModel):
	client_id: str | None = None
	working_section_id: str
	worker_id: str | None = None
	sequence_order: int | None = None
	ready_by_at: datetime | None = None


class CreateTaskRequest(BaseModel):
	client_id: str | None = None
	task_type: TaskTypeEnum
	state: TaskStateEnum | None = None
	title: str | None = None
	summary: str | None = None
	priority: TaskPriorityEnum = TaskPriorityEnum.NORMAL
	ready_by_at: datetime | None = None
	scheduled_start_at: datetime | None = None
	scheduled_end_at: datetime | None = None
	return_source: TaskReturnSourceEnum | None = None
	item_location: TaskItemLocationEnum | None = None
	return_method: TaskReturnMethodEnum | None = None
	fulfillment_method: TaskFulfillmentMethodEnum | None = None
	assortment: str | None = None
	additional_details: dict | None = None
	customer_id: str | None = None
	customer_display_name: str | None = None
	primary_phone_number: str | None = None
	secondary_phone_number: str | None = None
	primary_email: str | None = None
	secondary_email: str | None = None
	customer_address: dict | None = None
	item: FindOrCreateItemInput | None = None
	item_issues: list[ItemIssueInput] | None = None
	item_upholstery: ItemUpholsteryInput | None = None
	notes: list[TaskNoteInput] | None = None
	steps: list[TaskStepInput] | None = None


class UpdateTaskRequest(BaseModel):
	client_id: str
	task_type: TaskTypeEnum | None = None
	title: str | None = None
	summary: str | None = None
	priority: TaskPriorityEnum | None = None
	ready_by_at: datetime | None = None
	scheduled_start_at: datetime | None = None
	scheduled_end_at: datetime | None = None
	return_source: TaskReturnSourceEnum | None = None
	item_location: TaskItemLocationEnum | None = None
	return_method: TaskReturnMethodEnum | None = None
	fulfillment_method: TaskFulfillmentMethodEnum | None = None
	assortment: str | None = None
	additional_details: dict | None = None


class UpdateTaskReadyByAtRequest(BaseModel):
	client_id: str
	ready_by_at: datetime | None = None


class UpdateTaskScheduleRequest(BaseModel):
	client_id: str
	scheduled_start_at: datetime | None = None
	scheduled_end_at: datetime | None = None


class TerminalTaskRequest(BaseModel):
	client_id: str


class AddItemToTaskRequest(BaseModel):
	task_id: str
	item_id: str
	role: TaskItemRoleEnum


class RemoveItemFromTaskRequest(BaseModel):
	task_id: str
	item_id: str


class CreateTaskNoteRequest(BaseModel):
	client_id: str | None = None
	task_id: str
	note_type: TaskNoteTypeEnum
	content: list
	plain_text: str = ""
	users_read_list: list[str] | None = None


class CreateBatchTaskNotesRequest(BaseModel):
	task_id: str
	notes: list[TaskNoteInput]


class UpdateTaskNoteRequest(BaseModel):
	client_id: str
	note_type: TaskNoteTypeEnum | None = None
	content: list | None = None
	plain_text: str | None = None


class MarkNoteReadByRequest(BaseModel):
	client_id: str
	task_id: str
	user_ids: list[str]


class DeleteTaskNoteRequest(BaseModel):
	client_id: str


def _raise_validation_error(exc: PydanticValidationError) -> None:
	first_error = exc.errors()[0]
	field = ".".join(str(loc) for loc in first_error["loc"])
	raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_create_task_request(data: dict) -> CreateTaskRequest:
	try:
		return CreateTaskRequest.model_validate(data)
	except PydanticValidationError as exc:
		_raise_validation_error(exc)


def parse_update_task_request(data: dict) -> UpdateTaskRequest:
	try:
		return UpdateTaskRequest.model_validate(data)
	except PydanticValidationError as exc:
		_raise_validation_error(exc)


def parse_update_task_ready_by_at_request(data: dict) -> UpdateTaskReadyByAtRequest:
	try:
		return UpdateTaskReadyByAtRequest.model_validate(data)
	except PydanticValidationError as exc:
		_raise_validation_error(exc)


def parse_update_task_schedule_request(data: dict) -> UpdateTaskScheduleRequest:
	try:
		return UpdateTaskScheduleRequest.model_validate(data)
	except PydanticValidationError as exc:
		_raise_validation_error(exc)


def parse_send_customer_coordination_email_batch_request(
	data: dict,
) -> SendCustomerCoordinationEmailBatchRequest:
	try:
		return SendCustomerCoordinationEmailBatchRequest.model_validate(data)
	except PydanticValidationError as exc:
		_raise_validation_error(exc)


def parse_send_customer_coordination_reply_request(
	data: dict,
) -> SendCustomerCoordinationReplyRequest:
	try:
		return SendCustomerCoordinationReplyRequest.model_validate(data)
	except PydanticValidationError as exc:
		_raise_validation_error(exc)


def parse_terminal_task_request(data: dict) -> TerminalTaskRequest:
	try:
		return TerminalTaskRequest.model_validate(data)
	except PydanticValidationError as exc:
		_raise_validation_error(exc)


def parse_add_item_to_task_request(data: dict) -> AddItemToTaskRequest:
	try:
		return AddItemToTaskRequest.model_validate(data)
	except PydanticValidationError as exc:
		_raise_validation_error(exc)


def parse_remove_item_from_task_request(data: dict) -> RemoveItemFromTaskRequest:
	try:
		return RemoveItemFromTaskRequest.model_validate(data)
	except PydanticValidationError as exc:
		_raise_validation_error(exc)


def parse_create_task_note_request(data: dict) -> CreateTaskNoteRequest:
	try:
		return CreateTaskNoteRequest.model_validate(data)
	except PydanticValidationError as exc:
		_raise_validation_error(exc)


def parse_create_batch_task_notes_request(data: dict) -> CreateBatchTaskNotesRequest:
	try:
		return CreateBatchTaskNotesRequest.model_validate(data)
	except PydanticValidationError as exc:
		_raise_validation_error(exc)


def parse_update_task_note_request(data: dict) -> UpdateTaskNoteRequest:
	try:
		return UpdateTaskNoteRequest.model_validate(data)
	except PydanticValidationError as exc:
		_raise_validation_error(exc)


def parse_delete_task_note_request(data: dict) -> DeleteTaskNoteRequest:
	try:
		return DeleteTaskNoteRequest.model_validate(data)
	except PydanticValidationError as exc:
		_raise_validation_error(exc)


def parse_mark_note_read_by_request(data: dict) -> MarkNoteReadByRequest:
	try:
		return MarkNoteReadByRequest.model_validate(data)
	except PydanticValidationError as exc:
		_raise_validation_error(exc)
