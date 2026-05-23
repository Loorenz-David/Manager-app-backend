"""CMD: Set or update quantity on a mutable requirement."""

from decimal import Decimal

from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.commands.items.requests import (
    parse_update_requirement_quantity_request,
)
from beyo_manager.services.commands.upholstery._inventory_mutations import (
    adjust_need,
    check_and_inject_need,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext

_MUTABLE_STATES = {
    ItemUpholsteryRequirementStateEnum.MISSING_QUANTITY,
    ItemUpholsteryRequirementStateEnum.AVAILABLE,
    ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
}


async def update_requirement_quantity(ctx: ServiceContext) -> dict:
    """Set or update quantity on a mutable requirement."""
    request = parse_update_requirement_quantity_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        iup_result = await ctx.session.execute(
            select(ItemUpholstery).where(
                ItemUpholstery.workspace_id == ctx.workspace_id,
                ItemUpholstery.client_id == request.item_upholstery_id,
                ItemUpholstery.is_deleted.is_(False),
            )
        )
        iup = iup_result.scalar_one_or_none()
        if iup is None:
            raise NotFound("ItemUpholstery not found.")

        req_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.client_id == iup.active_requirement_id,
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        active_req = req_result.scalar_one_or_none()
        if active_req is None:
            raise NotFound("Active requirement not found.")

        if active_req.state not in _MUTABLE_STATES:
            raise ValidationError(
                "Quantity can only be set on requirements in MISSING_QUANTITY, AVAILABLE, or NEEDS_ORDERING state."
            )

        if active_req.state == ItemUpholsteryRequirementStateEnum.MISSING_QUANTITY:
            inv_result = await check_and_inject_need(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                upholstery_id=iup.upholstery_id,
                quantity=request.amount_meters,
                inject=True,
            )
            active_req.amount_meters = request.amount_meters
            active_req.upholstery_inventory_id = inv_result["inventory_id"]
            active_req.state = (
                ItemUpholsteryRequirementStateEnum.AVAILABLE
                if inv_result["sufficient"]
                else ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
            )
            active_req.updated_by_id = ctx.user_id

        else:
            if active_req.upholstery_inventory_id is None:
                raise ValidationError(
                    "Requirement has no linked inventory record - quantity cannot be adjusted."
                )

            old_amount = active_req.amount_meters or Decimal("0")
            delta = request.amount_meters - old_amount

            if delta == Decimal("0"):
                return {}

            inv_result = await adjust_need(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                upholstery_inventory_id=active_req.upholstery_inventory_id,
                delta=delta,
            )

            active_req.amount_meters = request.amount_meters
            active_req.state = (
                ItemUpholsteryRequirementStateEnum.AVAILABLE
                if inv_result["sufficient"]
                else ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
            )
            active_req.updated_by_id = ctx.user_id

    return {}
