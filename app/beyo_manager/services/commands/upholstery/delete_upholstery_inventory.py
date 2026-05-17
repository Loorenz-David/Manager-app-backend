"""Delete upholstery inventory command (soft delete)."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.upholstery.requests import parse_delete_upholstery_inventory_request
from beyo_manager.services.context import ServiceContext


async def delete_upholstery_inventory(ctx: ServiceContext) -> dict:
    """Soft delete an upholstery inventory record."""
    request = parse_delete_upholstery_inventory_request(ctx.incoming_data)

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.client_id == request.client_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        inv = result.scalar_one_or_none()
        if inv is None:
            raise NotFound("UpholsteryInventory not found.")

        inv.is_deleted = True
        inv.deleted_at = datetime.now(timezone.utc)
        inv.deleted_by_id = ctx.user_id

    return {}
