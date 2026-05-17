"""CMD-4: Soft-delete an Item."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.services.commands.items.requests import parse_delete_item_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def delete_item(ctx: ServiceContext) -> dict:
    """Soft-delete an Item. Does not cascade to issues or upholstery rows."""
    request = parse_delete_item_request(ctx.incoming_data)

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

        item.is_deleted = True
        item.deleted_at = datetime.now(timezone.utc)
        item.deleted_by_id = ctx.user_id

    return {}
