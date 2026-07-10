from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError as PydanticValidationError, field_validator, model_validator

from beyo_manager.errors.validation import ValidationError

_SUPPORTED_WEIGHT_UNITS = {"kg", "g", "lb", "oz"}
_MAX_ITEMS_PER_REQUEST = 200


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
        return self


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
