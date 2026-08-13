from __future__ import annotations

from sqlalchemy import select

from beyo_manager.domain.item_economics.serializers import serialize_item_valuation
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.items.item import Item
from beyo_manager.services.context import ServiceContext


async def get_item_valuation_history(ctx: ServiceContext) -> dict:
    item_id = ctx.incoming_data.get("item_client_id")
    item = await ctx.session.scalar(
        select(Item).where(
            Item.workspace_id == ctx.workspace_id,
            Item.client_id == item_id,
            Item.is_deleted.is_(False),
        )
    )
    if item is None:
        raise NotFound("Item not found.")
    result = await ctx.session.execute(
        select(ItemValuation)
        .where(
            ItemValuation.workspace_id == ctx.workspace_id,
            ItemValuation.item_id == item.client_id,
            ItemValuation.is_deleted.is_(False),
        )
        .order_by(ItemValuation.created_at.desc(), ItemValuation.client_id.desc())
    )
    rows = result.scalars().all()
    return {"item_valuations": [serialize_item_valuation(row) for row in rows]}
