"""Request models for upholstery inventory commands."""

from decimal import Decimal

from pydantic import BaseModel, field_validator

from beyo_manager.domain.upholstery.enums import UpholsteryCurrencyEnum
from beyo_manager.errors.validation import ValidationError


class CreateUpholsteryInventoryRequest(BaseModel):
    """Request to create a new upholstery inventory record."""

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
