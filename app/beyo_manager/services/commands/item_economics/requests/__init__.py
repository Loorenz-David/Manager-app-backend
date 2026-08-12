"""Request models and parsers for item-economics configuration commands."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN

from pydantic import BaseModel, ConfigDict, Field, ValidationError as PydanticValidationError, field_validator

from beyo_manager.domain.item_economics.enums import CostModelTermCalculationTypeEnum
from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.errors.validation import ValidationError


def _decimal(value: object, field: str, scale: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a decimal")
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (ArithmeticError, ValueError, TypeError) as exc:
        raise ValueError(f"{field} must be a decimal") from exc
    return parsed.quantize(Decimal(scale), rounding=ROUND_HALF_EVEN)


class _Request(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ProductionCostGroupCreateRequest(_Request):
    name: str

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value


class ProductionCostGroupUpdateRequest(_Request):
    client_id: str
    name: str

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value


class ClientIdRequest(_Request):
    client_id: str


class AddSectionToCostGroupRequest(_Request):
    production_cost_group_id: str
    working_section_id: str


class RemoveSectionFromCostGroupRequest(_Request):
    production_cost_group_id: str
    working_section_id: str


class ProductionCostBasisVersionCreateRequest(_Request):
    production_cost_group_id: str
    effective_from: date | None = None
    fixed_monthly_cost_minor: int
    currency: ItemCurrencyEnum
    monthly_paid_hours: Decimal
    planning_utilization_percent: Decimal

    @field_validator("monthly_paid_hours", mode="before")
    @classmethod
    def canonicalize_hours(cls, value: object) -> Decimal:
        return _decimal(value, "monthly_paid_hours", "0.01")

    @field_validator("planning_utilization_percent", mode="before")
    @classmethod
    def canonicalize_utilization(cls, value: object) -> Decimal:
        return _decimal(value, "planning_utilization_percent", "0.01")


class CostModelTermRequest(_Request):
    name: str
    calculation_type: CostModelTermCalculationTypeEnum
    percent_value: Decimal | None = None
    fixed_amount_minor: int | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value

    @field_validator("percent_value", mode="before")
    @classmethod
    def canonicalize_percent(cls, value: object) -> Decimal | None:
        return None if value is None else _decimal(value, "percent_value", "0.001")


class CostModelVersionCreateRequest(_Request):
    effective_from: date | None = None
    currency: ItemCurrencyEnum
    terms: list[CostModelTermRequest] = Field(default_factory=list)


def _parse(model: type[BaseModel], data: dict) -> BaseModel:
    try:
        return model.model_validate(data)
    except PydanticValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(loc) for loc in first["loc"])
        raise ValidationError(f"{field}: {first['msg']}") from exc


def parse_production_cost_group_create_request(data: dict) -> ProductionCostGroupCreateRequest:
    return _parse(ProductionCostGroupCreateRequest, data)  # type: ignore[return-value]


def parse_production_cost_group_update_request(data: dict) -> ProductionCostGroupUpdateRequest:
    return _parse(ProductionCostGroupUpdateRequest, data)  # type: ignore[return-value]


def parse_client_id_request(data: dict) -> ClientIdRequest:
    return _parse(ClientIdRequest, data)  # type: ignore[return-value]


def parse_add_section_to_cost_group_request(data: dict) -> AddSectionToCostGroupRequest:
    return _parse(AddSectionToCostGroupRequest, data)  # type: ignore[return-value]


def parse_remove_section_from_cost_group_request(data: dict) -> RemoveSectionFromCostGroupRequest:
    return _parse(RemoveSectionFromCostGroupRequest, data)  # type: ignore[return-value]


def parse_production_cost_basis_version_create_request(data: dict) -> ProductionCostBasisVersionCreateRequest:
    return _parse(ProductionCostBasisVersionCreateRequest, data)  # type: ignore[return-value]


def parse_cost_model_version_create_request(data: dict) -> CostModelVersionCreateRequest:
    return _parse(CostModelVersionCreateRequest, data)  # type: ignore[return-value]
