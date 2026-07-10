from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from beyo_manager.domain.shopify.enums import ShopifyProductSyncItemStatusEnum, ShopifyProductSyncOperationEnum
from beyo_manager.services.tasks.shopify import handle_shopify_process_products as handler_module


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows, shops):
        self._rows = rows
        self._shops = shops
        self.execute_calls = 0
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, _query):
        self.execute_calls += 1
        return _FakeResult(self._rows if self.execute_calls == 1 else self._shops)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_shopify_process_products_emits_one_final_workspace_summary_without_tokens(monkeypatch) -> None:
    success_row = SimpleNamespace(
        client_id="shpsi_1",
        frontend_client_id="frontend_1",
        shop_integration_id="shpint_1",
        status=ShopifyProductSyncItemStatusEnum.PENDING,
        requested_operation=None,
        shopify_product_id=None,
        shopify_variant_id=None,
        error_code=None,
        error_message=None,
    )
    failed_row = SimpleNamespace(
        client_id="shpsi_2",
        frontend_client_id="frontend_2",
        shop_integration_id="shpint_2",
        status=ShopifyProductSyncItemStatusEnum.PENDING,
        requested_operation=None,
        shopify_product_id=None,
        shopify_variant_id=None,
        error_code=None,
        error_message=None,
    )
    shops = [
        SimpleNamespace(client_id="shpint_1", access_token_encrypted="encrypted-success"),
        SimpleNamespace(client_id="shpint_2", access_token_encrypted="encrypted-fail"),
    ]
    session = _FakeSession([success_row, failed_row], shops)
    emitted: dict = {}

    @asynccontextmanager
    async def _fake_task_db_session():
        yield session

    async def _fake_sync_one_product_sync_item(_session, *, sync_item, shop):
        assert "encrypted-" in shop.access_token_encrypted
        if sync_item.client_id == "shpsi_1":
            sync_item.status = ShopifyProductSyncItemStatusEnum.SUCCEEDED
            sync_item.requested_operation = ShopifyProductSyncOperationEnum.CREATE
            sync_item.shopify_product_id = "gid://shopify/Product/1"
            sync_item.shopify_variant_id = "gid://shopify/ProductVariant/1"
            return
        sync_item.status = ShopifyProductSyncItemStatusEnum.FAILED
        sync_item.requested_operation = ShopifyProductSyncOperationEnum.UPDATE
        sync_item.error_code = "ambiguous_product_match"
        sync_item.error_message = "Multiple Shopify products matched the same identity."

    async def _fake_emit_to_workspace_room(**kwargs):
        emitted.update(kwargs)

    monkeypatch.setattr(handler_module, "task_db_session", _fake_task_db_session)
    monkeypatch.setattr(handler_module, "sync_one_product_sync_item", _fake_sync_one_product_sync_item)
    monkeypatch.setattr(handler_module, "emit_to_workspace_room", _fake_emit_to_workspace_room)

    await handler_module.handle_shopify_process_products(
        {
            "workspace_id": "ws_1",
            "requested_by_user_id": "usr_1",
            "sync_item_client_ids": ["shpsi_1", "shpsi_2"],
        },
        "task_shopify_products_1",
    )

    assert emitted["workspace_id"] == "ws_1"
    assert emitted["event"] == "shopify.products.synced"
    assert emitted["payload"] == {
        "task_id": "task_shopify_products_1",
        "succeeded": [
            {
                "frontend_client_id": "frontend_1",
                "shop_integration_id": "shpint_1",
                "sync_item_client_id": "shpsi_1",
                "requested_operation": "create",
                "shopify_product_id": "gid://shopify/Product/1",
                "shopify_variant_id": "gid://shopify/ProductVariant/1",
            }
        ],
        "failed": [
            {
                "frontend_client_id": "frontend_2",
                "shop_integration_id": "shpint_2",
                "sync_item_client_id": "shpsi_2",
                "requested_operation": "update",
                "error_code": "ambiguous_product_match",
                "error_message": "Multiple Shopify products matched the same identity.",
            }
        ],
    }
    assert "encrypted-success" not in str(emitted["payload"])
    assert "encrypted-fail" not in str(emitted["payload"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_shopify_process_products_rolls_back_before_recording_an_unexpected_error(monkeypatch) -> None:
    row = SimpleNamespace(
        client_id="shpsi_1",
        frontend_client_id="frontend_1",
        shop_integration_id="shpint_1",
        status=ShopifyProductSyncItemStatusEnum.PENDING,
        requested_operation=None,
        shopify_product_id=None,
        shopify_variant_id=None,
        error_code=None,
        error_message=None,
    )
    shop = SimpleNamespace(client_id="shpint_1", access_token_encrypted="encrypted-token")
    session = _FakeSession([row], [shop])
    emitted: dict = {}

    @asynccontextmanager
    async def _fake_task_db_session():
        yield session

    async def _fake_sync_one_product_sync_item(_session, *, sync_item, shop):
        # Simulates the orchestrator's own commit failing (e.g. a transient DB
        # error) and leaving the session in a state that requires an explicit
        # rollback before it can be used again.
        raise RuntimeError("simulated commit failure")

    async def _fake_emit_to_workspace_room(**kwargs):
        emitted.update(kwargs)

    monkeypatch.setattr(handler_module, "task_db_session", _fake_task_db_session)
    monkeypatch.setattr(handler_module, "sync_one_product_sync_item", _fake_sync_one_product_sync_item)
    monkeypatch.setattr(handler_module, "emit_to_workspace_room", _fake_emit_to_workspace_room)

    await handler_module.handle_shopify_process_products(
        {
            "workspace_id": "ws_1",
            "requested_by_user_id": "usr_1",
            "sync_item_client_ids": ["shpsi_1"],
        },
        "task_shopify_products_rollback",
    )

    assert session.rollbacks == 1
    assert row.status == ShopifyProductSyncItemStatusEnum.FAILED
    assert row.error_code == "unexpected_error"
    # The batch must still complete and emit its summary rather than crashing.
    assert emitted["payload"]["failed"][0]["error_code"] == "unexpected_error"
