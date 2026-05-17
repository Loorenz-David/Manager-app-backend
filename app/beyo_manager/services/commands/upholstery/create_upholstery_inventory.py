"""Create upholstery inventory command."""

from decimal import Decimal

from sqlalchemy import select

from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.upholstery.requests import parse_create_upholstery_inventory_request
from beyo_manager.services.context import ServiceContext


async def create_upholstery_inventory(ctx: ServiceContext) -> dict:
    """Create a new upholstery inventory record for the workspace."""
    request = parse_create_upholstery_inventory_request(ctx.incoming_data)

    async with ctx.session.begin():
        existing = await ctx.session.execute(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.upholstery_id == request.upholstery_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError(
                "An inventory record already exists for this upholstery in this workspace."
            )

        inv = UpholsteryInventory(
            workspace_id=ctx.workspace_id,
            upholstery_id=request.upholstery_id,
            inventory_condition=UpholsteryInventoryConditionEnum.AVAILABLE,
            current_stored_amount_meters=Decimal("0"),
            current_amount_in_need_meters=Decimal("0"),
            current_amount_in_use_meters=Decimal("0"),
            current_amount_ordered_meters=Decimal("0"),
            total_upholstery_used_meters=Decimal("0"),
            total_upholstery_used_inventory_meters=Decimal("0"),
            total_upholstery_used_surplus_meters=Decimal("0"),
            total_upholstery_surplus_meters=Decimal("0"),
            low_stock_threshold_meters=request.low_stock_threshold_meters,
            minimum_to_have=request.minimum_to_have,
            maximum_to_have=request.maximum_to_have,
            projected_inventory_value_minor=request.projected_inventory_value_minor,
            currency=request.currency,
            planning_position=request.planning_position,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(inv)

    return {"client_id": inv.client_id}
