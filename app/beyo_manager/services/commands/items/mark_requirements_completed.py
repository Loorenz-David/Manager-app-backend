"""CMD-3: Mark in-use and available requirements as completed."""

from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.commands.items._notification_helpers import _resolve_upholstery_audience
from beyo_manager.services.commands.items.requests import parse_mark_completed_request
from beyo_manager.services.commands.items.update_and_delete_item_upholstery import (
    ensure_requirement_actions_are_available,
)
from beyo_manager.services.commands.upholstery._inventory_mutations import (
    complete_available_direct,
    finish_in_use,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
from beyo_manager.services.infra.execution.task_factory import create_instant_task


async def mark_requirements_completed(ctx: ServiceContext) -> dict:
    """Mark all IN_USE and AVAILABLE requirements as COMPLETED."""
    request = parse_mark_completed_request(ctx.incoming_data)

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

        result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.item_upholstery_id == request.item_upholstery_id,
                ItemUpholsteryRequirement.state.in_([
                    ItemUpholsteryRequirementStateEnum.IN_USE,
                    ItemUpholsteryRequirementStateEnum.AVAILABLE,
                ]),
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        requirements = result.scalars().all()

        if not requirements:
            raise ValidationError(
                "No IN_USE or AVAILABLE requirements found for this item upholstery."
            )

        now = datetime.now(timezone.utc)
        for req in requirements:
            if req.state == ItemUpholsteryRequirementStateEnum.IN_USE:
                if req.upholstery_inventory_id is not None:
                    await finish_in_use(
                        session=ctx.session,
                        workspace_id=ctx.workspace_id,
                        upholstery_inventory_id=req.upholstery_inventory_id,
                        quantity=req.amount_meters,
                        source=req.source,
                    )
            elif req.state == ItemUpholsteryRequirementStateEnum.AVAILABLE:
                if req.upholstery_inventory_id is not None:
                    await complete_available_direct(
                        session=ctx.session,
                        workspace_id=ctx.workspace_id,
                        upholstery_inventory_id=req.upholstery_inventory_id,
                        quantity=req.amount_meters,
                        source=req.source,
                    )
            req.state = ItemUpholsteryRequirementStateEnum.COMPLETED
            req.completed_at = now
            req.updated_by_id = ctx.user_id

        target_user_ids = await _resolve_upholstery_audience(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            item_upholstery_ids=[request.item_upholstery_id],
            actor_id=ctx.user_id,
        )
        if target_user_ids:
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(NotificationPayload(
                    notification_type="upholstery_requirement_completed",
                    user_ids=target_user_ids,
                    title="Requirements completed",
                    body="Upholstery requirements have been marked as completed.",
                    entity_type="item_upholstery",
                    entity_client_id=request.item_upholstery_id,
                    exclude_viewing=[],
                )),
            )

    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="item:upholstery-requirement-state-changed",
            client_id=request.item_upholstery_id,
            workspace_id=ctx.workspace_id,
            extra={"new_state": ItemUpholsteryRequirementStateEnum.COMPLETED.value},
        ),
    ])
    return {}
