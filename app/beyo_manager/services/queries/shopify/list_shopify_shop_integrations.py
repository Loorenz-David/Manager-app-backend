from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import load_only, selectinload

from beyo_manager.domain.shopify.serializers import serialize_shopify_shop_integration
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


def _parse_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


async def list_shopify_shop_integrations(ctx: ServiceContext) -> dict:
    limit = min(max(_parse_int(ctx.query_params.get("limit"), _DEFAULT_LIMIT), 0), _MAX_LIMIT)
    offset = max(_parse_int(ctx.query_params.get("offset"), 0), 0)

    result = await ctx.session.execute(
        select(ShopifyShopIntegration)
        .options(
            selectinload(ShopifyShopIntegration.created_by).load_only(User.client_id, User.username, User.profile_picture),
            selectinload(ShopifyShopIntegration.updated_by).load_only(User.client_id, User.username, User.profile_picture),
        )
        .where(
            ShopifyShopIntegration.workspace_id == ctx.workspace_id,
            ShopifyShopIntegration.is_deleted.is_(False),
        )
        .order_by(ShopifyShopIntegration.created_at.desc())
        .offset(offset)
        .limit(limit + 1)
    )
    rows = result.scalars().all()
    page = rows[:limit]
    return {
        "shops": [asdict(serialize_shopify_shop_integration(item)) for item in page],
        "shops_pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": len(rows) > limit,
        },
    }