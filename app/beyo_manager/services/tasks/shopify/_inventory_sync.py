from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.shopify.enums import ShopifyInventoryAdjustmentStatusEnum
from beyo_manager.domain.shopify.scopes import has_all_required_scopes
from beyo_manager.errors.external_service import ShopifyGraphQLNonRetryableError, ShopifyGraphQLError
from beyo_manager.models.tables.shopify.shopify_inventory_adjustment import ShopifyInventoryAdjustment
from beyo_manager.models.tables.shopify.shopify_product_sync_item import ShopifyProductSyncItem
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.services.infra.shopify.inventory_client import (
    activate_inventory_at_location,
    adjust_inventory_quantities,
    enable_inventory_tracking,
    fetch_shop_locations,
    resolve_inventory_item_state,
)

logger = logging.getLogger(__name__)

_REQUIRED_INVENTORY_SCOPES = ("read_locations", "write_inventory")


async def sync_inventory_adjustments(
    session: AsyncSession,
    *,
    sync_item: ShopifyProductSyncItem,
    shop: ShopifyShopIntegration,
    inventory_item_id: str | None,
    adjustments: list[dict],
) -> dict:
    if not adjustments:
        return {"adjustments": []}
    if not has_all_required_scopes(_REQUIRED_INVENTORY_SCOPES, shop.granted_scopes or ()):
        summary = _failed_summary(adjustments, "missing_inventory_scope")
        sync_item.inventory_result_json = summary
        await session.commit()
        raise _inventory_error(
            "missing_inventory_scope",
            "Shopify inventory access needs reauthorization before inventory can be updated.",
        )
    if not inventory_item_id:
        summary = _failed_summary(adjustments, "inventory_item_unresolved")
        sync_item.inventory_result_json = summary
        await session.commit()
        raise _inventory_error("inventory_item_unresolved", "Shopify inventory item could not be resolved.")

    locations = await fetch_shop_locations(
        shop_domain=shop.shop_domain,
        access_token_encrypted=shop.access_token_encrypted or "",
    )
    owned_location_ids = {location["location_id"] for location in locations}
    missing_location_ids = [
        adjustment["location_id"]
        for adjustment in adjustments
        if adjustment["location_id"] not in owned_location_ids
    ]
    if missing_location_ids:
        summary = _failed_summary(adjustments, "location_not_in_shop")
        sync_item.inventory_result_json = summary
        await session.commit()
        raise _inventory_error(
            "location_not_in_shop",
            "One or more Shopify locations do not belong to this shop.",
        )

    claimed_rows: list[tuple[ShopifyInventoryAdjustment, dict]] = []
    summary_entries: list[dict] = []
    for adjustment in adjustments:
        ledger = await _claim_ledger_row(
            session,
            sync_item=sync_item,
            shop=shop,
            inventory_item_id=inventory_item_id,
            adjustment=adjustment,
        )
        if ledger.requested_delta != adjustment["quantity_to_add"]:
            entry = _summary_entry(adjustment, "failed", "inventory_adjustment_conflict")
            summary_entries.append(entry)
            sync_item.inventory_result_json = {"adjustments": summary_entries}
            await session.commit()
            raise _inventory_error(
                "inventory_adjustment_conflict",
                "This item already has an inventory adjustment with a different quantity.",
            )

        if ledger.status == ShopifyInventoryAdjustmentStatusEnum.APPLIED:
            summary_entries.append(_summary_entry(adjustment, "already_applied", None))
            continue

        state = await resolve_inventory_item_state(
            shop_domain=shop.shop_domain,
            access_token_encrypted=shop.access_token_encrypted or "",
            inventory_item_id=inventory_item_id,
            location_id=adjustment["location_id"],
        )
        if (
            ledger.status == ShopifyInventoryAdjustmentStatusEnum.PENDING
            and ledger.baseline_available is not None
            and state["available"] == ledger.baseline_available + ledger.requested_delta
        ):
            ledger.status = ShopifyInventoryAdjustmentStatusEnum.APPLIED
            ledger.applied_at = datetime.now(timezone.utc)
            ledger.shopify_error_code = None
            summary_entries.append(_summary_entry(adjustment, "already_applied", None))
            await session.commit()
            continue

        ledger.baseline_available = state["available"]
        ledger.status = ShopifyInventoryAdjustmentStatusEnum.PENDING
        ledger.shopify_error_code = None
        await session.commit()

        logger.info(
            "shopify_inventory_diag | plan | sync_item_id=%s inventory_item_id=%s location_id=%s "
            "tracked_before=%s will_enable_tracking=%s level_exists=%s will_activate=%s "
            "requested_delta=%s baseline_available=%s",
            sync_item.client_id,
            inventory_item_id,
            adjustment["location_id"],
            state["tracked"],
            not state["tracked"],
            state["level_exists"],
            not state["level_exists"],
            adjustment["quantity_to_add"],
            state["available"],
        )

        try:
            if not state["tracked"]:
                await enable_inventory_tracking(
                    shop_domain=shop.shop_domain,
                    access_token_encrypted=shop.access_token_encrypted or "",
                    inventory_item_id=inventory_item_id,
                )
                state["tracked"] = True
            if not state["level_exists"]:
                await activate_inventory_at_location(
                    shop_domain=shop.shop_domain,
                    access_token_encrypted=shop.access_token_encrypted or "",
                    inventory_item_id=inventory_item_id,
                    location_id=adjustment["location_id"],
                    idempotency_key=ledger.client_id,
                )
        except ShopifyGraphQLError as exc:
            ledger.status = ShopifyInventoryAdjustmentStatusEnum.FAILED
            ledger.shopify_error_code = exc.error_code
            summary_entries.append(_summary_entry(adjustment, "failed", exc.error_code))
            sync_item.inventory_result_json = {"adjustments": summary_entries}
            await session.commit()
            raise

        claimed_rows.append((ledger, adjustment))

    if claimed_rows:
        changes = [
            {
                "inventory_item_id": inventory_item_id,
                "location_id": adjustment["location_id"],
                "quantity_to_add": adjustment["quantity_to_add"],
            }
            for _ledger, adjustment in claimed_rows
        ]
        first_ledger = claimed_rows[0][0]
        try:
            await adjust_inventory_quantities(
                shop_domain=shop.shop_domain,
                access_token_encrypted=shop.access_token_encrypted or "",
                changes=changes,
                reference_document_uri=first_ledger.reference_uri,
                idempotency_key=_batch_idempotency_key(claimed_rows),
            )
        except ShopifyGraphQLError as exc:
            for ledger, adjustment in claimed_rows:
                ledger.status = ShopifyInventoryAdjustmentStatusEnum.FAILED
                ledger.shopify_error_code = exc.error_code
                summary_entries.append(_summary_entry(adjustment, "failed", exc.error_code))
            sync_item.inventory_result_json = {"adjustments": summary_entries}
            await session.commit()
            raise
        for ledger, adjustment in claimed_rows:
            ledger.status = ShopifyInventoryAdjustmentStatusEnum.APPLIED
            ledger.shopify_error_code = None
            ledger.applied_at = datetime.now(timezone.utc)
            summary_entries.append(_summary_entry(adjustment, "applied", None))
        await session.commit()

    summary = {"adjustments": summary_entries}
    sync_item.inventory_result_json = summary
    await session.commit()
    logger.info(
        "shopify_inventory | completed | shop_integration_id=%s sync_item_id=%s inventory_item_id=%s adjustment_count=%s",
        shop.client_id,
        sync_item.client_id,
        inventory_item_id,
        len(adjustments),
    )
    return summary


