from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.errors.validation import ValidationError


class WorkingSectionCreateRequest(BaseModel):
    client_id: str | None = None
    name: str
    image: str | None = None
    order_list: int | None = None
    allows_batch_working: bool = False
    working_section_dependencies: list[str] = []
    working_section_item_categories: list[str] = []
    working_section_supported_issue_types: list[str] = []

    @field_validator("name", mode="before")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("name must not be blank.")
        return value

    @field_validator("image", mode="before")
    @classmethod
    def strip_image(cls, v: str | None) -> str | None:
        if v is None:
            return v
        value = v.strip()
        return value if value else None


def parse_create_working_section_request(data: dict) -> WorkingSectionCreateRequest:
    try:
        return WorkingSectionCreateRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
