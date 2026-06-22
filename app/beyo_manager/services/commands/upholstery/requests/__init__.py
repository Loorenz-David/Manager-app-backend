"""Request models for upholstery inventory commands."""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, field_validator

from beyo_manager.domain.upholstery.enums import UpholsteryCurrencyEnum, UpholsteryOrderStateEnum
from beyo_manager.errors.validation import ValidationError


_METERS_SCALE = Decimal("0.001")


def _normalize_meters(value: Decimal) -> Decimal:
    """Round meter values to DB-compatible scale (Numeric(14, 3))."""
    return value.quantize(_METERS_SCALE, rounding=ROUND_HALF_UP)


class CreateUpholsteryInventoryRequest(BaseModel):
    """Request to create a new upholstery inventory record."""

    client_id: str | None = None
    upholstery_id: str
    low_stock_threshold_meters: Decimal | None = None
    minimum_to_have: int | None = None
    maximum_to_have: int | None = None
    projected_inventory_value_minor: int | None = None
    currency: UpholsteryCurrencyEnum | None = None
    planning_position: str | None = None

    @field_validator("low_stock_threshold_meters")
    @classmethod
    def threshold_must_be_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= Decimal("0"):
            raise ValueError("low_stock_threshold_meters must be greater than 0.")
        return v

    @field_validator("minimum_to_have", "maximum_to_have", "projected_inventory_value_minor")
    @classmethod
    def must_be_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("Value must be >= 0.")
        return v


def parse_create_upholstery_inventory_request(data: dict) -> CreateUpholsteryInventoryRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return CreateUpholsteryInventoryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class UpdateUpholsteryInventoryRequest(BaseModel):
    """Request to update an upholstery inventory record."""

    client_id: str
    low_stock_threshold_meters: Decimal | None = None
    minimum_to_have: int | None = None
    maximum_to_have: int | None = None
    projected_inventory_value_minor: int | None = None
    currency: UpholsteryCurrencyEnum | None = None
    planning_position: str | None = None

    @field_validator("low_stock_threshold_meters")
    @classmethod
    def threshold_must_be_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= Decimal("0"):
            raise ValueError("low_stock_threshold_meters must be greater than 0.")
        return v


def parse_update_upholstery_inventory_request(data: dict) -> UpdateUpholsteryInventoryRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return UpdateUpholsteryInventoryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class DeleteUpholsteryInventoryRequest(BaseModel):
    """Request to delete an upholstery inventory record."""

    client_id: str


def parse_delete_upholstery_inventory_request(data: dict) -> DeleteUpholsteryInventoryRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return DeleteUpholsteryInventoryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class AddOrderedRequest(BaseModel):
    """Request to add ordered quantity to inventory."""

    client_id: str
    quantity: Decimal

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("quantity must be > 0.")
        return v


def parse_add_ordered_request(data: dict) -> AddOrderedRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return AddOrderedRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class ConfirmOrderedRequest(BaseModel):
    """Request to confirm ordered quantity as received stock."""

    client_id: str
    quantity: Decimal

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("quantity must be > 0.")
        return v


def parse_confirm_ordered_request(data: dict) -> ConfirmOrderedRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return ConfirmOrderedRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class SetCurrentStoredAmountInventoryRequest(BaseModel):
    """Request to set the absolute stored stock amount for an inventory record."""

    client_id: str
    current_stored_amount_meters: Decimal

    @field_validator("current_stored_amount_meters")
    @classmethod
    def validate_current_stored_amount_meters(cls, v: Decimal) -> Decimal:
        normalized = _normalize_meters(v)
        if normalized < Decimal("0"):
            raise ValueError("current_stored_amount_meters must be >= 0.")
        return normalized


