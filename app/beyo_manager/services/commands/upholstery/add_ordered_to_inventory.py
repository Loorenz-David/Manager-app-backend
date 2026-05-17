"""Add ordered quantity command."""

from datetime import datetime, timezone

from beyo_manager.services.commands.upholstery.requests import parse_add_ordered_request
from beyo_manager.services.commands.upholstery._inventory_mutations import add_ordered
from beyo_manager.services.context import ServiceContext


async def add_ordered_to_inventory(ctx: ServiceContext) -> dict:
    """Add ordered quantity to an upholstery inventory record."""
    request = parse_add_ordered_request(ctx.incoming_data)

    async with ctx.session.begin():
        await add_ordered(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            upholstery_inventory_id=request.client_id,
            quantity=request.quantity,
        )

    return {}
