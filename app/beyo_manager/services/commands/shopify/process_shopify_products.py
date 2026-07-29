from __future__ import annotations

from dataclasses import asdict
import logging

from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.shopify import ShopifyProcessProductsPayload
from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventSeverityEnum,
    ShopifyIntegrationEventTypeEnum,
    ShopifyInventoryModeEnum,
    ShopifyProductSyncOriginEnum,
    ShopifyProductSyncItemStatusEnum,
)
from beyo_manager.models.tables.shopify.shopify_product_sync_item import ShopifyProductSyncItem
from beyo_manager.models.tables.images.image import Image
from beyo_manager.services.commands.shopify._events import create_shopify_integration_event
from beyo_manager.services.commands.shopify._product_sync_normalizer import resolve_and_normalize_sync_targets
from beyo_manager.services.commands.shopify.requests.process_shopify_products_request import (
    ProcessShopifyProductsRequest,
    parse_process_shopify_products_request,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.execution.task_factory import create_instant_task
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError


_MAX_SHOPIFY_IMAGE_BYTES = 20 * 1024 * 1024
_MAX_SHOPIFY_IMAGE_PIXELS = 25_000_000
_MAX_SHOPIFY_IMAGE_DIMENSION = 5_000

logger = logging.getLogger(__name__)


async def process_shopify_products(ctx: ServiceContext) -> dict:
    legacy_item_count = _legacy_inventory_item_count(ctx.incoming_data)
    if legacy_item_count:
        logger.warning(
            "shopify_product_sync | deprecated_inventory_request_converted | "
            "workspace_id=%s user_id=%s item_count=%s semantics=absolute",
            ctx.workspace_id,
            ctx.user_id,
            legacy_item_count,
        )
    request = parse_process_shopify_products_request(ctx.incoming_data)
    return await enqueue_shopify_product_sync(
        ctx,
        request=request,
        sync_origin=ShopifyProductSyncOriginEnum.STANDARD_PRODUCT_SYNC,
    )


async def enqueue_shopify_product_sync(
    ctx: ServiceContext,
    *,
    request: ProcessShopifyProductsRequest,
    sync_origin: ShopifyProductSyncOriginEnum,
    source_entity_type: str | None = None,
    source_entity_id: str | None = None,
) -> dict:
    """Persist a product-sync intent and its execution task in one transaction."""
    async with maybe_begin(ctx.session):
        await _validate_image_limits(ctx, request)
        targets = await resolve_and_normalize_sync_targets(
            ctx.session,
            workspace_id=ctx.workspace_id,
            request=request,
        )

        sync_items = [
            ShopifyProductSyncItem(
                workspace_id=ctx.workspace_id,
                shop_integration_id=shop.client_id,
                frontend_client_id=item.client_id,
                status=ShopifyProductSyncItemStatusEnum.PENDING,
                sync_origin=sync_origin.value,
                source_entity_type=source_entity_type,
                source_entity_id=source_entity_id,
                # Retained for one compatibility release. Runtime execution is
                # absolute regardless of this legacy column.
                inventory_mode=ShopifyInventoryModeEnum.SET,
                normalized_payload_json=normalized_payload,
                created_by_id=ctx.user_id,
            )
            for shop, item, normalized_payload in targets
        ]
        ctx.session.add_all(sync_items)
        await ctx.session.flush()

        distinct_shops: dict[str, object] = {}
        for shop, _item, _payload in targets:
            distinct_shops.setdefault(shop.client_id, shop)
        rows_by_shop: dict[str, list[ShopifyProductSyncItem]] = {}
        for row in sync_items:
            rows_by_shop.setdefault(row.shop_integration_id, []).append(row)

        events = []
        for shop in distinct_shops.values():
            shop_rows = rows_by_shop[shop.client_id]
            event_type, message = _enqueue_event_policy(
                sync_origin,
                target_count=len(shop_rows),
            )
            metadata = {
                "item_count": len(request.items),
                "target_count": len(sync_items),
                "sync_origin": sync_origin.value,
            }
            if source_entity_type is not None:
                metadata["source_entity_type"] = source_entity_type
            if source_entity_id is not None:
                metadata["source_entity_id"] = source_entity_id
            if sync_origin == ShopifyProductSyncOriginEnum.PREORDER_TASK:
                metadata["task_id"] = source_entity_id
                metadata["preorder_operation_id"] = shop_rows[0].client_id
            events.append(
                await create_shopify_integration_event(
                    ctx.session,
                    workspace_id=ctx.workspace_id,
                    shop_integration_id=shop.client_id,
                    event_type=event_type,
                    severity=ShopifyIntegrationEventSeverityEnum.INFO,
                    message=message,
                    metadata_json=metadata,
                    created_by_id=ctx.user_id,
                )
            )

        task = await create_instant_task(
            session=ctx.session,
            task_type=TaskType.SHOPIFY_PROCESS_PRODUCTS,
            payload=asdict(
                ShopifyProcessProductsPayload(
                    workspace_id=ctx.workspace_id,
                    requested_by_user_id=ctx.user_id,
                    sync_item_client_ids=[row.client_id for row in sync_items],
                )
            ),
            event_client_id=events[0].client_id if events else None,
        )

        for event in events:
            event.metadata_json = {
                **(event.metadata_json or {}),
                "shopify_process_products_task_id": task.client_id,
            }

    return {
        "queued": True,
        "task_id": task.client_id,
        "sync_item_client_ids": [row.client_id for row in sync_items],
        "event_client_ids": [event.client_id for event in events],
        "target_count": len(sync_items),
    }


def _enqueue_event_policy(
    sync_origin: ShopifyProductSyncOriginEnum,
    *,
    target_count: int,
) -> tuple[ShopifyIntegrationEventTypeEnum, str]:
    if sync_origin == ShopifyProductSyncOriginEnum.STANDARD_PRODUCT_SYNC:
        return (
            ShopifyIntegrationEventTypeEnum.PRODUCT_SYNC,
            f"Product sync batch enqueued for {target_count} (item, shop) operations.",
        )
    if sync_origin == ShopifyProductSyncOriginEnum.PREORDER_TASK:
        return (
            ShopifyIntegrationEventTypeEnum.PREORDER,
            "Shopify pre-order product provisioning enqueued.",
        )
    raise ValueError(f"Unsupported Shopify product sync origin: {sync_origin!r}")


def _legacy_inventory_item_count(incoming_data: dict) -> int:
    items = incoming_data.get("items")
    if not isinstance(items, list):
        return 0
    return sum(
        1
        for item in items
        if isinstance(item, dict) and bool(item.get("inventory_adjustments"))
    )


async def _validate_image_limits(ctx: ServiceContext, request: object) -> None:
    image_ids = {
        item.image_id
        for item in request.items
        if item.image_id is not None
    }
    if not image_ids:
        return

    images = (
        await ctx.session.execute(
            select(Image).where(
                Image.client_id.in_(image_ids),
                Image.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    images_by_id = {image.client_id: image for image in images}
    if set(images_by_id) != image_ids:
        raise NotFound("Image not found.")

    for image in images:
        if (
            image.file_size_bytes is not None
            and image.file_size_bytes > _MAX_SHOPIFY_IMAGE_BYTES
        ):
            raise ValidationError("Shopify product images cannot exceed 20 MB.")
        if image.width_px is not None and image.height_px is not None:
            if (
                image.width_px > _MAX_SHOPIFY_IMAGE_DIMENSION
                or image.height_px > _MAX_SHOPIFY_IMAGE_DIMENSION
                or image.width_px * image.height_px > _MAX_SHOPIFY_IMAGE_PIXELS
            ):
                raise ValidationError(
                    "Shopify product images cannot exceed 25 MP or 5000×5000 pixels."
                )
