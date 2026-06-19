"""Update and delete commands for ItemUpholstery."""

from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.items.enums import (
    ItemUpholsteryRequirementStateEnum,
    ItemUpholsterySourceEnum,
)
from beyo_manager.domain.items.upholstery_selection import (
    has_positive_amount_meters,
    is_deferred_internal_upholstery,
)
from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
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
from beyo_manager.services.commands.items.create_item_upholstery import (
    _create_initial_requirement_for_item_upholstery,
)
from beyo_manager.services.commands.upholstery._inventory_mutations import (
    adjust_need,
    rollback_in_use_to_stored,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


_DECREMENT_NEED_STATES = {
    ItemUpholsteryRequirementStateEnum.AVAILABLE,
    ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
    ItemUpholsteryRequirementStateEnum.ORDERED,
}

_SELECTION_REQUIRED_ERROR = "Upholstery must be selected before requirement actions can be performed."


def _raise_if_internal_selection_still_missing(
    source: ItemUpholsterySourceEnum,
    upholstery_id: str | None,
    amount_meters: Decimal | None,
) -> None:
    if source == ItemUpholsterySourceEnum.INTERNAL and upholstery_id is None and not has_positive_amount_meters(amount_meters):
        raise ValidationError(
            "upholstery_id is required when source is INTERNAL unless positive amount_meters is provided."
        )


def ensure_requirement_actions_are_available(iup: ItemUpholstery) -> None:
    if iup.active_requirement_id is None and is_deferred_internal_upholstery(iup.source, iup.upholstery_id, iup.amount_meters):
        raise ValidationError(_SELECTION_REQUIRED_ERROR)


async def update_item_upholstery(ctx: ServiceContext) -> dict:
    """Update ItemUpholstery fields."""
    request = parse_update_item_upholstery_request(ctx.incoming_data)
    fields_set = request.model_fields_set
    mutable_fields = [
        "upholstery_id",
        "source",
        "name",
        "code",
        "amount_meters",
        "time_to_fix_in_seconds",
    ]

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

        before_name = iup.name
        before_values = {
            "upholstery_id": iup.upholstery_id,
            "source": iup.source,
            "name": iup.name,
            "code": iup.code,
            "amount_meters": iup.amount_meters,
            "time_to_fix_in_seconds": iup.time_to_fix_in_seconds,
        }

        swap_requested = (
            ("upholstery_id" in fields_set and request.upholstery_id != iup.upholstery_id)
            or ("source" in fields_set and request.source != iup.source)
        )

        now = datetime.now(timezone.utc)

        resolved_source = request.source if "source" in fields_set else iup.source
        resolved_upholstery_id = request.upholstery_id if "upholstery_id" in fields_set else iup.upholstery_id
        resolved_amount = request.amount_meters if "amount_meters" in fields_set else iup.amount_meters
        resolved_time = (
            request.time_to_fix_in_seconds
            if "time_to_fix_in_seconds" in fields_set
            else iup.time_to_fix_in_seconds
        )
        resolved_name = request.name if "name" in fields_set else iup.name
        resolved_code = request.code if "code" in fields_set else iup.code

        _raise_if_internal_selection_still_missing(
            resolved_source,
            resolved_upholstery_id,
            resolved_amount,
        )

        if swap_requested:
            if iup.active_requirement_id is None:
                iup.upholstery_id = resolved_upholstery_id
                iup.source = resolved_source
                iup.name = resolved_name
                iup.code = resolved_code
                iup.amount_meters = resolved_amount
                iup.time_to_fix_in_seconds = resolved_time

                if (
                    resolved_source == ItemUpholsterySourceEnum.INTERNAL
                    and resolved_upholstery_id is not None
                ):
                    await _create_initial_requirement_for_item_upholstery(
                        session=ctx.session,
                        workspace_id=ctx.workspace_id,
                        item_upholstery=iup,
                        amount_meters=iup.amount_meters,
                        source=iup.source,
                        user_id=ctx.user_id,
                    )
            else:
                active_req_result = await ctx.session.execute(
                    select(ItemUpholsteryRequirement).where(
                        ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                        ItemUpholsteryRequirement.client_id == iup.active_requirement_id,
                        ItemUpholsteryRequirement.item_upholstery_id == iup.client_id,
                        ItemUpholsteryRequirement.is_deleted.is_(False),
                    )
                )
                active_req = active_req_result.scalar_one_or_none()
                if active_req is None:
                    raise NotFound("Active requirement not found.")

                if active_req.state == ItemUpholsteryRequirementStateEnum.COMPLETED:
                    raise ConflictError("Cannot swap upholstery after requirement completion.")

                old_amount = active_req.amount_meters or Decimal("0")
                if old_amount > Decimal("0") and active_req.upholstery_inventory_id is not None:
                    if active_req.state in _DECREMENT_NEED_STATES:
                        await adjust_need(
                            session=ctx.session,
                            workspace_id=ctx.workspace_id,
                            upholstery_inventory_id=active_req.upholstery_inventory_id,
                            delta=-old_amount,
                        )
                    elif active_req.state == ItemUpholsteryRequirementStateEnum.IN_USE:
                        await rollback_in_use_to_stored(
                            session=ctx.session,
                            workspace_id=ctx.workspace_id,
                            upholstery_inventory_id=active_req.upholstery_inventory_id,
                            quantity=old_amount,
                        )

                active_req.state = ItemUpholsteryRequirementStateEnum.FAILED
                active_req.failed_at = now
                active_req.updated_by_id = ctx.user_id

                if (
                    resolved_source != ItemUpholsterySourceEnum.CUSTOMER
                    and resolved_upholstery_id is None
                ):
                    raise ValidationError(
                        "upholstery_id is required when source is not CUSTOMER."
                    )

                iup.upholstery_id = resolved_upholstery_id
                iup.source = resolved_source
                iup.name = resolved_name
                iup.code = resolved_code
                iup.amount_meters = resolved_amount
                iup.time_to_fix_in_seconds = resolved_time

                await _create_initial_requirement_for_item_upholstery(
                    session=ctx.session,
                    workspace_id=ctx.workspace_id,
                    item_upholstery=iup,
                    amount_meters=iup.amount_meters,
                    source=iup.source,
                    user_id=ctx.user_id,
                )
        else:
            if "name" in fields_set:
                iup.name = request.name
            if "code" in fields_set:
                iup.code = request.code
            if "amount_meters" in fields_set:
                iup.amount_meters = request.amount_meters
            if "time_to_fix_in_seconds" in fields_set:
                iup.time_to_fix_in_seconds = request.time_to_fix_in_seconds

        iup.updated_at = now
        iup.updated_by_id = ctx.user_id

        after_values = {
            "upholstery_id": iup.upholstery_id,
            "source": iup.source,
            "name": iup.name,
            "code": iup.code,
            "amount_meters": iup.amount_meters,
            "time_to_fix_in_seconds": iup.time_to_fix_in_seconds,
        }
        updated_fields = [
            field for field in mutable_fields if before_values[field] != after_values[field]
        ]

        username = ctx.identity.get("username")
        upholstery_target = f"upholstery '{before_name}'" if before_name else "upholstery"
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.ITEM_UPHOLSTERY,
            entity_client_id=iup.client_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=build_update_message(username, updated_fields, upholstery_target),
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
        WorkspaceEvent(
            event_name="item:upholstery-updated",
            client_id=iup.client_id,
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
        upholstery_target = f"upholstery '{iup.name}'" if iup.name else "upholstery"
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.ITEM_UPHOLSTERY,
            entity_client_id=iup.client_id,
            change_type=HistoryRecordChangeTypeEnum.DELETED,
            description=build_delete_message(username, upholstery_target, "item"),
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
        WorkspaceEvent(
            event_name="item:upholstery-deleted",
            client_id=iup.client_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ])
    return {}
