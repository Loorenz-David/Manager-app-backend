"""CMD-1: Create Item atomically with optional issues and optional upholstery."""

from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.items.enums import ItemUpholsterySourceEnum
from beyo_manager.domain.items.upholstery_selection import should_defer_requirement_creation
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import build_create_message
from beyo_manager.services.commands.items._create_item_in_session import create_item_in_session
from beyo_manager.services.commands.items.batch_create_item_issues import _create_item_issues_in_session
from beyo_manager.services.commands.items.create_item_upholstery import (
    ensure_item_upholstery_in_session,
)
from beyo_manager.services.commands.items.requests import parse_create_item_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def create_item(ctx: ServiceContext) -> dict:
    """Create Item with optional embedded issues and optional item upholstery."""
    request = parse_create_item_request(ctx.incoming_data)

    if request.article_number is None and request.sku is None and request.sku_template_task_type is None:
        raise ValidationError(
            "At least one of article_number, sku, or sku_template_task_type must be provided."
        )

    if request.item_upholstery is not None:
        iup_input = request.item_upholstery
        if (
            iup_input.source == ItemUpholsterySourceEnum.INTERNAL
            and iup_input.upholstery_id is None
            and not should_defer_requirement_creation(
                iup_input.source,
                iup_input.upholstery_id,
                iup_input.amount_meters,
            )
        ):
            raise ValidationError(
                "item_upholstery.upholstery_id is required when source is internal unless positive amount_meters is provided."
            )
        if iup_input.source == ItemUpholsterySourceEnum.CUSTOMER and iup_input.upholstery_id is not None:
            raise ValidationError("item_upholstery.upholstery_id must be null when source is customer.")

    async with maybe_begin(ctx.session):
        item, pending_events = await create_item_in_session(
            ctx.session,
            workspace_id=ctx.workspace_id,
            user_id=ctx.user_id,
            username=ctx.identity.get("username"),
            client_id=request.client_id,
            article_number=request.article_number,
            sku=request.sku,
            sku_template_task_type=request.sku_template_task_type,
            item_category_id=request.item_category_id,
            quantity=request.quantity,
            designer=request.designer,
            height_in_cm=request.height_in_cm,
            width_in_cm=request.width_in_cm,
            depth_in_cm=request.depth_in_cm,
            item_position=request.item_position,
            item_zone=request.item_zone,
            external_id=request.external_id,
            external_url=request.external_url,
            external_source=request.external_source,
            external_order_id=request.external_order_id,
            can_have_upholstery=request.can_have_upholstery,
            properties=request.properties,
        )

        if request.item_issues:
            await _create_item_issues_in_session(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                item_id=item.client_id,
                issues_data=request.item_issues,
            )

        if request.item_upholstery is not None:
            iup_input = request.item_upholstery
            upholstery_name = iup_input.name
            upholstery_code = iup_input.code

            if iup_input.source == ItemUpholsterySourceEnum.INTERNAL and iup_input.upholstery_id is not None:
                upholstery_result = await ctx.session.execute(
                    select(Upholstery).where(
                        Upholstery.workspace_id == ctx.workspace_id,
                        Upholstery.client_id == iup_input.upholstery_id,
                        Upholstery.is_deleted.is_(False),
                    )
                )
                upholstery = upholstery_result.scalar_one_or_none()
                if upholstery is None:
                    raise NotFound("Upholstery not found.")
                if upholstery_name is None:
                    upholstery_name = upholstery.name
                if upholstery_code is None:
                    upholstery_code = upholstery.code

            await ensure_item_upholstery_in_session(
                ctx,
                item_id=item.client_id,
                data={
                    "client_id": iup_input.client_id,
                    "upholstery_id": iup_input.upholstery_id,
                    "name": upholstery_name,
                    "code": upholstery_code,
                    "amount_meters": iup_input.amount_meters,
                    "source": iup_input.source,
                    "time_to_fix_in_seconds": iup_input.time_to_fix_in_seconds,
                },
            )

        username = ctx.identity.get("username")
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.ITEM,
            entity_client_id=item.client_id,
            change_type=HistoryRecordChangeTypeEnum.CREATED,
            description=build_create_message(username, "item", "workspace"),
            field_name=None,
            from_value=None,
            to_value=None,
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )

    pending_events.append(build_workspace_event(item, "item:created"))
    await event_bus.dispatch(pending_events)
    return {"client_id": item.client_id}
