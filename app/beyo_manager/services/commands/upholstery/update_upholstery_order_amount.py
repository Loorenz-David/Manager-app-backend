"""Change the amount of an upholstery order that was already placed.

Plan: ``docs/architecture/under_construction/implementation/edit_upholstery_order_amount/
PLAN_edit_upholstery_order_amount_20261116.md`` (owner-approved 2026-11-16 with C1–C5 as
proposed).

``ordered`` requirements are pooled per inventory, not tied to an order, so an edit only
moves ``inventory.current_amount_ordered_meters`` by the delta and then restores the
allocation invariant the create path maintains::

    sum(ORDERED) <= stored + ordered - sum(AVAILABLE)

— the ordered-side twin of ``set_current_stored_amount_inventory``:

1. **demote** ``ordered -> needs_ordering``, latest due first (``demotion_sort_key``),
   until the invariant holds again (only possible after a decrease);
2. **re-promote** with the exact allocator ``create_upholstery_order`` uses
   (``allocate_needs_ordering_to_ordered``: earliest due first, skip-and-continue), so a
   decrease can still cover a smaller item and an increase covers new ones.

The deficit in step 1 is ``-calculate_pooled_requirement_pool(inventory, NEEDS_ORDERING,
"ordered")``: the same pool step 2 allocates from, so after demoting it is never negative.
Only *net* requirement transitions reach the ledger and the events (a requirement demoted
and re-promoted in one call nets to nothing).

Lock order: order row, then inventory row (``adjust_ordered``) — the same order
``receive_upholstery_order`` takes, so an edit and a receipt on one order serialise.
"""

