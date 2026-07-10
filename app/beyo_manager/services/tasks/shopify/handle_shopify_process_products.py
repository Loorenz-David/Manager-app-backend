from __future__ import annotations

import logging

from sqlalchemy import select

from beyo_manager.domain.execution.payloads.shopify import ShopifyProcessProductsPayload
from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum, ShopifyProductSyncItemStatusEnum
from beyo_manager.models.tables.shopify.shopify_product_sync_item import ShopifyProductSyncItem
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.services.infra.execution.db import task_db_session
from beyo_manager.services.tasks.shopify._product_sync_orchestrator import sync_one_product_sync_item
from beyo_manager.sockets.worker_emitter import emit_to_workspace_room

logger = logging.getLogger(__name__)

SHOPIFY_PRODUCTS_SYNCED_EVENT = "shopify.products.synced"


async def handle_shopify_process_products(raw: dict, task_client_id: str) -> None:
    payload = ShopifyProcessProductsPayload(**raw)
    succeeded: list[dict] = []
    failed: list[dict] = []

    async with task_db_session() as session:
        rows = (
            await session.execute(
                select(ShopifyProductSyncItem).where(
                    ShopifyProductSyncItem.client_id.in_(payload.sync_item_client_ids),
                    ShopifyProductSyncItem.workspace_id == payload.workspace_id,
                )
            )
        ).scalars().all()
        rows_by_id = {row.client_id: row for row in rows}

        shops = (
            await session.execute(
                select(ShopifyShopIntegration).where(
                    ShopifyShopIntegration.client_id.in_({row.shop_integration_id for row in rows}),
                    ShopifyShopIntegration.is_deleted.is_(False),
                    ShopifyShopIntegration.status == ShopifyIntegrationStatusEnum.ACTIVE,
                )
            )
        ).scalars().all()
        shops_by_id = {shop.client_id: shop for shop in shops}

        for sync_item_id in payload.sync_item_client_ids:
            row = rows_by_id.get(sync_item_id)
            if row is None:
                continue

            shop = shops_by_id.get(row.shop_integration_id)
            if shop is None:
                row.status = ShopifyProductSyncItemStatusEnum.FAILED
                row.error_code = "missing_shop_integration"
                row.error_message = "Shopify shop integration not found or no longer active."
                await session.commit()
                logger.warning(
                    "shopify_process_products | missing_or_inactive_shop_integration | "
                    "task_id=%s sync_item_id=%s shop_integration_id=%s",
                    task_client_id, row.client_id, row.shop_integration_id,
                )
                failed.append(_failure_entry(row))
                continue

            if not (shop.access_token_encrypted or "").strip():
                row.status = ShopifyProductSyncItemStatusEnum.FAILED
                row.error_code = "missing_access_token"
                row.error_message = "Shopify access token is not available."
                await session.commit()
                logger.warning(
                    "shopify_process_products | missing_access_token | task_id=%s sync_item_id=%s shop_integration_id=%s",
                    task_client_id, row.client_id, row.shop_integration_id,
                )
                failed.append(_failure_entry(row))
                continue

            try:
                await sync_one_product_sync_item(session, sync_item=row, shop=shop)
            except Exception as exc:
                await session.rollback()
                row.status = ShopifyProductSyncItemStatusEnum.FAILED
                row.error_code = "unexpected_error"
                row.error_message = str(exc)[:1024]
                await session.commit()
                logger.exception(
                    "shopify_process_products | unexpected_error | task_id=%s sync_item_id=%s shop_integration_id=%s",
                    task_client_id, row.client_id, row.shop_integration_id,
                )

            if row.status == ShopifyProductSyncItemStatusEnum.SUCCEEDED:
                succeeded.append(_success_entry(row))
            else:
                failed.append(_failure_entry(row))

    await emit_to_workspace_room(
        workspace_id=payload.workspace_id,
        event=SHOPIFY_PRODUCTS_SYNCED_EVENT,
        payload={
            "task_id": task_client_id,
            "succeeded": succeeded,
            "failed": failed,
        },
    )


def _success_entry(row: ShopifyProductSyncItem) -> dict:
    return {
        "frontend_client_id": row.frontend_client_id,
        "shop_integration_id": row.shop_integration_id,
        "sync_item_client_id": row.client_id,
        "requested_operation": row.requested_operation.value if row.requested_operation else None,
        "shopify_product_id": row.shopify_product_id,
        "shopify_variant_id": row.shopify_variant_id,
    }


def _failure_entry(row: ShopifyProductSyncItem) -> dict:
    return {
        "frontend_client_id": row.frontend_client_id,
        "shop_integration_id": row.shop_integration_id,
        "sync_item_client_id": row.client_id,
        "requested_operation": row.requested_operation.value if row.requested_operation else None,
        "error_code": row.error_code,
        "error_message": row.error_message,
    }
