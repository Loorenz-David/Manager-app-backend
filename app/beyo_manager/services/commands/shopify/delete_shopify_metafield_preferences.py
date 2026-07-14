from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.shopify.shopify_metafield_preference import ShopifyMetafieldPreference
from beyo_manager.services.commands.shopify.requests.delete_shopify_metafield_preferences_request import (
    parse_delete_shopify_metafield_preferences_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def delete_shopify_metafield_preferences(ctx: ServiceContext) -> dict:
    request = parse_delete_shopify_metafield_preferences_request(ctx.incoming_data)
    requested_ids = set(request.client_ids)
    now = datetime.now(timezone.utc)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(ShopifyMetafieldPreference).where(
                ShopifyMetafieldPreference.workspace_id == ctx.workspace_id,
                ShopifyMetafieldPreference.client_id.in_(requested_ids),
                ShopifyMetafieldPreference.is_deleted.is_(False),
            )
        )
        preferences = result.scalars().all()
        found_ids = {preference.client_id for preference in preferences}
        if found_ids != requested_ids:
            missing_ids = sorted(requested_ids - found_ids)
            raise NotFound(
                f"Shopify metafield preference(s) not found: {', '.join(missing_ids)}"
            )

        for preference in preferences:
            preference.is_deleted = True
            preference.deleted_at = now
            preference.deleted_by_id = ctx.user_id

    return {}
