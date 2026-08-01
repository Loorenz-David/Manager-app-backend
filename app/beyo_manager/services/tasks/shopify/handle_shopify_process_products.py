from __future__ import annotations

import logging

from sqlalchemy import select

from beyo_manager.domain.execution.payloads.shopify import ShopifyProcessProductsPayload
from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventSeverityEnum,
    ShopifyIntegrationEventTypeEnum,
    ShopifyIntegrationStatusEnum,
    ShopifyProductSyncOriginEnum,
    ShopifyProductSyncItemStatusEnum,
)
from beyo_manager.errors.external_service import ShopifyGraphQLRetryableError
from beyo_manager.services.commands.shopify._events import create_shopify_integration_event
from beyo_manager.models.tables.shopify.shopify_product_sync_item import ShopifyProductSyncItem
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.services.infra.execution.db import task_db_session
from beyo_manager.services.tasks.shopify._product_sync_orchestrator import sync_one_product_sync_item
from beyo_manager.services.infra.events.realtime_push import push_workspace_refresh

logger = logging.getLogger(__name__)

SHOPIFY_PRODUCTS_SYNCED_EVENT = "shopify.products.synced"
SHOPIFY_PREORDER_PROCESSED_EVENT = "shopify.preorder.processed"


async def handle_shopify_process_products(raw: dict, task_client_id: str) -> None:
    payload = ShopifyProcessProductsPayload(**raw)
    succeeded: list[dict] = []
    failed: list[dict] = []
    standard_rows: list[ShopifyProductSyncItem] = []
    preorder_rows: list[ShopifyProductSyncItem] = []

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
        # Validate the entire batch before resolving shops or making any Shopify
        # request. A producer deployed ahead of this worker must cause a retry,
        # never be silently treated as a standard sync.
        origins_by_id = {
            row.client_id: _resolve_sync_origin(row)
            for row in rows
        }

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
            origin = origins_by_id[row.client_id]

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
                _record_completion(
                    row,
                    origin=origin,
                    standard_rows=standard_rows,
                    preorder_rows=preorder_rows,
                    succeeded=succeeded,
                    failed=failed,
                )
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
                _record_completion(
                    row,
                    origin=origin,
                    standard_rows=standard_rows,
                    preorder_rows=preorder_rows,
                    succeeded=succeeded,
                    failed=failed,
                )
                continue

            try:
                await sync_one_product_sync_item(session, sync_item=row, shop=shop)
            except ShopifyGraphQLRetryableError:
                await session.rollback()
                logger.warning(
                    "shopify_process_products | retryable_shopify_error | "
                    "task_id=%s sync_item_id=%s shop_integration_id=%s",
                    task_client_id,
                    row.client_id,
                    row.shop_integration_id,
                    exc_info=True,
                )
                raise
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

            _record_completion(
                row,
                origin=origin,
                standard_rows=standard_rows,
                preorder_rows=preorder_rows,
                succeeded=succeeded,
                failed=failed,
            )

        # Every producer receives an origin-specific terminal audit event. Socket
        # routing below uses the same explicit origin and never inventory behavior.
        for row in standard_rows:
            await _write_standard_terminal_event(session, row=row)
        for row in preorder_rows:
            await _write_preorder_terminal_event(session, row=row)
        if standard_rows or preorder_rows:
            await session.commit()

    if succeeded or failed:
        await push_workspace_refresh(
            payload.workspace_id,
            SHOPIFY_PRODUCTS_SYNCED_EVENT,
            {
                "task_id": task_client_id,
                "succeeded": succeeded,
                "failed": failed,
            },
        )
    for row in preorder_rows:
        await push_workspace_refresh(
            payload.workspace_id,
            SHOPIFY_PREORDER_PROCESSED_EVENT,
            _preorder_entry(row, task_client_id=task_client_id),
        )


def _resolve_sync_origin(
    row: ShopifyProductSyncItem,
) -> ShopifyProductSyncOriginEnum:
    try:
        return ShopifyProductSyncOriginEnum(row.sync_origin)
    except (TypeError, ValueError) as exc:
        logger.error(
            "shopify_process_products | unknown_sync_origin | "
            "sync_item_id=%s sync_origin=%r",
            row.client_id,
            row.sync_origin,
        )
        raise RuntimeError(
            f"Unsupported Shopify product sync origin: {row.sync_origin!r}"
        ) from exc


