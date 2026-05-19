from pydantic import BaseModel, ValidationError as PydanticValidationError

from beyo_manager.errors.validation import ValidationError


class CreateCaseRequest(BaseModel):
    client_id: str | None = None
    case_type_id: str | None = None
    type_label: str | None = None


class CreateConversationRequest(BaseModel):
    client_id: str | None = None
    case_client_id: str


class SendMessageRequest(BaseModel):
    client_id: str | None = None
    conversation_client_id: str
    content: list
    plain_text: str = ""


def _raise_validation_error(exc: PydanticValidationError) -> None:
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"])
    raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_create_case_request(data: dict) -> CreateCaseRequest:
    try:
        return CreateCaseRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_create_conversation_request(data: dict) -> CreateConversationRequest:
    try:
        return CreateConversationRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_send_message_request(data: dict) -> SendMessageRequest:
    try:
        return SendMessageRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)
