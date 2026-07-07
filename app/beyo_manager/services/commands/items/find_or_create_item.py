"""Find existing Item by article_number or sku, update its fields if found, create if not found."""

from datetime import datetime, timezone

from sqlalchemy import or_, select

from beyo_manager.domain.items.enums import ItemStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.services.commands.location_tracker.enqueue_item_zone_push import (
    enqueue_item_zone_location_push,
)
from beyo_manager.services.commands.items.requests import parse_find_or_create_item_request
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


_DIRECT_FIELDS = {
    "article_number",
    "sku",
    "quantity",
    "designer",
    "height_in_cm",
    "width_in_cm",
    "depth_in_cm",
    "item_value_minor",
    "item_cost_minor",
    "item_currency",
    "item_position",
    "item_zone",
    "external_id",
    "external_url",
    "external_source",
    "external_order_id",
}


async def find_or_create_item(ctx: ServiceContext) -> dict:
    """Return an existing active item matched by article_number or sku, updating its fields; create if not found."""
    request = parse_find_or_create_item_request(ctx.incoming_data)

    if request.article_number is None and request.sku is None:
        raise ValidationError("At least one of article_number or sku must be provided.")

    if request.client_id is not None:
        validate_provided_client_id(request.client_id, "itm")

    async with maybe_begin(ctx.session):
        lookup_conditions = []
        if request.article_number is not None:
            lookup_conditions.append(Item.article_number == request.article_number)
        if request.sku is not None:
            lookup_conditions.append(Item.sku == request.sku)

        existing_result = await ctx.session.execute(
            select(Item)
            .where(
                Item.workspace_id == ctx.workspace_id,
                Item.is_deleted.is_(False),
                or_(*lookup_conditions),
            )
            .limit(1)
        )
        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            for field_name in _DIRECT_FIELDS:
                if field_name in request.model_fields_set:
                    setattr(existing, field_name, getattr(request, field_name))

            if "item_category_id" in request.model_fields_set:
                existing.item_category_id = request.item_category_id
                if request.item_category_id is None:
                    existing.item_category_snapshot = None
                    existing.item_major_category_snapshot = None
                else:
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
                    existing.item_category_snapshot = category.name
                    existing.item_major_category_snapshot = category.major_category.value

            existing.updated_at = datetime.now(timezone.utc)
            existing.updated_by_id = ctx.user_id

            if "item_zone" in request.model_fields_set:
                await enqueue_item_zone_location_push(
                    ctx.session,
                    existing,
                    username=ctx.identity.get("username"),
                    requested_by_user_id=ctx.user_id,
                )

            return {"client_id": existing.client_id, "was_created": False}

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

        item_kwargs: dict[str, str] = {}
        if request.client_id is not None:
            dup = await ctx.session.get(Item, request.client_id)
            if dup is not None:
                raise ConflictError("Provided client_id is already in use.")
            item_kwargs["client_id"] = request.client_id

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

    return {"client_id": item.client_id, "was_created": True}
