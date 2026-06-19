"""Update upholstery inventory command."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.upholstery.requests import parse_update_upholstery_inventory_request
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


async def update_upholstery_inventory(ctx: ServiceContext) -> dict:
    """Update upholstery inventory record fields."""
    request = parse_update_upholstery_inventory_request(ctx.incoming_data)

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

        if request.low_stock_threshold_meters is not None:
            inv.low_stock_threshold_meters = request.low_stock_threshold_meters
        if request.minimum_to_have is not None:
            inv.minimum_to_have = request.minimum_to_have
        if request.maximum_to_have is not None:
            inv.maximum_to_have = request.maximum_to_have
        if request.projected_inventory_value_minor is not None:
            inv.projected_inventory_value_minor = request.projected_inventory_value_minor
        if request.currency is not None:
            inv.currency = request.currency
        if request.planning_position is not None:
            inv.planning_position = request.planning_position

        inv.updated_at = datetime.now(timezone.utc)
        inv.updated_by_id = ctx.user_id

    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="upholstery:inventory-updated",
            client_id=inv.client_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ])
    return {}
