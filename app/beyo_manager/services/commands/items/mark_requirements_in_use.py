"""CMD-2: Mark available requirements as in-use."""

from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.items.notification_targets import resolve_upholstery_notification_targets
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.commands.items.requests import parse_mark_in_use_request
from beyo_manager.services.commands.items.update_and_delete_item_upholstery import (
    ensure_requirement_actions_are_available,
)
from beyo_manager.services.commands.upholstery._inventory_mutations import consume_to_in_use
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
from beyo_manager.services.infra.execution.task_factory import create_instant_task


async def mark_requirements_in_use(ctx: ServiceContext) -> dict:
    """Mark all AVAILABLE requirements as IN_USE."""
    request = parse_mark_in_use_request(ctx.incoming_data)

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

        target_user_ids = list(
            await resolve_upholstery_notification_targets(
                ctx.session,
                ctx.workspace_id,
                [request.item_upholstery_id],
                ctx.user_id,
                {"state": ItemUpholsteryRequirementStateEnum.IN_USE.value},
            )
        )
        if target_user_ids:
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(NotificationPayload(
                    notification_type="upholstery_requirement_in_use",
                    user_ids=target_user_ids,
                    title="Requirements in use",
                    body=f'{iup.name or "Upholstery"} was marked in use for {len(requirements)} item(s)',
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
            extra={"new_state": ItemUpholsteryRequirementStateEnum.IN_USE.value},
        ),
    ])
    return {}
