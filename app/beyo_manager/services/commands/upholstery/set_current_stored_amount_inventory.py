from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.upholstery.enums import InventoryMovementTriggerEnum
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.upholstery._inventory_history import (
    InventoryMovementContext,
    RequirementStateTracker,
    allocation_details,
    record_requirement_transitions,
)
from beyo_manager.services.commands.upholstery._inventory_mutations import (
    load_inventory_for_update,
    set_stored_amount,
)
from beyo_manager.services.commands.upholstery._pooled_requirement_allocation import (
    allocate_pooled_requirements,
    demotion_sort_key as _demotion_sort_key,
    calculate_pooled_requirement_pool,
    fetch_earliest_ready_by_at,
)
from beyo_manager.services.commands.upholstery.requests import (
    parse_set_current_stored_amount_inventory_request,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


async def set_current_stored_amount_inventory(ctx: ServiceContext) -> dict:
    request = parse_set_current_stored_amount_inventory_request(ctx.incoming_data)

    promoted_ids: list[str] = []
    demoted_ids: list[str] = []

    async with ctx.session.begin():
        inventory = await load_inventory_for_update(
            ctx.session, ctx.workspace_id, request.client_id
        )

        if request.current_stored_amount_meters == inventory.current_stored_amount_meters:
            return {}

        movement = InventoryMovementContext.from_service(
            ctx, InventoryMovementTriggerEnum.MANUAL_STORED_SET
        )
        stored_record = await set_stored_amount(
            ctx.session,
            inventory,
            request.current_stored_amount_meters,
            movement=movement,
        )

        available_candidates = await _load_requirement_candidates(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            inventory_id=inventory.client_id,
            states=[ItemUpholsteryRequirementStateEnum.AVAILABLE],
        )
        forward_seed_candidates = await _load_requirement_candidates(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            inventory_id=inventory.client_id,
            states=[
                ItemUpholsteryRequirementStateEnum.ORDERED,
                ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
            ],
        )
        ready_by_at_map = await fetch_earliest_ready_by_at(
            ctx.session,
            ctx.workspace_id,
            list(
                {
                    req.item_upholstery_id
                    for req in available_candidates + forward_seed_candidates
                }
            ),
        )

        # Diff requirement states across demotion + promotion; a requirement demoted and then
        # re-promoted in this same command nets to "no change" and records no child row.
        tracker = RequirementStateTracker.capture(available_candidates + forward_seed_candidates)

        demoted_ids = _demote_available_requirements(
            candidates=available_candidates,
            new_stored_amount_meters=request.current_stored_amount_meters,
            ready_by_at_map=ready_by_at_map,
            actor_id=ctx.user_id,
        )
        await ctx.session.flush()

        forward_candidates = await _load_requirement_candidates(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            inventory_id=inventory.client_id,
            states=[
                ItemUpholsteryRequirementStateEnum.ORDERED,
                ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
            ],
        )
        promoted_ids = _promote_forward_requirements(
            inventory=inventory,
            candidates=forward_candidates,
            ready_by_at_map=ready_by_at_map,
            actor_id=ctx.user_id,
        )

        touched = list(available_candidates) + list(forward_seed_candidates) + list(forward_candidates)
        await record_requirement_transitions(
            ctx.session,
            parent=stored_record,
            transitions=tracker.transitions(touched),
            movement=movement,
        )
        stored_record.details = allocation_details(
            pool_meters=calculate_pooled_requirement_pool(inventory, list(forward_candidates), "stored"),
            resolved=[
                r for r in forward_candidates
                if r.state == ItemUpholsteryRequirementStateEnum.AVAILABLE
            ],
            unresolved=[
                r for r in forward_candidates
                if r.state != ItemUpholsteryRequirementStateEnum.AVAILABLE
            ],
            target_state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
        )

        now = datetime.now(timezone.utc)
        inventory.updated_at = now
        inventory.updated_by_id = ctx.user_id

    pending_events = []
    if promoted_ids:
        pending_events.append(
            WorkspaceEvent(
                event_name="item:upholstery-requirement-state-changed",
                client_id="",
                workspace_id=ctx.workspace_id,
                extra={
                    "ids": promoted_ids,
                    "new_state": ItemUpholsteryRequirementStateEnum.AVAILABLE.value,
                },
            )
        )
    if demoted_ids:
        pending_events.append(
            WorkspaceEvent(
                event_name="item:upholstery-requirement-state-changed",
                client_id="",
                workspace_id=ctx.workspace_id,
                extra={
                    "ids": demoted_ids,
                    "new_state": ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING.value,
                },
            )
        )
    if pending_events:
        await event_bus.dispatch(pending_events)

    return {}


async def _load_requirement_candidates(
    *,
    session: AsyncSession,
    workspace_id: str,
    inventory_id: str,
    states: list[ItemUpholsteryRequirementStateEnum],
) -> list[ItemUpholsteryRequirement]:
    result = await session.execute(
        select(ItemUpholsteryRequirement).where(
            ItemUpholsteryRequirement.workspace_id == workspace_id,
            ItemUpholsteryRequirement.upholstery_inventory_id == inventory_id,
            ItemUpholsteryRequirement.state.in_(states),
            ItemUpholsteryRequirement.is_deleted.is_(False),
        )
    )
    return result.scalars().all()


def _demote_available_requirements(
    *,
    candidates: list[ItemUpholsteryRequirement],
    new_stored_amount_meters: Decimal,
    ready_by_at_map: dict[str, datetime | None],
    actor_id: str,
) -> list[str]:
    sum_available = sum((req.amount_meters or Decimal("0")) for req in candidates)
    deficit = max(Decimal("0"), sum_available - new_stored_amount_meters)
    if deficit == Decimal("0"):
        return []

    now = datetime.now(timezone.utc)
    demoted_ids: list[str] = []
    sum_demoted = Decimal("0")

    for req in sorted(candidates, key=lambda candidate: _demotion_sort_key(candidate, ready_by_at_map)):
        req.state = ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
        req.updated_at = now
        req.updated_by_id = actor_id
        demoted_ids.append(req.item_upholstery_id)
        sum_demoted += req.amount_meters or Decimal("0")
        if sum_demoted >= deficit:
            break

    return demoted_ids


def _promote_forward_requirements(
    *,
    inventory: UpholsteryInventory,
    candidates: list[ItemUpholsteryRequirement],
    ready_by_at_map: dict[str, datetime | None],
    actor_id: str,
) -> list[str]:
    if not candidates:
        return []

    tier_a = sorted(
        [
            req
            for req in candidates
            if req.state == ItemUpholsteryRequirementStateEnum.ORDERED
        ],
        key=lambda req: (
            ready_by_at_map.get(req.item_upholstery_id) is None,
            ready_by_at_map.get(req.item_upholstery_id),
            req.created_at,
        ),
    )
    tier_b = sorted(
        [
            req
            for req in candidates
            if req.state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
        ],
        key=lambda req: (
            ready_by_at_map.get(req.item_upholstery_id) is None,
            ready_by_at_map.get(req.item_upholstery_id),
            req.created_at,
        ),
    )
    ordered_candidates = tier_a + tier_b

    promoted_ids = allocate_pooled_requirements(
        inventory=inventory,
        ordered_candidates=ordered_candidates,
        target_state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
        mode="stored",
        actor_id=actor_id,
        timestamp_field=None,
    )
    if not promoted_ids:
        return []

    now = datetime.now(timezone.utc)
    promoted_set = set(promoted_ids)
    for req in ordered_candidates:
        if req.item_upholstery_id in promoted_set:
            req.updated_at = now

    return promoted_ids
