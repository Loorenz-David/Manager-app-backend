from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.shopify import ShopifyProcessProductsPayload
from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventSeverityEnum,
    ShopifyIntegrationEventTypeEnum,
    ShopifyInventoryModeEnum,
    ShopifyProductSyncItemStatusEnum,
)
from beyo_manager.models.tables.shopify.shopify_product_sync_item import ShopifyProductSyncItem
from beyo_manager.models.tables.images.image import Image
from beyo_manager.services.commands.shopify._events import create_shopify_integration_event
from beyo_manager.services.commands.shopify._product_sync_normalizer import resolve_and_normalize_sync_targets
from beyo_manager.services.commands.shopify.requests.process_shopify_products_request import (
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


async def process_shopify_products(ctx: ServiceContext) -> dict:
    request = parse_process_shopify_products_request(ctx.incoming_data)

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

        events = []
        for shop in distinct_shops.values():
            events.append(
                await create_shopify_integration_event(
                    ctx.session,
                    workspace_id=ctx.workspace_id,
                    shop_integration_id=shop.client_id,
                    event_type=ShopifyIntegrationEventTypeEnum.PRODUCT_SYNC,
                    severity=ShopifyIntegrationEventSeverityEnum.INFO,
                    message=f"Product sync batch enqueued for {len(sync_items)} (item, shop) operations.",
                    metadata_json={
                        "item_count": len(request.items),
                        "target_count": len(sync_items),
                    },
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
        # One event per distinct target shop, in the same order as distinct_shops.
        # Returned so a subordinate caller can reclassify or annotate its own event
        # without re-querying by metadata — see _create_preorder_sync_item_in_session.
        "event_client_ids": [event.client_id for event in events],
        "target_count": len(sync_items),
    }


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
