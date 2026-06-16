from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.upholstery.enums import UpholsteryOrderStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.upholstery.supplier import Supplier
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.models.tables.upholstery.upholstery_order import UpholsteryOrder
from beyo_manager.models.tables.upholstery.upholstery_order_history_record import UpholsteryOrderHistoryRecord
from beyo_manager.models.tables.upholstery.upholstery_supplier_link import UpholsterySupplierLink
from beyo_manager.services.commands.items._allocation_algorithm import run_skip_and_continue_allocation
from beyo_manager.services.commands.items._notification_helpers import _resolve_upholstery_audience
from beyo_manager.services.commands.upholstery._inventory_mutations import add_ordered
from beyo_manager.services.commands.upholstery.requests import parse_create_upholstery_order_request
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
from beyo_manager.services.infra.execution.task_factory import create_instant_task


async def create_upholstery_order(ctx: ServiceContext) -> dict:
    request = parse_create_upholstery_order_request(ctx.incoming_data)

    if request.client_id is not None:
        validate_provided_client_id(request.client_id, "uor")

    async with ctx.session.begin():
        order_kwargs: dict[str, str] = {}
        if request.client_id is not None:
            dup = await ctx.session.get(UpholsteryOrder, request.client_id)
            if dup is not None:
                raise ConflictError("Provided client_id is already in use.")
            order_kwargs["client_id"] = request.client_id

        inv_result = await ctx.session.execute(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.upholstery_id == request.upholstery_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        inventory = inv_result.scalar_one_or_none()
        if inventory is None:
            raise NotFound("No active inventory record found for the given upholstery_id.")

        supplier: Supplier | None = None
        if request.supplier_id is not None:
            supplier = await ctx.session.get(Supplier, request.supplier_id)
            if (
                supplier is None
                or supplier.workspace_id != ctx.workspace_id
                or supplier.is_deleted
            ):
                raise NotFound("Supplier not found.")

        supplier_link: UpholsterySupplierLink | None = None
        if request.upholstery_supplier_link_id is not None:
            supplier_link = await ctx.session.get(
                UpholsterySupplierLink,
                request.upholstery_supplier_link_id,
            )
            if (
                supplier_link is None
                or supplier_link.workspace_id != ctx.workspace_id
                or supplier_link.is_deleted
            ):
                raise NotFound("Upholstery supplier link not found.")
            if supplier_link.upholstery_id != request.upholstery_id:
                raise ValidationError(
                    "upholstery_supplier_link_id does not belong to the given upholstery_id."
                )
            if (
                request.supplier_id is not None
                and supplier_link.supplier_id != request.supplier_id
            ):
                raise ValidationError(
                    "supplier_id does not match the provided upholstery_supplier_link_id."
                )

        order = UpholsteryOrder(
            **order_kwargs,
            workspace_id=ctx.workspace_id,
            upholstery_inventory_id=inventory.client_id,
            upholstery_supplier_link_id=(
                supplier_link.client_id if supplier_link is not None else None
            ),
            supplier_id=(
                supplier.client_id
                if supplier is not None
                else supplier_link.supplier_id if supplier_link is not None else None
            ),
            order_amount_meters=request.order_amount_meters,
            price_minor=request.price_minor,
            currency=request.currency,
            order_at=request.order_at,
            state=request.state,
            ordered_by_id=ctx.user_id,
            expected_receive_at=request.expected_receive_at,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(order)
        await ctx.session.flush()

        history = UpholsteryOrderHistoryRecord(
            workspace_id=ctx.workspace_id,
            upholstery_order_id=order.client_id,
            state=order.state,
            changed_at=datetime.now(timezone.utc),
            snapshot_price_minor=order.price_minor,
            snapshot_currency=order.currency,
            snapshot_order_amount_meters=order.order_amount_meters,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(history)

        allocated_item_upholstery_ids: list[str] = []
        if request.state == UpholsteryOrderStateEnum.ORDERED:
            await add_ordered(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                upholstery_inventory_id=inventory.client_id,
                quantity=request.order_amount_meters,
            )
            allocated_item_upholstery_ids = await _allocate_requirements(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                inventory_id=inventory.client_id,
                order_amount_meters=request.order_amount_meters,
                priority_item_upholstery_ids=request.priority_item_upholstery_ids,
                actor_id=ctx.user_id,
            )
            if allocated_item_upholstery_ids:
                target_user_ids = await _resolve_upholstery_audience(
                    session=ctx.session,
                    workspace_id=ctx.workspace_id,
                    item_upholstery_ids=allocated_item_upholstery_ids,
                    actor_id=ctx.user_id,
                )
                if target_user_ids:
                    await create_instant_task(
                        session=ctx.session,
                        task_type=TaskType.CREATE_NOTIFICATIONS,
                        payload=asdict(NotificationPayload(
                            notification_type="upholstery_requirement_ordered",
                            user_ids=target_user_ids,
                            title="Requirements ordered",
                            body="Upholstery requirements have been ordered.",
                            entity_type=None,
                            entity_client_id=None,
                            exclude_viewing=[],
                        )),
                    )

    await event_bus.dispatch(
        [
            WorkspaceEvent(
                event_name="upholstery:order-created",
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
                        "new_state": ItemUpholsteryRequirementStateEnum.ORDERED.value,
                    },
                ),
            ]
        )

    return {"client_id": order.client_id}


async def _allocate_requirements(
    session: AsyncSession,
    workspace_id: str,
    inventory_id: str,
    order_amount_meters: Decimal,
    priority_item_upholstery_ids: list[str],
    actor_id: str,
) -> list[str]:
    req_result = await session.execute(
        select(ItemUpholsteryRequirement).where(
            ItemUpholsteryRequirement.workspace_id == workspace_id,
            ItemUpholsteryRequirement.upholstery_inventory_id == inventory_id,
            ItemUpholsteryRequirement.state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
            ItemUpholsteryRequirement.is_deleted.is_(False),
        )
    )
    candidates = req_result.scalars().all()
    if not candidates:
        return []

    item_upholstery_ids = [req.item_upholstery_id for req in candidates]
    ready_result = await session.execute(
        select(
            ItemUpholstery.client_id,
            func.min(Task.ready_by_at).label("earliest_ready_by_at"),
        )
        .join(
            TaskItem,
            (TaskItem.item_id == ItemUpholstery.item_id)
            & (TaskItem.workspace_id == workspace_id)
            & (TaskItem.removed_at.is_(None)),
        )
        .join(
            Task,
            (Task.client_id == TaskItem.task_id)
            & (Task.workspace_id == workspace_id)
            & (Task.is_deleted.is_(False))
            & (Task.ready_by_at.is_not(None)),
        )
        .where(
            ItemUpholstery.workspace_id == workspace_id,
            ItemUpholstery.client_id.in_(item_upholstery_ids),
            ItemUpholstery.is_deleted.is_(False),
        )
        .group_by(ItemUpholstery.client_id)
    )
    ready_by_at_map: dict[str, datetime | None] = {
        row.client_id: row.earliest_ready_by_at for row in ready_result
    }

    priority_set = set(priority_item_upholstery_ids)
    priority_order = {
        item_upholstery_id: index
        for index, item_upholstery_id in enumerate(priority_item_upholstery_ids)
    }

    tier1 = sorted(
        [req for req in candidates if req.item_upholstery_id in priority_set],
        key=lambda req: priority_order.get(
            req.item_upholstery_id,
            len(priority_item_upholstery_ids),
        ),
    )
    tier2_and_3 = sorted(
        [req for req in candidates if req.item_upholstery_id not in priority_set],
        key=lambda req: (
            ready_by_at_map.get(req.item_upholstery_id) is None,
            ready_by_at_map.get(req.item_upholstery_id),
            req.created_at,
        ),
    )
    ordered_candidates = tier1 + tier2_and_3

    result = run_skip_and_continue_allocation(
        candidates=ordered_candidates,
        running_pool=order_amount_meters,
        target_state=ItemUpholsteryRequirementStateEnum.ORDERED,
        timestamp_field="ordered_at",
    )

    resolved_set = set(result["resolved"])
    for req in ordered_candidates:
        if req.item_upholstery_id in resolved_set:
            req.updated_by_id = actor_id

    return result["resolved"]
