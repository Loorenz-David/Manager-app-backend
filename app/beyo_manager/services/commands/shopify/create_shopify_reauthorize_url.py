from __future__ import annotations

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.services.commands.shopify.create_shopify_install_url import create_shopify_install_url
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def create_shopify_reauthorize_url(ctx: ServiceContext) -> dict:
    shop_integration_id = str(ctx.incoming_data.get("shop_integration_id") or "").strip()
    if not shop_integration_id:
        raise NotFound("Shopify shop integration not found.")

    async with maybe_begin(ctx.session):
        integration = await ctx.session.get(ShopifyShopIntegration, shop_integration_id)
        if integration is None or integration.workspace_id != ctx.workspace_id or integration.is_deleted:
            raise NotFound("Shopify shop integration not found.")

        return await create_shopify_install_url(
            ServiceContext(
                identity=ctx.identity,
                incoming_data={
                    "shop_domain": integration.shop_domain,
                    "redirect_after_success": "default",
                },
                session=ctx.session,
            )
        )
