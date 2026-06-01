"""Request models for item upholstery lifecycle commands."""

from decimal import Decimal
from pydantic import BaseModel, field_validator
from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemUpholsterySourceEnum
from beyo_manager.errors.validation import ValidationError


class CreateItemUpholsteryRequest(BaseModel):
    """Request to create ItemUpholstery and initial requirement."""
    client_id: str | None = None
    item_id: str
    upholstery_id: str | None = None
    name: str | None = None
    code: str | None = None
    amount_meters: Decimal | None = None
    source: ItemUpholsterySourceEnum
    time_to_fix_in_seconds: int | None = None

    @field_validator("amount_meters", mode="before")
    @classmethod
    def coerce_zero_to_null(cls, v) -> Decimal | None:
        if v is None:
            return None
        v = Decimal(str(v))
        return None if v <= Decimal("0") else v

    @field_validator("time_to_fix_in_seconds")
    @classmethod
    def time_must_be_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("time_to_fix_in_seconds must be >= 0.")
        return v


class UpdateItemUpholsteryRequest(BaseModel):
    """Request to update ItemUpholstery fields."""
    client_id: str
    upholstery_id: str | None = None
    source: ItemUpholsterySourceEnum | None = None
    name: str | None = None
    code: str | None = None
    amount_meters: Decimal | None = None
    time_to_fix_in_seconds: int | None = None


class DeleteItemUpholsteryRequest(BaseModel):
    """Request to soft delete ItemUpholstery."""
    client_id: str


class MarkInUseRequest(BaseModel):
    """Request to mark available requirements as in-use."""
    item_upholstery_id: str


class MarkCompletedRequest(BaseModel):
    """Request to mark all active requirements as completed."""
    item_upholstery_id: str


