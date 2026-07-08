from __future__ import annotations

from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.shopify._linking import link_or_update_shopify_shop_record
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


class LinkOrUpdateShopifyShopRequest(BaseModel):
    workspace_id: str
    user_id: str
    shop_domain: str
    access_token: str
    requested_scopes: list[str]
    granted_scopes: list[str]
    api_version: str
    shop_name: str | None = None

    @field_validator("workspace_id", "user_id", "shop_domain", "access_token", "api_version")
    @classmethod
    def _required_strings_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank.")
        return value


def parse_link_or_update_shopify_shop_request(data: dict) -> LinkOrUpdateShopifyShopRequest:
    try:
        return LinkOrUpdateShopifyShopRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(part) for part in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


async def link_or_update_shopify_shop(ctx: ServiceContext) -> dict:
    request = parse_link_or_update_shopify_shop_request(ctx.incoming_data)
    async with maybe_begin(ctx.session):
        integration = await link_or_update_shopify_shop_record(
            ctx.session,
            workspace_id=request.workspace_id,
            user_id=request.user_id,
            shop_domain=request.shop_domain,
            access_token=request.access_token,
            requested_scopes=tuple(request.requested_scopes),
            granted_scopes=tuple(request.granted_scopes),
            api_version=request.api_version,
            shop_name=request.shop_name,
        )
    return {
        "shop_integration_id": integration.client_id,
        "shop_domain": integration.shop_domain,
        "status": integration.status.value,
    }
