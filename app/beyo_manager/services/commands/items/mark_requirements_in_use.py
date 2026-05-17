"""CMD-2: Mark available requirements as in-use."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.commands.items.requests import parse_mark_in_use_request
from beyo_manager.services.commands.upholstery._inventory_mutations import consume_to_in_use
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def mark_requirements_in_use(ctx: ServiceContext) -> dict:
    """Mark all AVAILABLE requirements as IN_USE."""
    request = parse_mark_in_use_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.item_upholstery_id == request.item_upholstery_id,
                ItemUpholsteryRequirement.state == ItemUpholsteryRequirementStateEnum.AVAILABLE,
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        requirements = result.scalars().all()

        if not requirements:
            raise ValidationError(
                "No AVAILABLE requirements found for this item upholstery."
            )

        now = datetime.now(timezone.utc)
        for req in requirements:
            if req.upholstery_inventory_id is not None:
                await consume_to_in_use(
                    session=ctx.session,
                    workspace_id=ctx.workspace_id,
                    upholstery_inventory_id=req.upholstery_inventory_id,
                    quantity=req.amount_meters,
                )
            req.state = ItemUpholsteryRequirementStateEnum.IN_USE
            req.in_use_at = now
            req.updated_by_id = ctx.user_id

    return {}
