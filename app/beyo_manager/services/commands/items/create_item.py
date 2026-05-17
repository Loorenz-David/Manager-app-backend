"""CMD-1: Create Item atomically with optional issues and optional upholstery."""

from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemStateEnum, ItemUpholsterySourceEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.services.commands.items.create_item_issue import _create_item_issue_in_session
from beyo_manager.services.commands.items.create_item_upholstery import _create_item_upholstery_in_session
from beyo_manager.services.commands.items.requests import (
    CreateItemIssueRequest,
    parse_create_item_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def create_item(ctx: ServiceContext) -> dict:
    """Create Item with optional embedded issues and optional item upholstery."""
    request = parse_create_item_request(ctx.incoming_data)

    if request.article_number is None and request.sku is None:
        raise ValidationError("At least one of article_number or sku must be provided.")

    if request.item_upholstery is not None:
        iup_input = request.item_upholstery
        if iup_input.source == ItemUpholsterySourceEnum.INTERNAL and iup_input.upholstery_id is None:
            raise ValidationError("item_upholstery.upholstery_id is required when source is internal.")
        if iup_input.source == ItemUpholsterySourceEnum.CUSTOMER and iup_input.upholstery_id is not None:
            raise ValidationError("item_upholstery.upholstery_id must be null when source is customer.")

    async with maybe_begin(ctx.session):
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

        if request.item_issues:
            for issue_input in request.item_issues:
                issue_data = CreateItemIssueRequest(
                    item_id=item.client_id,
                    issue_type_id=issue_input.issue_type_id,
                    issue_severity_id=issue_input.issue_severity_id,
                    base_time_seconds=issue_input.base_time_seconds,
                    time_multiplier=issue_input.time_multiplier,
                    issue_name_snapshot=issue_input.issue_name_snapshot,
                    severity_name_snapshot=issue_input.severity_name_snapshot,
                )
                await _create_item_issue_in_session(
                    session=ctx.session,
                    workspace_id=ctx.workspace_id,
                    item_id=item.client_id,
                    issue_data=issue_data,
                    user_id=ctx.user_id,
                )

        if request.item_upholstery is not None:
            iup_input = request.item_upholstery
            upholstery_name = iup_input.name
            upholstery_code = iup_input.code

            if iup_input.source == ItemUpholsterySourceEnum.INTERNAL:
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

    return {"client_id": item.client_id}
