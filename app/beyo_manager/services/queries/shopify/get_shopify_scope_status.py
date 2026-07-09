from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import select

from beyo_manager.domain.shopify.serializers import serialize_shopify_scope_status
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.services.context import ServiceContext


async def get_shopify_scope_status(ctx: ServiceContext) -> dict:
    shop_integration_id = str(ctx.query_params.get("shop_integration_id") or "").strip()
    query = select(ShopifyShopIntegration).where(
        ShopifyShopIntegration.workspace_id == ctx.workspace_id,
        ShopifyShopIntegration.is_deleted.is_(False),
    )
    if shop_integration_id:
        query = query.where(ShopifyShopIntegration.client_id == shop_integration_id)

    rows = (await ctx.session.execute(query.order_by(ShopifyShopIntegration.created_at.desc()))).scalars().all()
    if shop_integration_id and not rows:
        raise NotFound("Shopify shop integration not found.")

    return {
        "scope_statuses": [asdict(serialize_shopify_scope_status(row)) for row in rows],
    }