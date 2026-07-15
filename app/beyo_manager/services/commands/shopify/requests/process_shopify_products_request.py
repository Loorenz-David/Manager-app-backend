from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError as PydanticValidationError, field_validator, model_validator

from beyo_manager.errors.validation import ValidationError

_SUPPORTED_WEIGHT_UNITS = {"kg", "g", "lb", "oz"}
_MAX_ITEMS_PER_REQUEST = 200
_MAX_INVENTORY_INCREMENT = 1_000_000
_SHOPIFY_LOCATION_GID_PATTERN = r"^gid://shopify/Location/[0-9]+$"


class InventoryAdjustmentRequest(BaseModel):
    shop_integration_id: str
    location_id: str
    quantity_to_add: int

    @field_validator("shop_integration_id", "location_id", mode="before")
    @classmethod
    def _trim_ids(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return value.strip()

    @field_validator("location_id")
    @classmethod
    def _validate_location_gid(cls, value: str) -> str:
        import re

        if not re.fullmatch(_SHOPIFY_LOCATION_GID_PATTERN, value):
            raise ValueError("location_id must be a Shopify Location GID")
        return value

    @field_validator("quantity_to_add", mode="before")
    @classmethod
    def _validate_quantity_type(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("quantity_to_add must be an integer")
        return value

    @field_validator("quantity_to_add")
    @classmethod
    def _validate_quantity_range(cls, value: int) -> int:
        if value < 0:
            raise ValueError("quantity_to_add cannot be negative")
        if value > _MAX_INVENTORY_INCREMENT:
            raise ValueError(f"quantity_to_add cannot exceed {_MAX_INVENTORY_INCREMENT}")
        return value


class WeightRequest(BaseModel):
    value: float
    unit: str

    @field_validator("unit", mode="before")
    @classmethod
    def _validate_unit(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Input should be a valid string")
        stripped = value.strip().lower()
        if stripped not in _SUPPORTED_WEIGHT_UNITS:
            raise ValueError("unit must be one of: g, kg, lb, oz")
        return stripped


class ProcessShopifyProductItemRequest(BaseModel):
    client_id: str
    target_shop_integration_ids: list[str] | None = None
    title: str
    description: str | None = None
    status: str | None = None
    tags: list[str] = Field(default_factory=list)
    product_category: str | None = None
    price: str | None = None
    weight: WeightRequest | None = None
    sku: str | None = None
    item_article_number: str | None = None
    article_number: str | None = None
    metafields: dict[str, object] = Field(default_factory=dict)
    inventory_adjustments: list[InventoryAdjustmentRequest] = Field(default_factory=list)

    @field_validator(
        "client_id",
        "title",
        "description",
        "status",
        "product_category",
        "price",
        "sku",
        "item_article_number",
        "article_number",
        mode="before",
    )
    @classmethod
    def _trim_optional_text(cls, value: object) -> str | None | object:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("Input should be a valid list")
        normalized: list[str] = []
        for tag in value:
            if not isinstance(tag, str):
                raise ValueError("tags entries must be strings")
            stripped = tag.strip()
            if stripped:
                normalized.append(stripped)
        return normalized

    @field_validator("target_shop_integration_ids", mode="before")
    @classmethod
    def _normalize_target_ids(cls, value: object) -> list[str] | None:
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError("Input should be a valid list")
        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("target_shop_integration_ids entries must be strings")
            stripped = item.strip()
            if stripped:
                normalized.append(stripped)
        return normalized

    @model_validator(mode="after")
    def _require_identity(self) -> "ProcessShopifyProductItemRequest":
        if self.sku is None and self.item_article_number is None and self.article_number is None:
            raise ValueError("At least one of sku, item_article_number, or article_number is required.")
        if self.target_shop_integration_ids == []:
            raise ValueError("target_shop_integration_ids cannot be empty when provided.")
        seen_locations: set[tuple[str, str]] = set()
        for adjustment in self.inventory_adjustments:
            key = (adjustment.shop_integration_id, adjustment.location_id)
            if key in seen_locations:
                raise ValueError("duplicate_inventory_location")
            seen_locations.add(key)
        return self

    @field_validator("inventory_adjustments", mode="before")
    @classmethod
    def _drop_zero_inventory_adjustments(cls, value: object) -> object:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("inventory_adjustments must be a list")
        return [
            entry
            for entry in value
            if not (isinstance(entry, dict) and entry.get("quantity_to_add") == 0)
        ]


class ProcessShopifyProductsRequest(BaseModel):
    items: list[ProcessShopifyProductItemRequest] = Field(min_length=1, max_length=_MAX_ITEMS_PER_REQUEST)


def parse_process_shopify_products_request(data: dict) -> ProcessShopifyProductsRequest:
    try:
        return ProcessShopifyProductsRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(part) for part in first_error["loc"])
        prefix = f"{field}: " if field else ""
        raise ValidationError(f"{prefix}{first_error['msg']}") from exc
