"""Find existing Item by article_number or sku, update its fields if found, create if not found."""

from datetime import datetime, timezone

from sqlalchemy import or_, select

from beyo_manager.domain.items.enums import ItemStateEnum
from beyo_manager.domain.items.location_push import has_zone_changed, normalize_zone
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
    "item_position",
    "item_zone",
    "external_id",
    "external_url",
    "external_source",
    "external_order_id",
    "can_have_upholstery",
}


async def find_or_create_item(
    ctx: ServiceContext,
    *,
    deferred_location_pushes: list[Item] | None = None,
) -> dict:
    """Return an existing active item matched by article_number or sku, updating its fields; create if not found.

    Pass deferred_location_pushes to collect the items whose zone should be pushed to the
    location tracker instead of enqueueing them here. The push payload is a frozen snapshot of
    article_number/sku taken at enqueue time, so a caller that writes either field after this
    returns (create_task backfilling a template sku, for instance) would otherwise ship a target
    that never matches what landed in the row. Collecting keeps the decision of *whether* to
    push — which needs the pre-update zone only visible in here — with the caller's control over
    *when*.
    """
    request = parse_find_or_create_item_request(ctx.incoming_data)

    async def _push_or_defer(item: Item) -> None:
        if deferred_location_pushes is not None:
            deferred_location_pushes.append(item)
            return
        await enqueue_item_zone_location_push(
            ctx.session,
            item,
            username=ctx.identity.get("username"),
            requested_by_user_id=ctx.user_id,
        )

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
            zone_before_update = existing.item_zone

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

            if "item_zone" in request.model_fields_set and has_zone_changed(
                zone_before_update, existing.item_zone
            ):
                await _push_or_defer(existing)

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
            item_position=request.item_position,
            item_zone=request.item_zone,
            external_id=request.external_id,
            external_url=request.external_url,
            external_source=request.external_source,
            external_order_id=request.external_order_id,
            can_have_upholstery=request.can_have_upholstery,
            item_category_snapshot=item_category_snapshot,
            item_major_category_snapshot=item_major_category_snapshot,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(item)
        await ctx.session.flush()

        if normalize_zone(item.item_zone):
            await _push_or_defer(item)

    return {"client_id": item.client_id, "was_created": True}
