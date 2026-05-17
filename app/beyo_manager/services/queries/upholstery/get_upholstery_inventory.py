"""Query for getting a single upholstery inventory."""

from sqlalchemy import select

from beyo_manager.domain.upholstery.serializers import serialize_upholstery_inventory
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.context import ServiceContext


async def get_upholstery_inventory(ctx: ServiceContext) -> dict:
    """Get a single upholstery inventory by client_id."""
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(UpholsteryInventory).where(
            UpholsteryInventory.workspace_id == ctx.workspace_id,
            UpholsteryInventory.client_id == client_id,
            UpholsteryInventory.is_deleted.is_(False),
        )
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        raise NotFound("UpholsteryInventory not found.")

    return {"inventory": serialize_upholstery_inventory(inv)}
