from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.items.notification_targets import resolve_upholstery_notification_targets
from beyo_manager.domain.upholstery.enums import UpholsteryOrderStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.models.tables.upholstery.upholstery_order import UpholsteryOrder
from beyo_manager.models.tables.upholstery.upholstery_order_history_record import UpholsteryOrderHistoryRecord
from beyo_manager.services.commands.upholstery._inventory_mutations import confirm_ordered_to_stock
from beyo_manager.services.commands.upholstery._pooled_requirement_allocation import (
    allocate_pooled_requirements,
    fetch_earliest_ready_by_at,
)
from beyo_manager.services.commands.upholstery.requests import parse_receive_upholstery_order_request
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
from beyo_manager.services.infra.execution.task_factory import create_instant_task

_RECEIVABLE_STATES = {
    UpholsteryOrderStateEnum.ORDERED,
    UpholsteryOrderStateEnum.PARTIALLY_RECEIVED,
}


async def receive_upholstery_order(ctx: ServiceContext) -> dict:
    request = parse_receive_upholstery_order_request(ctx.incoming_data)

    allocated_item_upholstery_ids: list[str] = []

    async with ctx.session.begin():
        order = await ctx.session.get(UpholsteryOrder, request.client_id)
        if order is None or order.workspace_id != ctx.workspace_id or order.is_deleted:
            raise NotFound("Upholstery order not found.")

        if order.state not in _RECEIVABLE_STATES:
            raise ValidationError(
                "Order must be in ORDERED or PARTIALLY_RECEIVED state to record a receipt."
            )

        if order.upholstery_inventory_id is None:
            raise ValidationError("Order has no linked inventory - cannot confirm stock.")

        existing_received = order.received_amount_meters or Decimal("0")
        cumulative_received = existing_received + request.received_amount_meters
        if cumulative_received > order.order_amount_meters:
            remaining = order.order_amount_meters - existing_received
            raise ValidationError(
                "Received amount exceeds the ordered amount. "
                f"Maximum receivable: {remaining} m."
            )

        received_at = request.received_at or datetime.now(timezone.utc)
        order.state = (
            UpholsteryOrderStateEnum.RECEIVED
            if cumulative_received == order.order_amount_meters
            else UpholsteryOrderStateEnum.PARTIALLY_RECEIVED
        )
        order.received_amount_meters = cumulative_received
        order.received_at = received_at
        order.updated_by_id = ctx.user_id
        await ctx.session.flush()

        ctx.session.add(
            UpholsteryOrderHistoryRecord(
                workspace_id=ctx.workspace_id,
                upholstery_order_id=order.client_id,
                state=order.state,
                changed_at=received_at,
                snapshot_price_minor=order.price_minor,
                snapshot_currency=order.currency,
                snapshot_order_amount_meters=order.order_amount_meters,
                created_by_id=ctx.user_id,
            )
        )

        await confirm_ordered_to_stock(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            upholstery_inventory_id=order.upholstery_inventory_id,
            quantity=request.received_amount_meters,
        )

        allocated_item_upholstery_ids = await _allocate_received_requirements(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            inventory_id=order.upholstery_inventory_id,
            priority_item_upholstery_ids=request.priority_item_upholstery_ids,
            actor_id=ctx.user_id,
        )
        if allocated_item_upholstery_ids:
            target_user_ids = list(
                await resolve_upholstery_notification_targets(
                    ctx.session,
                    ctx.workspace_id,
                    allocated_item_upholstery_ids,
                    ctx.user_id,
                    {"state": ItemUpholsteryRequirementStateEnum.AVAILABLE.value},
                )
            )
            if target_user_ids:
                await create_instant_task(
                    session=ctx.session,
                    task_type=TaskType.CREATE_NOTIFICATIONS,
                    payload=asdict(
                        NotificationPayload(
                            notification_type="upholstery_requirement_available",
                            user_ids=target_user_ids,
                            title="Upholstery available",
                            body="Upholstery requirements are now available for production.",
                            entity_type=None,
                            entity_client_id=None,
                            exclude_viewing=[],
                        )
                    ),
                )

    await event_bus.dispatch(
        [
            WorkspaceEvent(
                event_name="upholstery:order-received",
                client_id=order.client_id,
                workspace_id=ctx.workspace_id,
                extra={"state": order.state.value},
            ),
        ]
    )
    if allocated_item_upholstery_ids:
        await event_bus.dispatch(
            [
                WorkspaceEvent(
                    event_name="item:upholstery-requirement-state-changed",
                    client_id="",
                    workspace_id=ctx.workspace_id,
                    extra={
                        "ids": allocated_item_upholstery_ids,
                        "new_state": ItemUpholsteryRequirementStateEnum.AVAILABLE.value,
                    },
                ),
            ]
        )

    return {
        "client_id": order.client_id,
        "state": order.state.value,
    }


async def _allocate_received_requirements(
    session: AsyncSession,
    workspace_id: str,
    inventory_id: str,
    priority_item_upholstery_ids: list[str],
    actor_id: str,
) -> list[str]:
    inventory = await session.get(UpholsteryInventory, inventory_id)
    if inventory is None or inventory.workspace_id != workspace_id or inventory.is_deleted:
        raise NotFound("UpholsteryInventory not found.")

    req_result = await session.execute(
        select(ItemUpholsteryRequirement).where(
            ItemUpholsteryRequirement.workspace_id == workspace_id,
            ItemUpholsteryRequirement.upholstery_inventory_id == inventory_id,
            ItemUpholsteryRequirement.state.in_(
                [
                    ItemUpholsteryRequirementStateEnum.ORDERED,
                    ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
                ]
            ),
            ItemUpholsteryRequirement.is_deleted.is_(False),
        )
    )
    candidates = req_result.scalars().all()
    if not candidates:
        return []

    priority_set = set(priority_item_upholstery_ids)
    priority_order = {
        item_upholstery_id: index
        for index, item_upholstery_id in enumerate(priority_item_upholstery_ids)
    }
    non_pinned_iup_ids = [
        req.item_upholstery_id for req in candidates if req.item_upholstery_id not in priority_set
    ]
    ready_by_at_map = await fetch_earliest_ready_by_at(session, workspace_id, non_pinned_iup_ids)

    tier1 = sorted(
        [req for req in candidates if req.item_upholstery_id in priority_set],
        key=lambda req: priority_order.get(
            req.item_upholstery_id,
            len(priority_item_upholstery_ids),
        ),
    )
    tier2 = sorted(
        [
            req
            for req in candidates
            if req.item_upholstery_id not in priority_set
            and req.state == ItemUpholsteryRequirementStateEnum.ORDERED
        ],
        key=lambda req: (
            ready_by_at_map.get(req.item_upholstery_id) is None,
            ready_by_at_map.get(req.item_upholstery_id),
            req.created_at,
        ),
    )
    tier3 = sorted(
        [
            req
            for req in candidates
            if req.item_upholstery_id not in priority_set
            and req.state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
        ],
        key=lambda req: (
            ready_by_at_map.get(req.item_upholstery_id) is None,
            ready_by_at_map.get(req.item_upholstery_id),
            req.created_at,
        ),
    )
    ordered_candidates = tier1 + tier2 + tier3

    return allocate_pooled_requirements(
        inventory=inventory,
        ordered_candidates=ordered_candidates,
        target_state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
        mode="stored",
        actor_id=actor_id,
        timestamp_field=None,
    )
