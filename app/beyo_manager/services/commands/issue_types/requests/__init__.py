from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.domain.issue_types.enums import IssueModeEnum
from beyo_manager.errors.validation import ValidationError


class ItemCategoryIssueTypeLinkInput(BaseModel):
    item_category_id: str
    placement_of_issue: str | None = None

    @field_validator("placement_of_issue")
    @classmethod
    def normalize_placement_of_issue(cls, v: str | None) -> str | None:
        if v is None:
            return None
        normalized = v.strip()
        if not normalized:
            return None
        return normalized


class CreateIssueTypeRequest(BaseModel):
    issue_type_name: str
    issue_mode: IssueModeEnum
    linked_working_section_ids: list[str] = []
    linked_item_category_ids: list[ItemCategoryIssueTypeLinkInput] = []

    @field_validator("issue_type_name")
    @classmethod
    def issue_type_name_must_not_be_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("issue_type_name must not be empty.")
        return v

    @field_validator("linked_item_category_ids")
    @classmethod
    def linked_item_category_ids_must_be_unique_by_category_and_placement(
        cls, v: list[ItemCategoryIssueTypeLinkInput]
    ) -> list[ItemCategoryIssueTypeLinkInput]:
        seen: set[tuple[str, str | None]] = set()
        for entry in v:
            key = (entry.item_category_id, entry.placement_of_issue)
            if key in seen:
                raise ValueError(
                    "linked_item_category_ids contains duplicate item_category_id + placement_of_issue combinations."
                )
            seen.add(key)
        return v


class UpdateIssueTypeRequest(BaseModel):
    issue_type_id: str
    issue_type_name: str | None = None
    issue_mode: IssueModeEnum | None = None
    linked_working_section_ids: list[str] | None = None
    linked_item_category_ids: list[ItemCategoryIssueTypeLinkInput] | None = None

    @field_validator("issue_type_name")
    @classmethod
    def issue_type_name_must_not_be_empty(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("issue_type_name must not be empty.")
        return v

    @field_validator("linked_item_category_ids")
    @classmethod
    def linked_item_category_ids_must_be_unique_by_category_and_placement(
        cls, v: list[ItemCategoryIssueTypeLinkInput] | None
    ) -> list[ItemCategoryIssueTypeLinkInput] | None:
        if v is None:
            return v
        seen: set[tuple[str, str | None]] = set()
        for entry in v:
            key = (entry.item_category_id, entry.placement_of_issue)
            if key in seen:
                raise ValueError(
                    "linked_item_category_ids contains duplicate item_category_id + placement_of_issue combinations."
                )
            seen.add(key)
        return v


class DeleteIssueTypeInput(BaseModel):
    issue_type_id: str


class DeleteIssueTypesRequest(BaseModel):
    issues: list[DeleteIssueTypeInput]

    @field_validator("issues")
    @classmethod
    def issues_must_not_be_empty(cls, v: list[DeleteIssueTypeInput]) -> list[DeleteIssueTypeInput]:
        if not v:
            raise ValueError("issues must contain at least one entry.")
        return v


def _raise_validation_error(exc: PydanticValidationError) -> None:
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"])
    raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_create_issue_type_request(data: dict) -> CreateIssueTypeRequest:
    try:
        return CreateIssueTypeRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_update_issue_type_request(data: dict) -> UpdateIssueTypeRequest:
    try:
        return UpdateIssueTypeRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_delete_issue_types_request(data: dict) -> DeleteIssueTypesRequest:
    try:
        return DeleteIssueTypesRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)
