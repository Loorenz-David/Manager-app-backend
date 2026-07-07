"""CMD-1: Create Item atomically with optional issues and optional upholstery."""

from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.items.enums import ItemStateEnum, ItemUpholsterySourceEnum
from beyo_manager.domain.items.upholstery_selection import should_defer_requirement_creation
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import build_create_message
from beyo_manager.services.commands.items.batch_create_item_issues import _create_item_issues_in_session
from beyo_manager.services.commands.items.create_item_upholstery import _create_item_upholstery_in_session
from beyo_manager.services.commands.location_tracker.enqueue_item_zone_push import (
    enqueue_item_zone_location_push,
)
from beyo_manager.services.commands.items.requests import parse_create_item_request
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def create_item(ctx: ServiceContext) -> dict:
    """Create Item with optional embedded issues and optional item upholstery."""
    request = parse_create_item_request(ctx.incoming_data)

    if request.article_number is None and request.sku is None:
        raise ValidationError("At least one of article_number or sku must be provided.")

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
        item_kwargs: dict[str, str] = {}
        if request.client_id is not None:
            validate_provided_client_id(request.client_id, "itm")
            existing = await ctx.session.get(Item, request.client_id)
            if existing is not None:
                raise ConflictError("Provided client_id is already in use.")
            item_kwargs["client_id"] = request.client_id

        item_category_snapshot: str | None = None
        item_major_category_snapshot: str | None = None
        if request.item_category_id is not None:
            category_result = await ctx.session.execute(
                select(ItemCategory).where(
                    ItemCategory.workspace_id == ctx.workspace_id,
                    ItemCategory.client_id == request.item_category_id,
                    ItemCategory.is_deleted.is_(False),
                )
            )
            category = category_result.scalar_one_or_none()
            if category is None:
                raise NotFound("ItemCategory not found.")
            item_category_snapshot = category.name
            item_major_category_snapshot = category.major_category.value

        item = Item(
            **item_kwargs,
            workspace_id=ctx.workspace_id,
            article_number=request.article_number,
            sku=request.sku,
            state=ItemStateEnum.PENDING,
            item_category_id=request.item_category_id,
            quantity=request.quantity,
            designer=request.designer,
            height_in_cm=request.height_in_cm,
            width_in_cm=request.width_in_cm,
            depth_in_cm=request.depth_in_cm,
            item_value_minor=request.item_value_minor,
            item_cost_minor=request.item_cost_minor,
            item_currency=request.item_currency,
            item_position=request.item_position,
            item_zone=request.item_zone,
            external_id=request.external_id,
            external_url=request.external_url,
            external_source=request.external_source,
            external_order_id=request.external_order_id,
            item_category_snapshot=item_category_snapshot,
            item_major_category_snapshot=item_major_category_snapshot,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(item)
        await ctx.session.flush()

        if item.item_zone:
            await enqueue_item_zone_location_push(
                ctx.session,
                item,
                username=ctx.identity.get("username"),
                requested_by_user_id=ctx.user_id,
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

            await _create_item_upholstery_in_session(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                item_id=item.client_id,
                upholstery_id=iup_input.upholstery_id,
                name=upholstery_name,
                code=upholstery_code,
                amount_meters=iup_input.amount_meters,
                source=iup_input.source,
                time_to_fix_in_seconds=iup_input.time_to_fix_in_seconds,
                user_id=ctx.user_id,
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

    await event_bus.dispatch([
        build_workspace_event(item, "item:created"),
    ])
    return {"client_id": item.client_id}
