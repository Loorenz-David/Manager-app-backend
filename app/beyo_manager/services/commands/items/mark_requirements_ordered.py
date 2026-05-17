"""CMD-4: Mark NEEDS_ORDERING requirements as ORDERED via pool allocation."""

from decimal import Decimal

from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.items._allocation_algorithm import run_skip_and_continue_allocation
from beyo_manager.services.commands.items.requests import parse_mark_ordered_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def mark_requirements_ordered(ctx: ServiceContext) -> dict:
    """Allocate ordered_quantity to NEEDS_ORDERING requirements with priority."""
    request = parse_mark_ordered_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        # Get valid inventory IDs for upholstery
        inv_result = await ctx.session.execute(
            select(UpholsteryInventory.client_id).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.upholstery_id == request.upholstery_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        valid_inventory_ids = set(inv_result.scalars().all())

        # Load all NEEDS_ORDERING requirements for this upholstery
        req_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        all_candidates = req_result.scalars().all()

        # Filter to upholstery inventory IDs
        candidates = [r for r in all_candidates if r.upholstery_inventory_id in valid_inventory_ids]

        # Sort: priority first, then oldest
        priority_set = set(request.priority_item_upholstery_ids)
        priority_order = {iid: idx for idx, iid in enumerate(request.priority_item_upholstery_ids)}

        tier1 = sorted(
            [r for r in candidates if r.item_upholstery_id in priority_set],
            key=lambda r: priority_order.get(r.item_upholstery_id, 9999),
        )
        tier2 = sorted(
            [r for r in candidates if r.item_upholstery_id not in priority_set],
            key=lambda r: r.created_at,
        )
        ordered_candidates = tier1 + tier2

        result_dict = run_skip_and_continue_allocation(
            candidates=ordered_candidates,
            running_pool=request.ordered_quantity,
            target_state=ItemUpholsteryRequirementStateEnum.ORDERED,
            timestamp_field="ordered_at",
        )

        modified_ids = set(result_dict["resolved"])
        for req in ordered_candidates:
            if req.item_upholstery_id in modified_ids:
                req.updated_by_id = ctx.user_id

    return {"ordered": result_dict["resolved"], "unordered": result_dict["unresolved"]}