from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.items.notification_targets import resolve_upholstery_notification_targets
from beyo_manager.domain.upholstery.enums import (
    InventoryMovementTriggerEnum,
    UpholsteryOrderStateEnum,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.models.tables.upholstery.upholstery_inventory_history_record import (
    UpholsteryInventoryHistoryRecord,
)
from beyo_manager.models.tables.upholstery.upholstery_order import UpholsteryOrder
from beyo_manager.models.tables.upholstery.upholstery_order_history_record import (
    UpholsteryOrderHistoryRecord,
)
from beyo_manager.services.commands.upholstery._inventory_history import (
    InventoryMovementContext,
    RequirementStateTracker,
    allocation_details,
    record_requirement_transitions,
)
from beyo_manager.services.commands.upholstery._inventory_mutations import (
    adjust_ordered,
    load_inventory_for_update,
)
from beyo_manager.services.commands.upholstery._pooled_requirement_allocation import (
    allocate_needs_ordering_to_ordered,
    calculate_pooled_requirement_pool,
    demotion_sort_key,
    fetch_earliest_ready_by_at,
)
from beyo_manager.services.commands.upholstery.requests import (
    parse_update_upholstery_order_amount_request,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
from beyo_manager.services.infra.execution.task_factory import create_instant_task

ORDERED = ItemUpholsteryRequirementStateEnum.ORDERED
NEEDS_ORDERING = ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
_ZERO = Decimal("0")

# Counted in inventory.current_amount_ordered_meters: an edit moves that bucket (C2).
COUNTED_ORDER_STATES = frozenset(
    {UpholsteryOrderStateEnum.ORDERED, UpholsteryOrderStateEnum.PARTIALLY_RECEIVED}
)
# Never counted in inventory: an edit changes only the field.
UNCOUNTED_ORDER_STATES = frozenset(
    {
        UpholsteryOrderStateEnum.DRAFT,
        UpholsteryOrderStateEnum.PENDING,
        UpholsteryOrderStateEnum.APPROVED,
    }
)
EDITABLE_ORDER_STATES = COUNTED_ORDER_STATES | UNCOUNTED_ORDER_STATES


async def update_upholstery_order_amount(ctx: ServiceContext) -> dict:
    request = parse_update_upholstery_order_amount_request(ctx.incoming_data)

    promoted_ids: list[str] = []
    demoted_ids: list[str] = []

    async with ctx.session.begin():
        order = (
            await ctx.session.execute(
                select(UpholsteryOrder)
                .where(
                    UpholsteryOrder.workspace_id == ctx.workspace_id,
                    UpholsteryOrder.client_id == request.client_id,
                    UpholsteryOrder.is_deleted.is_(False),
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if order is None:
            raise NotFound("Upholstery order not found.")
        if order.state not in EDITABLE_ORDER_STATES:
            raise ConflictError(
                f"This order is {order.state.value.replace('_', ' ')} and can no longer be changed."
            )

        new_amount = request.order_amount_meters
        received = order.received_amount_meters or _ZERO
        if new_amount < received:
            raise ValidationError(
                f"The ordered amount can't be less than the {received} m already received."
            )

        old_amount = order.order_amount_meters
        if new_amount == old_amount:
            return _payload(order)

        was_counted = order.state in COUNTED_ORDER_STATES
        now = datetime.now(timezone.utc)
        order.order_amount_meters = new_amount
        order.updated_at = now
        order.updated_by_id = ctx.user_id
        # C3: shrinking a partly received order to what already arrived closes it.
        if was_counted and received > _ZERO and new_amount == received:
            order.state = UpholsteryOrderStateEnum.RECEIVED
            order.received_at = order.received_at or now
        await ctx.session.flush()

        ctx.session.add(
            UpholsteryOrderHistoryRecord(
                workspace_id=ctx.workspace_id,
                upholstery_order_id=order.client_id,
                state=order.state,
                changed_at=now,
                snapshot_price_minor=order.price_minor,
                snapshot_currency=order.currency,
                snapshot_order_amount_meters=order.order_amount_meters,
                created_by_id=ctx.user_id,
            )
        )

        if was_counted and order.upholstery_inventory_id is not None:
            movement = InventoryMovementContext.from_service(
                ctx,
                InventoryMovementTriggerEnum.ORDER_AMOUNT_CHANGED,
                upholstery_order_id=order.client_id,
            )
            parent = await adjust_ordered(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                upholstery_inventory_id=order.upholstery_inventory_id,
                delta=new_amount - old_amount,
                movement=movement,
            )
            inventory = await load_inventory_for_update(
                ctx.session, ctx.workspace_id, order.upholstery_inventory_id
            )
            promoted_ids, demoted_ids = await reallocate_after_ordered_change(
                ctx.session,
                workspace_id=ctx.workspace_id,
                inventory=inventory,
                actor_id=ctx.user_id,
                parent=parent,
                movement=movement,
            )
            await _notify(ctx, promoted_ids, demoted_ids)

    events = [
        WorkspaceEvent(
            event_name="upholstery:order-updated",
            client_id=order.client_id,
            workspace_id=ctx.workspace_id,
            extra={
                "state": order.state.value,
                "order_amount_meters": float(order.order_amount_meters),
            },
        )
    ]
    for ids, state in ((promoted_ids, ORDERED), (demoted_ids, NEEDS_ORDERING)):
        if ids:
            events.append(
                WorkspaceEvent(
                    event_name="item:upholstery-requirement-state-changed",
                    client_id="",
                    workspace_id=ctx.workspace_id,
                    extra={"ids": ids, "new_state": state.value},
                )
            )
    await event_bus.dispatch(events)
    return _payload(order)


async def reallocate_after_ordered_change(
    session: AsyncSession,
    *,
    workspace_id: str,
    inventory: UpholsteryInventory,
    actor_id: str,
    parent: UpholsteryInventoryHistoryRecord,
    movement: InventoryMovementContext,
) -> tuple[list[str], list[str]]:
    """Demote then re-promote against the ordered pool. Returns the item upholstery ids
    whose requirement *net* moved to ``ordered`` / back to ``needs_ordering``."""
    ordered = await _load(session, workspace_id, inventory.client_id, ORDERED)
    needs = await _load(session, workspace_id, inventory.client_id, NEEDS_ORDERING)
    tracker = RequirementStateTracker.capture([*ordered, *needs])

    deficit = -calculate_pooled_requirement_pool(inventory, list(needs), "ordered")
    if deficit > _ZERO:
        ready_by_at_map = await fetch_earliest_ready_by_at(
            session, workspace_id, [req.item_upholstery_id for req in ordered]
        )
        now = datetime.now(timezone.utc)
        demoted_meters = _ZERO
        for req in sorted(ordered, key=lambda r: demotion_sort_key(r, ready_by_at_map)):
            if demoted_meters >= deficit:
                break
            req.state = NEEDS_ORDERING
            req.ordered_at = None
            req.updated_at = now
            req.updated_by_id = actor_id
            demoted_meters += req.amount_meters or _ZERO
        await session.flush()

    await allocate_needs_ordering_to_ordered(
        session=session,
        workspace_id=workspace_id,
        inventory=inventory,
        priority_item_upholstery_ids=[],  # C5: no picker on the edit sheet
        actor_id=actor_id,
    )
    await session.flush()

    touched = [*ordered, *needs]
    transitions = tracker.transitions(touched)
    await record_requirement_transitions(
        session, parent=parent, transitions=transitions, movement=movement
    )
    now_ordered = [req for req in touched if req.state == ORDERED]
    now_needs = [req for req in touched if req.state == NEEDS_ORDERING]
    parent.details = allocation_details(
        pool_meters=calculate_pooled_requirement_pool(inventory, now_needs, "ordered"),
        resolved=now_ordered,
        unresolved=now_needs,
        target_state=ORDERED,
    )

    promoted = sorted({t.requirement.item_upholstery_id for t in transitions if t.to_state == ORDERED})
    demoted = sorted(
        {t.requirement.item_upholstery_id for t in transitions if t.to_state == NEEDS_ORDERING}
    )
    return promoted, demoted


async def _load(
    session: AsyncSession,
    workspace_id: str,
    inventory_id: str,
    state: ItemUpholsteryRequirementStateEnum,
) -> list[ItemUpholsteryRequirement]:
    return list(
        (
            await session.execute(
                select(ItemUpholsteryRequirement)
                .where(
                    ItemUpholsteryRequirement.workspace_id == workspace_id,
                    ItemUpholsteryRequirement.upholstery_inventory_id == inventory_id,
                    ItemUpholsteryRequirement.state == state,
                    ItemUpholsteryRequirement.is_deleted.is_(False),
                )
                .order_by(ItemUpholsteryRequirement.client_id.asc())
            )
        ).scalars()
    )


async def _notify(ctx: ServiceContext, promoted_ids: list[str], demoted_ids: list[str]) -> None:
    for ids, state, notification_type, title, body in (
        (
            promoted_ids,
            ORDERED,
            "upholstery_requirement_ordered",
            "Requirements ordered",
            f"{len(promoted_ids)} item(s) with upholstery requirements ordered",
        ),
        (
            demoted_ids,
            NEEDS_ORDERING,
            "upholstery_requirement_needs_ordering",
            "Order reduced",
            f"{len(demoted_ids)} item(s) need their upholstery ordered again",
        ),
    ):
        if not ids:
            continue
        target_user_ids = list(
            await resolve_upholstery_notification_targets(
                ctx.session, ctx.workspace_id, ids, ctx.user_id, {"state": state.value}
            )
        )
        if not target_user_ids:
            continue
        await create_instant_task(
            session=ctx.session,
            task_type=TaskType.CREATE_NOTIFICATIONS,
            payload=asdict(
                NotificationPayload(
                    notification_type=notification_type,
                    user_ids=target_user_ids,
                    title=title,
                    body=body,
                    entity_type=None,
                    entity_client_id=None,
                    exclude_viewing=[],
                )
            ),
        )


def _payload(order: UpholsteryOrder) -> dict:
    return {
        "client_id": order.client_id,
        "state": order.state.value,
        "order_amount_meters": float(order.order_amount_meters),
        "received_amount_meters": (
            float(order.received_amount_meters)
            if order.received_amount_meters is not None
            else None
        ),
    }
