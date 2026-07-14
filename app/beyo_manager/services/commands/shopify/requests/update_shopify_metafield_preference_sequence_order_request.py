from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError as PydanticValidationError

from beyo_manager.errors.validation import ValidationError


class UpdateShopifyMetafieldPreferenceSequenceOrderRequest(BaseModel):
    client_id: str
    sequence_order: int = Field(ge=0)


def parse_update_shopify_metafield_preference_sequence_order_request(
    data: dict,
) -> UpdateShopifyMetafieldPreferenceSequenceOrderRequest:
    try:
        return UpdateShopifyMetafieldPreferenceSequenceOrderRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(part) for part in first_error["loc"])
        prefix = f"{field}: " if field else ""
        raise ValidationError(f"{prefix}{first_error['msg']}") from exc
