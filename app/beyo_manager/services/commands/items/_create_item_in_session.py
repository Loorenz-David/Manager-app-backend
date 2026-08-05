from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemStateEnum
from beyo_manager.domain.items.location_push import normalize_zone
from beyo_manager.domain.sku_templates.events import SkuTemplateEvent
from beyo_manager.domain.tasks.enums import TaskTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.services.commands.location_tracker.enqueue_item_zone_push import (
    enqueue_item_zone_location_push,
)
from beyo_manager.services.commands.sku_templates._allocate_sku_scalar_in_session import (
    allocate_sku_scalar_in_session,
)
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


async def create_item_in_session(
    session: AsyncSession,
    *,
    workspace_id: str,
    user_id: str,
    username: str,
    client_id: str | None = None,
    article_number: str | None = None,
    sku: str | None = None,
    sku_template_task_type: TaskTypeEnum | None = None,
    item_category_id: str | None = None,
    quantity: int = 1,
    designer: str | None = None,
    height_in_cm: int | None = None,
    width_in_cm: int | None = None,
    depth_in_cm: int | None = None,
    item_value_minor: int | None = None,
    item_cost_minor: int | None = None,
    item_currency: ItemCurrencyEnum | None = None,
    item_position: str | None = None,
    item_zone: str | None = None,
    external_id: str | None = None,
    external_url: str | None = None,
    external_source: str | None = None,
    external_order_id: str | None = None,
    needs_fixing: bool | None = None,
) -> tuple[Item, list]:
    """Build, add, and flush a new Item row. Always creates — this never looks up an existing
    item the way find_or_create_item does, so callers must only reach for this when they
    genuinely want a new row (or are relying on sku_template_task_type as the item's only
    source of identity, which can't be matched against anything pre-existing anyway).

    Must run inside the caller's own maybe_begin transaction block. This function neither
    commits nor dispatches events — callers own the transaction and must dispatch the
    returned events themselves once it commits, same convention as every other *_in_session
    helper in this codebase.

    Returns (item, pending_events) — pending_events holds a SkuTemplateEvent.SCALAR_RESERVED
    event when sku_template_task_type supplied the sku, otherwise it's empty.
    """
    pending_events: list = []
    item_kwargs: dict[str, str] = {}
    if client_id is not None:
        validate_provided_client_id(client_id, "itm")
        existing = await session.get(Item, client_id)
        if existing is not None:
            raise ConflictError("Provided client_id is already in use.")
        item_kwargs["client_id"] = client_id

    item_category_snapshot: str | None = None
    item_major_category_snapshot: str | None = None
    if item_category_id is not None:
        category_result = await session.execute(
            select(ItemCategory).where(
                ItemCategory.workspace_id == workspace_id,
                ItemCategory.client_id == item_category_id,
                ItemCategory.is_deleted.is_(False),
            )
        )
        category = category_result.scalar_one_or_none()
        if category is None:
            raise NotFound("ItemCategory not found.")
        item_category_snapshot = category.name
        item_major_category_snapshot = category.major_category.value

    resolved_sku = sku
    if resolved_sku is None and sku_template_task_type is not None:
        resolved_sku, sku_template_id, reserved_scalar = await allocate_sku_scalar_in_session(
            session,
            workspace_id=workspace_id,
            task_type=sku_template_task_type,
            user_id=user_id,
        )
        pending_events.append(
            WorkspaceEvent(
                event_name=SkuTemplateEvent.SCALAR_RESERVED,
                client_id=sku_template_id,
                workspace_id=workspace_id,
                extra={"last_scalar": reserved_scalar},
            )
        )

    item = Item(
        **item_kwargs,
        workspace_id=workspace_id,
        article_number=article_number,
        sku=resolved_sku,
        state=ItemStateEnum.PENDING,
        item_category_id=item_category_id,
        quantity=quantity,
        designer=designer,
        height_in_cm=height_in_cm,
        width_in_cm=width_in_cm,
        depth_in_cm=depth_in_cm,
        item_value_minor=item_value_minor,
        item_cost_minor=item_cost_minor,
        item_currency=item_currency,
        item_position=item_position,
        item_zone=item_zone,
        external_id=external_id,
        external_url=external_url,
        external_source=external_source,
        external_order_id=external_order_id,
        item_category_snapshot=item_category_snapshot,
        item_major_category_snapshot=item_major_category_snapshot,
        created_by_id=user_id,
    )
    session.add(item)
    await session.flush()

    if normalize_zone(item.item_zone):
        await enqueue_item_zone_location_push(
            session,
            item,
            username=username,
            requested_by_user_id=user_id,
            needs_fixing=needs_fixing,
        )

    return item, pending_events
