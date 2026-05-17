"""Confirm ordered to stock command."""

from datetime import datetime, timezone

from beyo_manager.services.commands.upholstery.requests import parse_confirm_ordered_request
from beyo_manager.services.commands.upholstery._inventory_mutations import confirm_ordered_to_stock
from beyo_manager.services.context import ServiceContext


async def confirm_ordered_to_stock_inventory(ctx: ServiceContext) -> dict:
    """Confirm ordered quantity as received stock."""
    request = parse_confirm_ordered_request(ctx.incoming_data)

    async with ctx.session.begin():
        await confirm_ordered_to_stock(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            upholstery_inventory_id=request.client_id,
            quantity=request.quantity,
        )

    return {}
