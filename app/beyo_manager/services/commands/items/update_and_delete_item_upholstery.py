"""Update and delete commands for ItemUpholstery."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import (
    build_delete_message,
    build_update_message,
)
from beyo_manager.services.commands.items.requests import (
    parse_update_item_upholstery_request,
    parse_delete_item_upholstery_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


async def update_item_upholstery(ctx: ServiceContext) -> dict:
    """Update ItemUpholstery fields."""
    request = parse_update_item_upholstery_request(ctx.incoming_data)
    iup_mutable_fields = ["name", "code", "amount_meters", "time_to_fix_in_seconds"]
    updated_fields = [field for field in iup_mutable_fields if getattr(request, field) is not None]

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(ItemUpholstery).where(
                ItemUpholstery.workspace_id == ctx.workspace_id,
                ItemUpholstery.client_id == request.client_id,
                ItemUpholstery.is_deleted.is_(False),
            )
        )
        iup = result.scalar_one_or_none()
        if iup is None:
            raise NotFound("ItemUpholstery not found.")

        if request.name is not None:
            iup.name = request.name
        if request.code is not None:
            iup.code = request.code
        if request.amount_meters is not None:
            iup.amount_meters = request.amount_meters
        if request.time_to_fix_in_seconds is not None:
            iup.time_to_fix_in_seconds = request.time_to_fix_in_seconds

        iup.updated_at = datetime.now(timezone.utc)
        iup.updated_by_id = ctx.user_id

        username = ctx.identity.get("username")
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.ITEM_UPHOLSTERY,
            entity_client_id=iup.client_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=build_update_message(username, updated_fields, "upholstery"),
            field_name=None,
            from_value=None,
            to_value=None,
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )

    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="item:updated",
            client_id=iup.item_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ])
    return {}


async def delete_item_upholstery(ctx: ServiceContext) -> dict:
    """Soft delete an ItemUpholstery."""
    request = parse_delete_item_upholstery_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(ItemUpholstery).where(
                ItemUpholstery.workspace_id == ctx.workspace_id,
                ItemUpholstery.client_id == request.client_id,
                ItemUpholstery.is_deleted.is_(False),
            )
        )
        iup = result.scalar_one_or_none()
        if iup is None:
            raise NotFound("ItemUpholstery not found.")

        iup.is_deleted = True
        iup.deleted_at = datetime.now(timezone.utc)
        iup.deleted_by_id = ctx.user_id

        username = ctx.identity.get("username")
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.ITEM_UPHOLSTERY,
            entity_client_id=iup.client_id,
            change_type=HistoryRecordChangeTypeEnum.DELETED,
            description=build_delete_message(username, "upholstery", "item"),
            field_name=None,
            from_value=None,
            to_value=None,
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )

    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="item:updated",
            client_id=iup.item_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ])
    return {}
