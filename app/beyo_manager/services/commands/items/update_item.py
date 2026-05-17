"""CMD-3: Update Item fields - null vs omit via model_fields_set."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.services.commands.items.requests import parse_update_item_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


_DIRECT_FIELDS = {
    "article_number",
    "sku",
    "quantity",
    "designer",
    "height_in_cm",
    "width_in_cm",
    "depth_in_cm",
    "item_value_minor",
    "item_cost_minor",
    "item_currency",
    "item_position",
    "external_id",
    "external_url",
    "external_source",
    "external_order_id",
}


async def update_item(ctx: ServiceContext) -> dict:
    """Update Item - only fields present in the request payload are written."""
    request = parse_update_item_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id == request.client_id,
                Item.is_deleted.is_(False),
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFound("Item not found.")

        for field_name in _DIRECT_FIELDS:
            if field_name in request.model_fields_set:
                setattr(item, field_name, getattr(request, field_name))

        if "item_category_id" in request.model_fields_set:
            item.item_category_id = request.item_category_id
            if request.item_category_id is None:
                item.item_category_snapshot = None
                item.item_major_category_snapshot = None
            else:
                category_result = await ctx.session.execute(
                    select(ItemCategory).where(
                        ItemCategory.workspace_id == ctx.workspace_id,
                        ItemCategory.client_id == request.item_category_id,
                        ItemCategory.is_deleted.is_(False),
                    )
                )
                category = category_result.scalar_one_or_none()
                if category is None:
                    raise NotFound("ItemCategory not found.")
                item.item_category_snapshot = category.name
                item.item_major_category_snapshot = category.major_category.value

        item.updated_at = datetime.now(timezone.utc)
        item.updated_by_id = ctx.user_id

    return {"client_id": item.client_id}
