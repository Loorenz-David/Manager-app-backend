"""Resolve which Shopify product a ManagerBeyo item is linked to, per shop.

The link is the newest product-sync row for the (item, shop) pair that holds a
``shopify_product_id``. Rows created by the worker product form carry
``source_entity_type="item"``; rows written before that link existed are
standard syncs whose ``frontend_client_id`` is the item's client id.
"""

from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.shopify.enums import ShopifyProductSyncOriginEnum
from beyo_manager.models.tables.shopify.shopify_product_sync_item import ShopifyProductSyncItem
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.services.infra.shopify.product_sync_client import get_shopify_product_core

ITEM_SOURCE_ENTITY_TYPE = "item"


def item_client_id_for_sync_row(row: ShopifyProductSyncItem) -> str | None:
    """Return the item a sync row belongs to, or None for non-item syncs."""
    if row.source_entity_type == ITEM_SOURCE_ENTITY_TYPE:
        return row.source_entity_id
    if (
        row.source_entity_type is None
        and row.sync_origin == ShopifyProductSyncOriginEnum.STANDARD_PRODUCT_SYNC.value
    ):
        return row.frontend_client_id
    return None


def _item_rows_condition(*, workspace_id: str, item_client_id: str, shop_integration_id: str):
    return and_(
        ShopifyProductSyncItem.workspace_id == workspace_id,
        ShopifyProductSyncItem.shop_integration_id == shop_integration_id,
        or_(
            and_(
                ShopifyProductSyncItem.source_entity_type == ITEM_SOURCE_ENTITY_TYPE,
                ShopifyProductSyncItem.source_entity_id == item_client_id,
            ),
            and_(
                ShopifyProductSyncItem.source_entity_type.is_(None),
                ShopifyProductSyncItem.sync_origin
                == ShopifyProductSyncOriginEnum.STANDARD_PRODUCT_SYNC.value,
                ShopifyProductSyncItem.frontend_client_id == item_client_id,
            ),
        ),
    )


async def find_latest_item_sync_row(
    session: AsyncSession,
    *,
    workspace_id: str,
    item_client_id: str,
    shop_integration_id: str,
    with_product_id: bool = False,
    exclude_sync_item_id: str | None = None,
) -> ShopifyProductSyncItem | None:
    conditions = [
        _item_rows_condition(
            workspace_id=workspace_id,
            item_client_id=item_client_id,
            shop_integration_id=shop_integration_id,
        )
    ]
    if with_product_id:
        conditions.append(ShopifyProductSyncItem.shopify_product_id.is_not(None))
    if exclude_sync_item_id is not None:
        conditions.append(ShopifyProductSyncItem.client_id != exclude_sync_item_id)
    return (
        await session.execute(
            select(ShopifyProductSyncItem)
            .where(*conditions)
            .order_by(ShopifyProductSyncItem.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def resolve_known_item_product(
    session: AsyncSession,
    *,
    workspace_id: str,
    item_client_id: str,
    shop: ShopifyShopIntegration,
    exclude_sync_item_id: str | None = None,
) -> dict | None:
    """Return the core ids of the product previously synced for this item.

    Any status counts: a row that failed after creating the product still holds
    a product that must be updated rather than duplicated. Returns None when no
    earlier row exists or the product was deleted from Shopify.
    """
    row = await find_latest_item_sync_row(
        session,
        workspace_id=workspace_id,
        item_client_id=item_client_id,
        shop_integration_id=shop.client_id,
        with_product_id=True,
        exclude_sync_item_id=exclude_sync_item_id,
    )
    if row is None or not row.shopify_product_id:
        return None
    return await get_shopify_product_core(
        shop_domain=shop.shop_domain,
        access_token_encrypted=shop.access_token_encrypted or "",
        shopify_product_id=row.shopify_product_id,
    )
