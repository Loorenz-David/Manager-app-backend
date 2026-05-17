"""CMD-8/9: Complete single requirement and reallocate stock."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.commands.items.requests import (
    parse_complete_single_requirement_request,
    parse_reallocate_stock_request,
)
from beyo_manager.services.commands.upholstery._inventory_mutations import finish_in_use
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def complete_single_requirement(ctx: ServiceContext) -> dict:
    """Complete a single IN_USE requirement independently."""
    request = parse_complete_single_requirement_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        req_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.client_id == request.client_id,
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        req = req_result.scalar_one_or_none()
        if req is None:
            raise NotFound("ItemUpholsteryRequirement not found.")

        if req.state != ItemUpholsteryRequirementStateEnum.IN_USE:
            raise ValidationError(
                "Only IN_USE requirements can be completed individually."
            )

        if req.upholstery_inventory_id is not None:
            await finish_in_use(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                upholstery_inventory_id=req.upholstery_inventory_id,
                quantity=req.amount_meters,
                source=req.source,
            )

        req.state = ItemUpholsteryRequirementStateEnum.COMPLETED
        req.completed_at = datetime.now(timezone.utc)
        req.updated_by_id = ctx.user_id

    return {}


async def reallocate_stock(ctx: ServiceContext) -> dict:
    """Move donors from AVAILABLE and reallocate to NEEDS_ORDERING."""
    request = parse_reallocate_stock_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        # Load inventory
        from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
        inv_result = await ctx.session.execute(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.upholstery_id == request.upholstery_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        inv = inv_result.scalar_one_or_none()
        if inv is None:
            raise NotFound("UpholsteryInventory not found.")

        # Load donors (AVAILABLE requirements)
        donor_set = set(request.donor_item_upholstery_ids)
        donor_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.upholstery_inventory_id == inv.client_id,
                ItemUpholsteryRequirement.state == ItemUpholsteryRequirementStateEnum.AVAILABLE,
                ItemUpholsteryRequirement.item_upholstery_id.in_(list(donor_set)),
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        donors = donor_result.scalars().all()

        # Mark donors as NEEDS_ORDERING
        now = datetime.now(timezone.utc)
        for donor in donors:
            donor.state = ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
            donor.updated_by_id = ctx.user_id

        # Load all current NEEDS_ORDERING
        needs_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.upholstery_inventory_id == inv.client_id,
                ItemUpholsteryRequirement.state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        all_needs = needs_result.scalars().all()

        # Calculate pool: donors' amounts
        from decimal import Decimal
        pool = Decimal("0")
        for donor in donors:
            pool += donor.amount_meters or Decimal("0")

        if pool <= Decimal("0"):
            return {"allocated": [], "unallocated": []}

        # Sort: priority + oldest
        priority_set = set(request.priority_item_upholstery_ids)
        priority_order = {iid: idx for idx, iid in enumerate(request.priority_item_upholstery_ids)}

        tier1 = sorted(
            [r for r in all_needs if r.item_upholstery_id in priority_set],
            key=lambda r: priority_order.get(r.item_upholstery_id, 9999),
        )
        tier2 = sorted(
            [r for r in all_needs if r.item_upholstery_id not in priority_set],
            key=lambda r: r.created_at,
        )
        ordered_candidates = tier1 + tier2

        # Allocate via skip-and-continue
        from beyo_manager.services.commands.items._allocation_algorithm import run_skip_and_continue_allocation
        result_dict = run_skip_and_continue_allocation(
            candidates=ordered_candidates,
            running_pool=pool,
            target_state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
            timestamp_field=None,
        )

        modified_ids = set(result_dict["resolved"])
        for req in ordered_candidates:
            if req.item_upholstery_id in modified_ids:
                req.updated_by_id = ctx.user_id

    return {"allocated": result_dict["resolved"], "unallocated": result_dict["unresolved"]}
