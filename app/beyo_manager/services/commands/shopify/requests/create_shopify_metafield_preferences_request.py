from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError as PydanticValidationError, field_validator, model_validator

from beyo_manager.domain.shopify.metafield_preferences import is_shopify_metafield_definition_gid
from beyo_manager.errors.validation import ValidationError


class CreateShopifyMetafieldPreferenceSelectionRequest(BaseModel):
    client_id: str | None = None
    shop_integration_id: str
    shopify_metafield_definition_id: str
    sequence_order: int = Field(ge=0)

    @field_validator("shopify_metafield_definition_id")
    @classmethod
    def _validate_gid_shape(cls, value: str) -> str:
        if not is_shopify_metafield_definition_gid(value):
            raise ValueError("shopify_metafield_definition_id must be a Shopify MetafieldDefinition GID.")
        return value


class CreateShopifyMetafieldPreferencesRequest(BaseModel):
    item_category_id: str
    preferences: list[CreateShopifyMetafieldPreferenceSelectionRequest] = Field(min_length=1)

    @model_validator(mode="after")
    def _reject_duplicate_selections(self) -> "CreateShopifyMetafieldPreferencesRequest":
        seen: set[tuple[str, str]] = set()
        seen_client_ids: set[str] = set()
        for selection in self.preferences:
            key = (selection.shop_integration_id, selection.shopify_metafield_definition_id)
            if key in seen:
                raise ValueError(
                    "Duplicate preference selection for the same shop_integration_id "
                    "and shopify_metafield_definition_id."
                )
            seen.add(key)
            if selection.client_id is not None:
                if selection.client_id in seen_client_ids:
                    raise ValueError("Duplicate client_id in preference selections.")
                seen_client_ids.add(selection.client_id)
        return self


def parse_create_shopify_metafield_preferences_request(
    data: dict,
) -> CreateShopifyMetafieldPreferencesRequest:
    try:
        return CreateShopifyMetafieldPreferencesRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(part) for part in first_error["loc"])
        prefix = f"{field}: " if field else ""
        raise ValidationError(f"{prefix}{first_error['msg']}") from exc