async def _claim_ledger_row(
    session: AsyncSession,
    *,
    sync_item: ShopifyProductSyncItem,
    shop: ShopifyShopIntegration,
    inventory_item_id: str,
    adjustment: dict,
) -> ShopifyInventoryAdjustment:
    values = {
        "workspace_id": sync_item.workspace_id,
        "shop_integration_id": shop.client_id,
        "sync_item_id": sync_item.client_id,
        "frontend_client_id": sync_item.frontend_client_id,
        "shopify_inventory_item_id": inventory_item_id,
        "shopify_location_id": adjustment["location_id"],
        "requested_delta": adjustment["quantity_to_add"],
        "status": ShopifyInventoryAdjustmentStatusEnum.PENDING,
        "reference_uri": f"managerbeyo://inventory-adjustment/{sync_item.frontend_client_id}/{adjustment['location_id'].rsplit('/', 1)[-1]}",
        "created_by_id": sync_item.created_by_id,
    }
    await session.execute(
        pg_insert(ShopifyInventoryAdjustment)
        .values(**values)
        .on_conflict_do_nothing(
            index_elements=[
                ShopifyInventoryAdjustment.shop_integration_id,
                ShopifyInventoryAdjustment.frontend_client_id,
                ShopifyInventoryAdjustment.shopify_location_id,
            ]
        )
    )
    row = (
        await session.execute(
            select(ShopifyInventoryAdjustment).where(
                ShopifyInventoryAdjustment.shop_integration_id == shop.client_id,
                ShopifyInventoryAdjustment.frontend_client_id == sync_item.frontend_client_id,
                ShopifyInventoryAdjustment.shopify_location_id == adjustment["location_id"],
            )
        )
    ).scalar_one()
    row.sync_item_id = sync_item.client_id
    return row


def _failed_summary(adjustments: list[dict], code: str) -> dict:
    return {"adjustments": [_summary_entry(adjustment, "failed", code) for adjustment in adjustments]}


def _summary_entry(adjustment: dict, outcome: str, error_code: str | None) -> dict:
    return {
        "location_id": adjustment["location_id"],
        "requested_delta": adjustment["quantity_to_add"],
        "outcome": outcome,
        "shopify_error_code": error_code,
    }


def _batch_idempotency_key(claimed_rows: list[tuple[ShopifyInventoryAdjustment, dict]]) -> str:
    return ":".join(sorted(row.client_id for row, _adjustment in claimed_rows))


def _inventory_error(code: str, message: str) -> ShopifyGraphQLNonRetryableError:
    return ShopifyGraphQLNonRetryableError(message, error_code=code)
