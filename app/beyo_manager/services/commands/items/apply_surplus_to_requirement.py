"""CMD-6: Apply surplus material to a requirement."""

from sqlalchemy import select

from beyo_manager.domain.items.enums import (
    ItemUpholsteryRequirementSourceEnum,
    ItemUpholsteryRequirementStateEnum,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.commands.items.requests import parse_apply_surplus_request
from beyo_manager.services.commands.items.update_and_delete_item_upholstery import (
    ensure_requirement_actions_are_available,
)
from beyo_manager.services.commands.upholstery._inventory_mutations import add_stored_surplus
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext

_ALLOWED_STATES = {
    ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
    ItemUpholsteryRequirementStateEnum.ORDERED,
}


async def apply_surplus_to_requirement(ctx: ServiceContext) -> dict:
    """Apply offcut material to NEEDS_ORDERING/ORDERED requirement."""
    request = parse_apply_surplus_request(ctx.incoming_data)

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
        ensure_requirement_actions_are_available(iup)

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

        if active_req.state not in _ALLOWED_STATES:
            raise ValidationError(
                "Surplus can only be applied to NEEDS_ORDERING or ORDERED requirements."
            )

        from decimal import Decimal
        if request.surplus_amount_meters > (active_req.amount_meters or Decimal("0")):
            raise ValidationError(
                "Surplus amount cannot exceed requirement amount_meters."
            )

        await add_stored_surplus(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            upholstery_inventory_id=active_req.upholstery_inventory_id,
            quantity=request.surplus_amount_meters,
        )

        if request.surplus_amount_meters == active_req.amount_meters:
            # Case A: full cover
            active_req.source = ItemUpholsteryRequirementSourceEnum.SURPLUS
            active_req.state = ItemUpholsteryRequirementStateEnum.AVAILABLE
            active_req.updated_by_id = ctx.user_id
        else:
            # Case B: partial - create SURPLUS requirement
            surplus_req = ItemUpholsteryRequirement(
                workspace_id=ctx.workspace_id,
                item_upholstery_id=iup.client_id,
                upholstery_inventory_id=active_req.upholstery_inventory_id,
                amount_meters=request.surplus_amount_meters,
                source=ItemUpholsteryRequirementSourceEnum.SURPLUS,
                state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
                created_by_id=ctx.user_id,
            )
            ctx.session.add(surplus_req)

            active_req.amount_meters = (active_req.amount_meters or Decimal("0")) - request.surplus_amount_meters
            active_req.updated_by_id = ctx.user_id

    return {}
