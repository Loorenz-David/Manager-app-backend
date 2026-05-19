"""CMD-5: Resolve requirements after stock arrival."""

from dataclasses import asdict
from decimal import Decimal

from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.items._allocation_algorithm import run_skip_and_continue_allocation
from beyo_manager.services.commands.items._notification_helpers import _resolve_upholstery_audience
from beyo_manager.services.commands.items.requests import parse_resolve_after_stock_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
from beyo_manager.services.infra.execution.task_factory import create_instant_task


async def resolve_requirements_after_stock(ctx: ServiceContext) -> dict:
    """Re-allocate ORDERED/NEEDS_ORDERING after stock arrival."""
    request = parse_resolve_after_stock_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        # Load inventory for condition calculation
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

        # Load all ORDERED and NEEDS_ORDERING candidates for this inventory
        req_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.upholstery_inventory_id == inv.client_id,
                ItemUpholsteryRequirement.state.in_([
                    ItemUpholsteryRequirementStateEnum.ORDERED,
                    ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
                ]),
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        candidates = req_result.scalars().all()

        if not candidates:
            return {"resolved": [], "unresolved": []}

        # Calculate available pool: stored - (in_need excluding candidates)
        total_candidate_need = sum(
            (r.amount_meters or Decimal("0")) for r in candidates
        )
        stored = inv.current_stored_amount_meters or Decimal("0")
        in_need = inv.current_amount_in_need_meters or Decimal("0")
        running_pool = stored - (in_need - total_candidate_need)

        # Three-tier sort
        priority_set = set(request.priority_item_upholstery_ids)
        priority_order = {iid: idx for idx, iid in enumerate(request.priority_item_upholstery_ids)}

        tier1 = sorted(
            [r for r in candidates if r.item_upholstery_id in priority_set],
            key=lambda r: priority_order.get(r.item_upholstery_id, 9999),
        )
        tier2 = sorted(
            [r for r in candidates if r.item_upholstery_id not in priority_set
             and r.state == ItemUpholsteryRequirementStateEnum.ORDERED],
            key=lambda r: r.ordered_at or r.created_at,
        )
        tier3 = sorted(
            [r for r in candidates if r.item_upholstery_id not in priority_set
             and r.state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING],
            key=lambda r: r.created_at,
        )
        ordered_candidates = tier1 + tier2 + tier3

        result_dict = run_skip_and_continue_allocation(
            candidates=ordered_candidates,
            running_pool=running_pool,
            target_state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
            timestamp_field=None,
        )

        modified_ids = set(result_dict["resolved"])
        for req in ordered_candidates:
            if req.item_upholstery_id in modified_ids:
                req.updated_by_id = ctx.user_id

        resolved_ids_for_notif = result_dict["resolved"]
        if resolved_ids_for_notif:
            target_user_ids = await _resolve_upholstery_audience(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                item_upholstery_ids=resolved_ids_for_notif,
                actor_id=ctx.user_id,
            )
            if target_user_ids:
                await create_instant_task(
                    session=ctx.session,
                    task_type=TaskType.CREATE_NOTIFICATIONS,
                    payload=asdict(NotificationPayload(
                        notification_type="upholstery_requirement_resolved",
                        user_ids=target_user_ids,
                        title="Requirements resolved",
                        body="Upholstery requirements have been resolved from stock.",
                        entity_type=None,
                        entity_client_id=None,
                        exclude_viewing=[],
                    )),
                )

    resolved_ids = result_dict["resolved"]
    if resolved_ids:
        await event_bus.dispatch([
            WorkspaceEvent(
                event_name="item:upholstery-requirement-state-changed",
                client_id="",
                workspace_id=ctx.workspace_id,
                extra={"ids": resolved_ids, "new_state": ItemUpholsteryRequirementStateEnum.AVAILABLE.value},
            ),
        ])
    return {"resolved": result_dict["resolved"], "unresolved": result_dict["unresolved"]}
