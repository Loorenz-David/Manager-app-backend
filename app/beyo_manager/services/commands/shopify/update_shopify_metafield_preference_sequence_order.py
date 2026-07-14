from __future__ import annotations

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.shopify.shopify_metafield_preference import (
    ShopifyMetafieldPreference,
)
from beyo_manager.services.commands.shopify.requests.update_shopify_metafield_preference_sequence_order_request import (
    parse_update_shopify_metafield_preference_sequence_order_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def update_shopify_metafield_preference_sequence_order(
    ctx: ServiceContext,
) -> dict:
    request = parse_update_shopify_metafield_preference_sequence_order_request(
        ctx.incoming_data
    )

    async with maybe_begin(ctx.session):
        preference = await ctx.session.scalar(
            select(ShopifyMetafieldPreference)
            .where(
                ShopifyMetafieldPreference.workspace_id == ctx.workspace_id,
                ShopifyMetafieldPreference.client_id == request.client_id,
                ShopifyMetafieldPreference.is_deleted.is_(False),
            )
            .with_for_update()
        )
        if preference is None:
            raise NotFound("Shopify metafield preference not found.")

        old_sequence_order = preference.sequence_order
        new_sequence_order = request.sequence_order
        if old_sequence_order != new_sequence_order:
            affected_query = select(ShopifyMetafieldPreference).where(
                ShopifyMetafieldPreference.workspace_id == ctx.workspace_id,
                ShopifyMetafieldPreference.shop_integration_id
                == preference.shop_integration_id,
                ShopifyMetafieldPreference.item_category_id
                == preference.item_category_id,
                ShopifyMetafieldPreference.client_id != preference.client_id,
                ShopifyMetafieldPreference.is_deleted.is_(False),
                ShopifyMetafieldPreference.is_enabled.is_(True),
            )
            if new_sequence_order > old_sequence_order:
                affected_query = affected_query.where(
                    ShopifyMetafieldPreference.sequence_order > old_sequence_order,
                    ShopifyMetafieldPreference.sequence_order <= new_sequence_order,
                )
                shift = -1
            else:
                affected_query = affected_query.where(
                    ShopifyMetafieldPreference.sequence_order >= new_sequence_order,
                    ShopifyMetafieldPreference.sequence_order < old_sequence_order,
                )
                shift = 1

            affected_result = await ctx.session.execute(
                affected_query.order_by(
                    ShopifyMetafieldPreference.sequence_order,
                    ShopifyMetafieldPreference.client_id,
                ).with_for_update()
            )
            affected_preferences = affected_result.scalars().all()
            for affected_preference in affected_preferences:
                affected_preference.sequence_order += shift
                affected_preference.updated_by_id = ctx.user_id

            preference.sequence_order = request.sequence_order
            preference.updated_by_id = ctx.user_id
            await ctx.session.flush()

    return {
        "client_id": preference.client_id,
        "sequence_order": preference.sequence_order,
    }