class MarkOrderedRequest(BaseModel):
    """Request to allocate ordered quantity to needs-ordering requirements."""
    upholstery_id: str
    ordered_quantity: Decimal
    priority_item_upholstery_ids: list[str] = []

    @field_validator("ordered_quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("ordered_quantity must be > 0.")
        return v


class ResolveAfterStockRequest(BaseModel):
    """Request to recalculate requirements after stock arrival."""
    upholstery_id: str
    priority_item_upholstery_ids: list[str] = []


class ApplySurplusRequest(BaseModel):
    """Request to apply offcut material to requirement."""
    item_upholstery_id: str
    surplus_amount_meters: Decimal

    @field_validator("surplus_amount_meters")
    @classmethod
    def surplus_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("surplus_amount_meters must be > 0.")
        return v


class UpdateRequirementQuantityRequest(BaseModel):
    """Request to set or update quantity on a mutable requirement."""
    item_upholstery_id: str
    amount_meters: Decimal

    @field_validator("amount_meters")
    @classmethod
    def quantity_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("amount_meters must be > 0.")
        return v


class CompleteSingleRequirementRequest(BaseModel):
    """Request to complete a single in-use requirement."""
    client_id: str


class ReallocateStockRequest(BaseModel):
    """Request to reallocate stock among requirements."""
    upholstery_id: str
    donor_item_upholstery_ids: list[str] = []
    priority_item_upholstery_ids: list[str] = []


class ItemIssueCreateInput(BaseModel):
    """Nested input for one issue to create atomically with an item."""

    issue_type_id: str | None = None
    issue_severity_id: str | None = None
    base_time_seconds: int | None = None
    time_multiplier: Decimal | None = None
    issue_name_snapshot: str | None = None
    severity_name_snapshot: str | None = None


class ItemUpholsteryCreateInput(BaseModel):
    """Nested input for the upholstery to create atomically with an item."""

    client_id: str | None = None
    upholstery_id: str | None = None
    source: ItemUpholsterySourceEnum
    name: str | None = None
    code: str | None = None
    amount_meters: Decimal | None = None
    time_to_fix_in_seconds: int | None = None

    @field_validator("amount_meters", mode="before")
    @classmethod
    def coerce_zero_to_null(cls, v) -> Decimal | None:
        if v is None:
            return None
        v = Decimal(str(v))
        return None if v <= Decimal("0") else v

    @field_validator("time_to_fix_in_seconds")
    @classmethod
    def time_must_be_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("time_to_fix_in_seconds must be >= 0.")
        return v


class CreateItemRequest(BaseModel):
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
    external_id: str | None = None
    external_url: str | None = None
    external_source: str | None = None
    external_order_id: str | None = None
    item_issues: list[ItemIssueCreateInput] | None = None
    item_upholstery: ItemUpholsteryCreateInput | None = None

    @field_validator("article_number", "sku", mode="before")
    @classmethod
    def strip_or_none(cls, v) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("quantity must be >= 1.")
        return v


class CreateItemIssueRequest(BaseModel):
    item_id: str
    issue_type_id: str | None = None
    issue_severity_id: str | None = None
    base_time_seconds: int | None = None
    time_multiplier: Decimal | None = None
    issue_name_snapshot: str | None = None
    severity_name_snapshot: str | None = None


class UpdateItemRequest(BaseModel):
    client_id: str
    article_number: str | None = None
    sku: str | None = None
    item_category_id: str | None = None
    quantity: int | None = None
    designer: str | None = None
    height_in_cm: int | None = None
    width_in_cm: int | None = None
    depth_in_cm: int | None = None
    item_value_minor: int | None = None
    item_cost_minor: int | None = None
    item_currency: ItemCurrencyEnum | None = None
    item_position: str | None = None
    external_id: str | None = None
    external_url: str | None = None
    external_source: str | None = None
    external_order_id: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("quantity must be >= 1.")
        return v


class DeleteItemRequest(BaseModel):
    client_id: str


class DeleteItemIssueRequest(BaseModel):
    item_id: str
    client_id: str


class DeleteItemIssuesRequest(BaseModel):
    item_id: str
    issue_ids: list[str]

    @field_validator("issue_ids")
    @classmethod
    def issue_ids_must_not_be_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("issue_ids must contain at least one id.")
        return v


# Parsing functions
def parse_create_item_upholstery_request(data: dict) -> CreateItemUpholsteryRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return CreateItemUpholsteryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_update_item_upholstery_request(data: dict) -> UpdateItemUpholsteryRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return UpdateItemUpholsteryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_delete_item_upholstery_request(data: dict) -> DeleteItemUpholsteryRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return DeleteItemUpholsteryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_mark_in_use_request(data: dict) -> MarkInUseRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return MarkInUseRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_mark_completed_request(data: dict) -> MarkCompletedRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return MarkCompletedRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_mark_ordered_request(data: dict) -> MarkOrderedRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return MarkOrderedRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_resolve_after_stock_request(data: dict) -> ResolveAfterStockRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return ResolveAfterStockRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_apply_surplus_request(data: dict) -> ApplySurplusRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return ApplySurplusRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_update_requirement_quantity_request(data: dict) -> UpdateRequirementQuantityRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return UpdateRequirementQuantityRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_complete_single_requirement_request(data: dict) -> CompleteSingleRequirementRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return CompleteSingleRequirementRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_reallocate_stock_request(data: dict) -> ReallocateStockRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return ReallocateStockRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_create_item_request(data: dict) -> CreateItemRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return CreateItemRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_create_item_issue_request(data: dict) -> CreateItemIssueRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return CreateItemIssueRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_update_item_request(data: dict) -> UpdateItemRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return UpdateItemRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_delete_item_request(data: dict) -> DeleteItemRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return DeleteItemRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_delete_item_issue_request(data: dict) -> DeleteItemIssueRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return DeleteItemIssueRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_delete_item_issues_request(data: dict) -> DeleteItemIssuesRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return DeleteItemIssuesRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class FindOrCreateItemRequest(BaseModel):
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
    external_id: str | None = None
    external_url: str | None = None
    external_source: str | None = None
    external_order_id: str | None = None

    @field_validator("article_number", "sku", mode="before")
    @classmethod
    def strip_or_none(cls, v) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("quantity must be >= 1.")
        return v


def parse_find_or_create_item_request(data: dict) -> FindOrCreateItemRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return FindOrCreateItemRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
