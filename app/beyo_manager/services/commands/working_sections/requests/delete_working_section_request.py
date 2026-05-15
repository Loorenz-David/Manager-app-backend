from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.errors.validation import ValidationError


class WorkingSectionDeleteRequest(BaseModel):
    client_id: str

    @field_validator("client_id", mode="before")
    @classmethod
    def client_id_must_not_be_blank(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("client_id must not be blank.")
        return value


def parse_delete_working_section_request(data: dict) -> WorkingSectionDeleteRequest:
    try:
        return WorkingSectionDeleteRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
