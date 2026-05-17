"""Update and delete commands for ItemUpholstery."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.services.commands.items.requests import (
    parse_update_item_upholstery_request,
    parse_delete_item_upholstery_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def update_item_upholstery(ctx: ServiceContext) -> dict:
    """Update ItemUpholstery fields."""
    request = parse_update_item_upholstery_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(ItemUpholstery).where(
                ItemUpholstery.workspace_id == ctx.workspace_id,
                ItemUpholstery.client_id == request.client_id,
                ItemUpholstery.is_deleted.is_(False),
            )
        )
        iup = result.scalar_one_or_none()
        if iup is None:
            raise NotFound("ItemUpholstery not found.")

        if request.name is not None:
            iup.name = request.name
        if request.code is not None:
            iup.code = request.code
        if request.amount_meters is not None:
            iup.amount_meters = request.amount_meters
        if request.time_to_fix_in_seconds is not None:
            iup.time_to_fix_in_seconds = request.time_to_fix_in_seconds

        iup.updated_at = datetime.now(timezone.utc)
        iup.updated_by_id = ctx.user_id

    return {}


async def delete_item_upholstery(ctx: ServiceContext) -> dict:
    """Soft delete an ItemUpholstery."""
    request = parse_delete_item_upholstery_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(ItemUpholstery).where(
                ItemUpholstery.workspace_id == ctx.workspace_id,
                ItemUpholstery.client_id == request.client_id,
                ItemUpholstery.is_deleted.is_(False),
            )
        )
        iup = result.scalar_one_or_none()
        if iup is None:
            raise NotFound("ItemUpholstery not found.")

        iup.is_deleted = True
        iup.deleted_at = datetime.now(timezone.utc)
        iup.deleted_by_id = ctx.user_id

    return {}
