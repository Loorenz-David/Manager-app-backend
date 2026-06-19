"""Delete upholstery inventory command (soft delete)."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.upholstery.requests import parse_delete_upholstery_inventory_request
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


async def delete_upholstery_inventory(ctx: ServiceContext) -> dict:
    """Soft delete an upholstery inventory record and its parent upholstery."""
    request = parse_delete_upholstery_inventory_request(ctx.incoming_data)

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.client_id == request.client_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        inv = result.scalar_one_or_none()
        if inv is None:
            raise NotFound("UpholsteryInventory not found.")

        now = datetime.now(timezone.utc)

        inv.is_deleted = True
        inv.deleted_at = now
        inv.deleted_by_id = ctx.user_id

        uph_result = await ctx.session.execute(
            select(Upholstery).where(
                Upholstery.workspace_id == ctx.workspace_id,
                Upholstery.client_id == inv.upholstery_id,
                Upholstery.is_deleted.is_(False),
            )
        )
        upholstery = uph_result.scalar_one_or_none()
        if upholstery is not None:
            upholstery.is_deleted = True
            upholstery.deleted_at = now
            upholstery.deleted_by_id = ctx.user_id
            upholstery.list_order = None

    pending_events = [
        WorkspaceEvent(
            event_name="upholstery:inventory-deleted",
            client_id=inv.client_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ]
    if upholstery is not None:
        pending_events.append(
            WorkspaceEvent(
                event_name="upholstery:deleted",
                client_id=upholstery.client_id,
                workspace_id=ctx.workspace_id,
                extra={},
            )
        )

    await event_bus.dispatch(pending_events)
    return {}
