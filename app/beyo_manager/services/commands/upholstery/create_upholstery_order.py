from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.items.notification_targets import resolve_upholstery_notification_targets
from beyo_manager.domain.upholstery.enums import InventoryMovementTriggerEnum, UpholsteryOrderStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.upholstery.supplier import Supplier
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.models.tables.upholstery.upholstery_order import UpholsteryOrder
from beyo_manager.models.tables.upholstery.upholstery_order_history_record import UpholsteryOrderHistoryRecord
from beyo_manager.models.tables.upholstery.upholstery_supplier_link import UpholsterySupplierLink
from beyo_manager.services.commands.upholstery._inventory_history import (
    InventoryMovementContext,
)
from beyo_manager.services.commands.upholstery._inventory_mutations import add_ordered
from beyo_manager.services.commands.upholstery._pooled_requirement_allocation import (
    allocate_needs_ordering_to_ordered,
)
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
            movement = InventoryMovementContext.from_service(
                ctx,
                InventoryMovementTriggerEnum.ORDER_CREATED,
                upholstery_order_id=order.client_id,
            )
            order_record = await add_ordered(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                upholstery_inventory_id=inventory.client_id,
                quantity=request.order_amount_meters,
                movement=movement,
            )
            allocated_item_upholstery_ids = await allocate_needs_ordering_to_ordered(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                inventory=inventory,
                priority_item_upholstery_ids=request.priority_item_upholstery_ids,
                actor_id=ctx.user_id,
                parent_record=order_record,
                movement=movement,
            )
            if allocated_item_upholstery_ids:
                target_user_ids = list(
                    await resolve_upholstery_notification_targets(
                        ctx.session,
                        ctx.workspace_id,
                        allocated_item_upholstery_ids,
                        ctx.user_id,
                        {"state": ItemUpholsteryRequirementStateEnum.ORDERED.value},
                    )
                )
                if target_user_ids:
                    await create_instant_task(
                        session=ctx.session,
                        task_type=TaskType.CREATE_NOTIFICATIONS,
                        payload=asdict(NotificationPayload(
                            notification_type="upholstery_requirement_ordered",
                            user_ids=target_user_ids,
                            title="Requirements ordered",
                            body=f'{len(allocated_item_upholstery_ids)} item(s) with upholstery requirements ordered',
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

