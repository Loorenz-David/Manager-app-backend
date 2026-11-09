"""GET /integrations/shopify/products/by-item/{item_client_id} and the shared
item → product resolution used by the sync worker."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from beyo_manager.config import settings
from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationStatusEnum,
    ShopifyProductSyncItemStatusEnum,
    ShopifyProductSyncOriginEnum,
)
from beyo_manager.errors.external_service import ShopifyGraphQLRetryableError
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.shopify.shopify_product_sync_item import ShopifyProductSyncItem
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.shopify import _resolve_item_shopify_product as resolver
from beyo_manager.services.queries.shopify import get_item_shopify_product as module

_SNAPSHOT = {
    "shopify_product_id": "gid://shopify/Product/1",
    "title": "Chair",
    "description_html": "<p>Soft</p>",
    "status": "ACTIVE",
    "sku": "SKU-1",
    "barcode": None,
    "metafields": [{"key": "material", "type": "single_line_text_field", "value": "oak"}],
    "inventory": [{"location_id": "gid://shopify/Location/1", "quantity": 2}],
}


@pytest.fixture(autouse=True)
def _outbound_enabled(monkeypatch):
    monkeypatch.setattr(settings, "outbound_integrations_enabled", True)


async def _seed(db_session, *, article_number: str | None = None):
    suffix = uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    shop = ShopifyShopIntegration(
        workspace_id=workspace.client_id,
        shop_domain=f"shop-{suffix}.myshopify.com",
        provider="shopify",
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        access_token_encrypted="encrypted-token",
        granted_scopes=["write_products"],
        requested_scopes=["write_products"],
        api_version="2026-01",
        installed_at=now,
        last_connected_at=now,
        created_by_id=user.client_id,
        updated_by_id=user.client_id,
        created_at=now,
        updated_at=now,
    )
    item = Item(
        client_id=f"itm_{suffix}",
        workspace_id=workspace.client_id,
        created_by_id=user.client_id,
        article_number=article_number,
    )
    db_session.add_all([shop, item])
    await db_session.flush()
    return workspace, user, shop, item


def _sync_row(workspace, shop, item, *, status, product_id=None, created_at=None, legacy=False):
    return ShopifyProductSyncItem(
        workspace_id=workspace.client_id,
        shop_integration_id=shop.client_id,
        frontend_client_id=item.client_id,
        status=status,
        sync_origin=ShopifyProductSyncOriginEnum.STANDARD_PRODUCT_SYNC.value,
        source_entity_type=None if legacy else "item",
        source_entity_id=None if legacy else item.client_id,
        normalized_payload_json={"product": {"title": "Chair"}},
        shopify_product_id=product_id,
        created_at=created_at or datetime.now(timezone.utc),
    )


def _ctx(db_session, workspace, user, item_client_id: str) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace.client_id, "user_id": user.client_id, "role_name": "worker"},
        incoming_data={"item_client_id": item_client_id},
        session=db_session,
    )


@pytest.mark.integration
async def test_no_sync_rows_and_no_article_number_returns_empty_shop_entry(db_session, monkeypatch) -> None:
    workspace, user, shop, item = await _seed(db_session)

    async def _unexpected(**_kwargs):
        raise AssertionError("nothing to look up")

    monkeypatch.setattr(module, "get_shopify_product_snapshot", _unexpected)
    monkeypatch.setattr(module, "find_product_variant_by_identity", _unexpected)

    result = await module.get_item_shopify_product(_ctx(db_session, workspace, user, item.client_id))

    assert result["item_client_id"] == item.client_id
    assert result["shops"] == [
        {
            "shop_integration_id": shop.client_id,
            "shop_domain": shop.shop_domain,
            "sync": None,
            "product": None,
            "fetch_error": None,
        }
    ]


@pytest.mark.integration
async def test_pending_sync_is_reported_without_product(db_session, monkeypatch) -> None:
    workspace, user, shop, item = await _seed(db_session)
    db_session.add(_sync_row(workspace, shop, item, status=ShopifyProductSyncItemStatusEnum.PENDING))
    await db_session.flush()

    result = await module.get_item_shopify_product(_ctx(db_session, workspace, user, item.client_id))

    entry = result["shops"][0]
    assert entry["sync"]["status"] == "pending"
    assert entry["product"] is None


@pytest.mark.integration
async def test_succeeded_sync_returns_live_snapshot_of_newest_known_product(db_session, monkeypatch) -> None:
    workspace, user, shop, item = await _seed(db_session)
    old = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.add_all(
        [
            _sync_row(
                workspace, shop, item,
                status=ShopifyProductSyncItemStatusEnum.SUCCEEDED,
                product_id="gid://shopify/Product/old",
                created_at=old,
                legacy=True,
            ),
            _sync_row(
                workspace, shop, item,
                status=ShopifyProductSyncItemStatusEnum.SUCCEEDED,
                product_id="gid://shopify/Product/1",
            ),
        ]
    )
    await db_session.flush()
    requested: list[str] = []

    async def _snapshot(*, shopify_product_id, **_kwargs):
        requested.append(shopify_product_id)
        return dict(_SNAPSHOT)

    monkeypatch.setattr(module, "get_shopify_product_snapshot", _snapshot)

    result = await module.get_item_shopify_product(_ctx(db_session, workspace, user, item.client_id))

    entry = result["shops"][0]
    assert requested == ["gid://shopify/Product/1"]
    assert entry["sync"]["status"] == "succeeded"
    assert entry["product"] == _SNAPSHOT
    assert entry["fetch_error"] is None


@pytest.mark.integration
async def test_deleted_known_product_falls_back_to_barcode(db_session, monkeypatch) -> None:
    workspace, user, shop, item = await _seed(db_session, article_number="ART-9")
    db_session.add(
        _sync_row(
            workspace, shop, item,
            status=ShopifyProductSyncItemStatusEnum.SUCCEEDED,
            product_id="gid://shopify/Product/deleted",
        )
    )
    await db_session.flush()

    async def _snapshot(*, shopify_product_id, **_kwargs):
        if shopify_product_id == "gid://shopify/Product/deleted":
            return None
        return {**_SNAPSHOT, "shopify_product_id": shopify_product_id}

    async def _find(*, barcode, **_kwargs):
        assert barcode == "ART-9"
        return [
            {
                "id": "gid://shopify/ProductVariant/7",
                "barcode": "ART-9",
                "product": {"id": "gid://shopify/Product/7"},
            }
        ]

    monkeypatch.setattr(module, "get_shopify_product_snapshot", _snapshot)
    monkeypatch.setattr(module, "find_product_variant_by_identity", _find)

    result = await module.get_item_shopify_product(_ctx(db_session, workspace, user, item.client_id))

    assert result["shops"][0]["product"]["shopify_product_id"] == "gid://shopify/Product/7"


@pytest.mark.integration
async def test_shopify_failure_is_reported_per_shop(db_session, monkeypatch) -> None:
    workspace, user, shop, item = await _seed(db_session)
    db_session.add(
        _sync_row(
            workspace, shop, item,
            status=ShopifyProductSyncItemStatusEnum.SUCCEEDED,
            product_id="gid://shopify/Product/1",
        )
    )
    await db_session.flush()

    async def _boom(**_kwargs):
        raise ShopifyGraphQLRetryableError("throttled", error_code="throttled")

    monkeypatch.setattr(module, "get_shopify_product_snapshot", _boom)

    result = await module.get_item_shopify_product(_ctx(db_session, workspace, user, item.client_id))

    entry = result["shops"][0]
    assert entry["product"] is None
    assert entry["fetch_error"] == "Could not read the product from Shopify."
    assert entry["sync"]["status"] == "succeeded"


@pytest.mark.integration
async def test_unknown_item_is_not_found(db_session) -> None:
    workspace, user, _shop, _item = await _seed(db_session)

    with pytest.raises(NotFound):
        await module.get_item_shopify_product(_ctx(db_session, workspace, user, "itm_missing"))


@pytest.mark.integration
async def test_resolve_known_item_product_uses_newest_row_with_product_and_skips_current(
    db_session, monkeypatch
) -> None:
    workspace, _user, shop, item = await _seed(db_session)
    old = datetime.now(timezone.utc) - timedelta(hours=1)
    failed_with_product = _sync_row(
        workspace, shop, item,
        status=ShopifyProductSyncItemStatusEnum.FAILED,
        product_id="gid://shopify/Product/created-then-failed",
        created_at=old,
    )
    current = _sync_row(workspace, shop, item, status=ShopifyProductSyncItemStatusEnum.PROCESSING)
    db_session.add_all([failed_with_product, current])
    await db_session.flush()
    requested: list[str] = []

    async def _core(*, shopify_product_id, **_kwargs):
        requested.append(shopify_product_id)
        return {
            "shopify_product_id": shopify_product_id,
            "shopify_variant_id": "gid://shopify/ProductVariant/1",
            "shopify_inventory_item_id": None,
        }

    monkeypatch.setattr(resolver, "get_shopify_product_core", _core)

    known = await resolver.resolve_known_item_product(
        db_session,
        workspace_id=workspace.client_id,
        item_client_id=item.client_id,
        shop=shop,
        exclude_sync_item_id=current.client_id,
    )

    # A failed row that already created the product still counts.
    assert requested == ["gid://shopify/Product/created-then-failed"]
    assert known["shopify_product_id"] == "gid://shopify/Product/created-then-failed"
