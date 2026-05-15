from pydantic import (
    BaseModel,
    ValidationError as PydanticValidationError,
    field_validator,
    model_validator,
)

from beyo_manager.errors.validation import ValidationError


class WorkingSectionEditRequest(BaseModel):
    client_id: str
    name: str | None = None
    image: str | None = None
    working_section_dependencies: list[str] | None = None
    working_section_item_categories: list[str] | None = None
    working_section_supported_issue_types: list[str] | None = None

    @field_validator("client_id", mode="before")
    @classmethod
    def client_id_must_not_be_blank(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("client_id must not be blank.")
        return value

    @field_validator("name", mode="before")
    @classmethod
    def name_must_not_be_blank_if_provided(cls, v: str | None) -> str | None:
        if v is None:
            return v
        value = v.strip()
        if not value:
            raise ValueError("name must not be blank.")
        return value

    @model_validator(mode="after")
    def at_least_one_updatable_field(self) -> "WorkingSectionEditRequest":
        updatable = {
            "name",
            "image",
            "working_section_dependencies",
            "working_section_item_categories",
            "working_section_supported_issue_types",
        }
        if not (updatable & self.model_fields_set):
            raise ValueError(
                "At least one of name, image, working_section_dependencies, "
                "working_section_item_categories, or working_section_supported_issue_types must be provided."
            )
        return self


def parse_edit_working_section_request(data: dict) -> WorkingSectionEditRequest:
    try:
        return WorkingSectionEditRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
