from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import load_only, selectinload

from beyo_manager.domain.shopify.serializers import serialize_shopify_shop_integration
from beyo_manager.domain.shopify.serializers import serialize_shopify_webhook_subscription
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.shopify.shopify_webhook_subscription import ShopifyWebhookSubscription
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.context import ServiceContext


async def get_shopify_shop_integration(ctx: ServiceContext) -> dict:
    shop_integration_id = str(ctx.incoming_data.get("shop_integration_id") or "").strip()
    if not shop_integration_id:
        raise NotFound("Shopify shop integration not found.")

    result = await ctx.session.execute(
        select(ShopifyShopIntegration)
        .options(
            selectinload(ShopifyShopIntegration.created_by).load_only(User.client_id, User.username, User.profile_picture),
            selectinload(ShopifyShopIntegration.updated_by).load_only(User.client_id, User.username, User.profile_picture),
        )
        .where(
            ShopifyShopIntegration.workspace_id == ctx.workspace_id,
            ShopifyShopIntegration.client_id == shop_integration_id,
            ShopifyShopIntegration.is_deleted.is_(False),
        )
    )
    integration = result.scalar_one_or_none()
    if integration is None:
        raise NotFound("Shopify shop integration not found.")

    subscriptions = (
        await ctx.session.execute(
            select(ShopifyWebhookSubscription).where(
                ShopifyWebhookSubscription.workspace_id == ctx.workspace_id,
                ShopifyWebhookSubscription.shop_integration_id == integration.client_id,
            )
        )
    ).scalars().all()

    summary = {
        "total": len(subscriptions),
        "active": sum(1 for row in subscriptions if row.status.value == "active"),
        "failed": sum(1 for row in subscriptions if row.status.value == "failed"),
        "pending": sum(1 for row in subscriptions if row.status.value == "pending"),
        "disabled": sum(1 for row in subscriptions if row.status.value == "disabled"),
        "removed": sum(1 for row in subscriptions if row.status.value == "removed"),
    }
    return {
        "shop_integration": asdict(serialize_shopify_shop_integration(integration, subscriptions)),
        "webhook_subscription_summary": summary,
        "webhook_subscriptions": [asdict(serialize_shopify_webhook_subscription(row)) for row in subscriptions],
    }