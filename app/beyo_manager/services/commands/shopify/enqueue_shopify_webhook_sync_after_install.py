from __future__ import annotations

from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.services.commands.shopify._webhook_sync import record_webhook_sync_pending
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


class EnqueueShopifyWebhookSyncAfterInstallRequest(BaseModel):
    workspace_id: str
    user_id: str
    shop_integration_id: str
    shop_domain: str

    @field_validator("workspace_id", "user_id", "shop_integration_id", "shop_domain")
    @classmethod
    def _required_strings_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank.")
        return value


def parse_enqueue_shopify_webhook_sync_after_install_request(
    data: dict,
) -> EnqueueShopifyWebhookSyncAfterInstallRequest:
    try:
        return EnqueueShopifyWebhookSyncAfterInstallRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(part) for part in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


async def enqueue_shopify_webhook_sync_after_install(ctx: ServiceContext) -> dict:
    request = parse_enqueue_shopify_webhook_sync_after_install_request(ctx.incoming_data)
    async with maybe_begin(ctx.session):
        integration = await ctx.session.get(ShopifyShopIntegration, request.shop_integration_id)
        if integration is None:
            raise ValidationError("shop_integration_id does not reference an existing Shopify integration.")

        await record_webhook_sync_pending(
            ctx.session,
            workspace_id=request.workspace_id,
            user_id=request.user_id,
            shop_integration_id=request.shop_integration_id,
            shop_domain=request.shop_domain,
        )

    return {
        "shop_integration_id": request.shop_integration_id,
        "sync_status": "pending",
    }
