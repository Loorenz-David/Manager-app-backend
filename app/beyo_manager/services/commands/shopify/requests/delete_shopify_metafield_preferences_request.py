from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError as PydanticValidationError

from beyo_manager.errors.validation import ValidationError


class DeleteShopifyMetafieldPreferencesRequest(BaseModel):
    client_ids: list[str] = Field(min_length=1)


def parse_delete_shopify_metafield_preferences_request(
    data: dict,
) -> DeleteShopifyMetafieldPreferencesRequest:
    try:
        return DeleteShopifyMetafieldPreferencesRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(part) for part in first_error["loc"])
        prefix = f"{field}: " if field else ""
        raise ValidationError(f"{prefix}{first_error['msg']}") from exc