def parse_set_current_stored_amount_inventory_request(
    data: dict,
) -> SetCurrentStoredAmountInventoryRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return SetCurrentStoredAmountInventoryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class CreateUpholsteryRequest(BaseModel):
    client_id: str | None = None
    name: str
    code: str | None = None
    image_url: str | None = None
    favorite: bool = False
    current_stored_amount_meters: Decimal | None = None
    low_stock_threshold_meters: Decimal | None = None
    minimum_to_have: int | None = None
    maximum_to_have: int | None = None
    projected_inventory_value_minor: int | None = None
    currency: UpholsteryCurrencyEnum | None = None
    planning_position: str | None = None
    upholstery_category_id: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        value = (v or "").strip()
        if not value:
            raise ValueError("name must not be blank.")
        return value

    @field_validator("low_stock_threshold_meters")
    @classmethod
    def create_threshold_must_be_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= Decimal("0"):
            raise ValueError("low_stock_threshold_meters must be greater than 0.")
        return v

    @field_validator("current_stored_amount_meters")
    @classmethod
    def create_current_stock_must_be_non_negative(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < Decimal("0"):
            raise ValueError("current_stored_amount_meters must be >= 0.")
        return v

    @field_validator("minimum_to_have", "maximum_to_have", "projected_inventory_value_minor")
    @classmethod
    def create_must_be_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("Value must be >= 0.")
        return v


def parse_create_upholstery_request(data: dict) -> CreateUpholsteryRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return CreateUpholsteryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class UpdateUpholsteryRequest(BaseModel):
    client_id: str
    name: str | None = None
    code: str | None = None
    image_url: str | None = None
    favorite: bool | None = None
    upholstery_category_id: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        value = v.strip()
        if not value:
            raise ValueError("name must not be blank.")
        return value


def parse_update_upholstery_request(data: dict) -> UpdateUpholsteryRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return UpdateUpholsteryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class CreateUpholsteryCategoryRequest(BaseModel):
    client_id: str | None = None
    name: str
    image_url: str | None = None
    favorite: bool = False

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        value = (v or "").strip()
        if not value:
            raise ValueError("name must not be blank.")
        return value


def parse_create_upholstery_category_request(data: dict) -> CreateUpholsteryCategoryRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return CreateUpholsteryCategoryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class UpdateUpholsteryCategoryRequest(BaseModel):
    client_id: str
    name: str | None = None
    image_url: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        value = v.strip()
        if not value:
            raise ValueError("name must not be blank.")
        return value


def parse_update_upholstery_category_request(data: dict) -> UpdateUpholsteryCategoryRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return UpdateUpholsteryCategoryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class DeleteUpholsteryCategoryRequest(BaseModel):
    client_id: str


def parse_delete_upholstery_category_request(data: dict) -> DeleteUpholsteryCategoryRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return DeleteUpholsteryCategoryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class MarkUpholsteryCategoryFavoriteRequest(BaseModel):
    client_id: str
    favorite: bool


def parse_mark_upholstery_category_favorite_request(data: dict) -> MarkUpholsteryCategoryFavoriteRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return MarkUpholsteryCategoryFavoriteRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class DeleteUpholsteryRequest(BaseModel):
    client_id: str


def parse_delete_upholstery_request(data: dict) -> DeleteUpholsteryRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return DeleteUpholsteryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class MarkUpholsteryFavoriteRequest(BaseModel):
    client_id: str
    favorite: bool


def parse_mark_upholstery_favorite_request(data: dict) -> MarkUpholsteryFavoriteRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return MarkUpholsteryFavoriteRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class CreateUpholsteryOrderRequest(BaseModel):
    client_id: str | None = None
    upholstery_id: str
    order_amount_meters: Decimal
    priority_item_upholstery_ids: list[str] = []
    state: UpholsteryOrderStateEnum = UpholsteryOrderStateEnum.ORDERED
    supplier_id: str | None = None
    upholstery_supplier_link_id: str | None = None
    price_minor: int | None = None
    currency: UpholsteryCurrencyEnum | None = None
    order_at: datetime | None = None
    expected_receive_at: datetime | None = None

    @field_validator("state")
    @classmethod
    def validate_creation_state(cls, v: UpholsteryOrderStateEnum) -> UpholsteryOrderStateEnum:
        allowed = {
            UpholsteryOrderStateEnum.DRAFT,
            UpholsteryOrderStateEnum.PENDING,
            UpholsteryOrderStateEnum.APPROVED,
            UpholsteryOrderStateEnum.ORDERED,
        }
        if v not in allowed:
            raise ValueError("state on creation must be one of: draft, pending, approved, ordered.")
        return v

    @field_validator("order_amount_meters")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("order_amount_meters must be > 0.")
        return v

    @field_validator("price_minor")
    @classmethod
    def price_must_be_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("price_minor must be >= 0.")
        return v


def parse_create_upholstery_order_request(data: dict) -> CreateUpholsteryOrderRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return CreateUpholsteryOrderRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class MarkUpholsteriesFavoriteRequest(BaseModel):
    upholstery_ids: list[str]
    favorite: bool

    @field_validator("upholstery_ids")
    @classmethod
    def ensure_non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("upholstery_ids must not be empty.")
        return v


def parse_mark_upholsteries_favorite_request(data: dict) -> MarkUpholsteriesFavoriteRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return MarkUpholsteriesFavoriteRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class UpdateUpholsteryListOrderRequest(BaseModel):
    client_id: str
    list_order: int | None = None

    @field_validator("list_order")
    @classmethod
    def validate_list_order(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("list_order must be >= 1.")
        return v


def parse_update_upholstery_list_order_request(data: dict) -> UpdateUpholsteryListOrderRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return UpdateUpholsteryListOrderRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class ReceiveUpholsteryOrderRequest(BaseModel):
    client_id: str
    received_amount_meters: Decimal
    priority_item_upholstery_ids: list[str] = []
    received_at: datetime | None = None

    @field_validator("received_amount_meters")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        normalized = _normalize_meters(v)
        if normalized <= Decimal("0"):
            raise ValueError("received_amount_meters must be > 0.")
        return normalized


def parse_receive_upholstery_order_request(data: dict) -> ReceiveUpholsteryOrderRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return ReceiveUpholsteryOrderRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