def _record_completion(
    row: ShopifyProductSyncItem,
    *,
    origin: ShopifyProductSyncOriginEnum,
    standard_rows: list[ShopifyProductSyncItem],
    preorder_rows: list[ShopifyProductSyncItem],
    succeeded: list[dict],
    failed: list[dict],
) -> None:
    if origin == ShopifyProductSyncOriginEnum.PREORDER_TASK:
        preorder_rows.append(row)
        return
    if origin == ShopifyProductSyncOriginEnum.STANDARD_PRODUCT_SYNC:
        standard_rows.append(row)
        if row.status == ShopifyProductSyncItemStatusEnum.SUCCEEDED:
            succeeded.append(_success_entry(row))
        else:
            failed.append(_failure_entry(row))
        return
    # Kept as a guard if the enum gains a value before this dispatch policy is
    # updated. This branch runs before emitting a wrongly classified result.
    raise RuntimeError(f"No completion policy for Shopify sync origin {origin.value!r}")


async def _write_standard_terminal_event(
    session,
    *,
    row: ShopifyProductSyncItem,
) -> None:
    succeeded = row.status == ShopifyProductSyncItemStatusEnum.SUCCEEDED
    operation = row.requested_operation.value if row.requested_operation else None
    await create_shopify_integration_event(
        session,
        workspace_id=row.workspace_id,
        shop_integration_id=row.shop_integration_id,
        event_type=ShopifyIntegrationEventTypeEnum.PRODUCT_SYNC,
        severity=(
            ShopifyIntegrationEventSeverityEnum.INFO
            if succeeded
            else ShopifyIntegrationEventSeverityEnum.ERROR
        ),
        message=(
            "Shopify product sync completed."
            if succeeded
            else f"Shopify product sync failed: {row.error_code or 'unknown_error'}."
        ),
        metadata_json={
            "frontend_client_id": row.frontend_client_id,
            "sync_item_client_id": row.client_id,
            "status": row.status.value,
            "requested_operation": operation,
            "shopify_product_id": row.shopify_product_id,
            "error_code": row.error_code,
            "sync_origin": row.sync_origin,
        },
        created_by_id=row.created_by_id,
    )


async def _write_preorder_terminal_event(session, *, row: ShopifyProductSyncItem) -> None:
    succeeded = row.status == ShopifyProductSyncItemStatusEnum.SUCCEEDED
    operation = row.requested_operation.value if row.requested_operation else None
    if succeeded:
        message = (
            "Shopify pre-order product updated."
            if operation == "update"
            else "Shopify pre-order product created."
        )
    else:
        message = f"Shopify pre-order product failed: {row.error_code or 'unknown_error'}."

    await create_shopify_integration_event(
        session,
        workspace_id=row.workspace_id,
        shop_integration_id=row.shop_integration_id,
        event_type=ShopifyIntegrationEventTypeEnum.PREORDER,
        severity=(
            ShopifyIntegrationEventSeverityEnum.INFO
            if succeeded
            else ShopifyIntegrationEventSeverityEnum.ERROR
        ),
        message=message,
        # IDs, codes and status only — no customer data, no tokens, no raw Shopify responses.
        metadata_json={
            "task_id": row.source_entity_id or row.frontend_client_id,
            "preorder_operation_id": row.client_id,
            "status": row.status.value,
            "requested_operation": operation,
            "shopify_product_id": row.shopify_product_id,
            "error_code": row.error_code,
        },
        created_by_id=row.created_by_id,
    )


def _success_entry(row: ShopifyProductSyncItem) -> dict:
    result = {
        "frontend_client_id": row.frontend_client_id,
        "shop_integration_id": row.shop_integration_id,
        "sync_item_client_id": row.client_id,
        "requested_operation": row.requested_operation.value if row.requested_operation else None,
        "shopify_product_id": row.shopify_product_id,
        "shopify_variant_id": row.shopify_variant_id,
    }
    if getattr(row, "inventory_result_json", None) is not None:
        result["inventory"] = row.inventory_result_json
    return result


def _failure_entry(row: ShopifyProductSyncItem) -> dict:
    result = {
        "frontend_client_id": row.frontend_client_id,
        "shop_integration_id": row.shop_integration_id,
        "sync_item_client_id": row.client_id,
        "requested_operation": row.requested_operation.value if row.requested_operation else None,
        "error_code": row.error_code,
        "error_message": row.error_message,
    }
    if getattr(row, "inventory_result_json", None) is not None:
        result["inventory"] = row.inventory_result_json
    return result


def _preorder_entry(
    row: ShopifyProductSyncItem,
    *,
    task_client_id: str,
) -> dict:
    return {
        "task_id": row.source_entity_id or row.frontend_client_id,
        "shopify_task_id": task_client_id,
        "preorder_operation_id": row.client_id,
        "shop_integration_id": row.shop_integration_id,
        "status": row.status.value,
        "requested_operation": (
            row.requested_operation.value if row.requested_operation else None
        ),
        "shopify_product_id": row.shopify_product_id,
        "shopify_variant_id": row.shopify_variant_id,
        "shopify_media_id": row.shopify_media_id,
        "media_status": row.media_status,
        "inventory": row.inventory_result_json,
        "error_code": row.error_code,
        "error_message": row.error_message,
    }
