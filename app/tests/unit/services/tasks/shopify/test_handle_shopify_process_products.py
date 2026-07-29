from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventTypeEnum,
    ShopifyInventoryModeEnum,
    ShopifyProductSyncItemStatusEnum,
    ShopifyProductSyncOperationEnum,
    ShopifyProductSyncOriginEnum,
)
from beyo_manager.errors.external_service import ShopifyGraphQLRetryableError
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
def test_completion_dispatch_uses_origin_not_absolute_inventory_mode() -> None:
    standard_row = SimpleNamespace(
        status=ShopifyProductSyncItemStatusEnum.SUCCEEDED,
        inventory_mode=ShopifyInventoryModeEnum.SET,
        frontend_client_id="frontend_standard",
        shop_integration_id="shop_1",
        client_id="sync_standard",
        requested_operation=ShopifyProductSyncOperationEnum.CREATE,
        shopify_product_id="gid://shopify/Product/1",
        shopify_variant_id="gid://shopify/ProductVariant/1",
        inventory_result_json=None,
    )
    preorder_row = SimpleNamespace(
        **{
            **vars(standard_row),
            "frontend_client_id": "task_preorder",
            "client_id": "sync_preorder",
        }
    )
    standard_rows: list = []
    preorder_rows: list = []
    succeeded: list[dict] = []
    failed: list[dict] = []

    handler_module._record_completion(
        standard_row,
        origin=ShopifyProductSyncOriginEnum.STANDARD_PRODUCT_SYNC,
        standard_rows=standard_rows,
        preorder_rows=preorder_rows,
        succeeded=succeeded,
        failed=failed,
    )
    handler_module._record_completion(
        preorder_row,
        origin=ShopifyProductSyncOriginEnum.PREORDER_TASK,
        standard_rows=standard_rows,
        preorder_rows=preorder_rows,
        succeeded=succeeded,
        failed=failed,
    )

    assert standard_rows == [standard_row]
    assert preorder_rows == [preorder_row]
    assert succeeded[0]["frontend_client_id"] == "frontend_standard"
    assert failed == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_shopify_process_products_emits_one_final_workspace_summary_without_tokens(monkeypatch) -> None:
    success_row = SimpleNamespace(
        client_id="shpsi_1",
        workspace_id="ws_1",
        frontend_client_id="frontend_1",
        shop_integration_id="shpint_1",
        sync_origin=ShopifyProductSyncOriginEnum.STANDARD_PRODUCT_SYNC.value,
        source_entity_id=None,
        created_by_id="usr_1",
        status=ShopifyProductSyncItemStatusEnum.PENDING,
        requested_operation=None,
        shopify_product_id=None,
        shopify_variant_id=None,
        error_code=None,
        error_message=None,
        inventory_result_json=None,
    )
    failed_row = SimpleNamespace(
        client_id="shpsi_2",
        workspace_id="ws_1",
        frontend_client_id="frontend_2",
        shop_integration_id="shpint_2",
        sync_origin=ShopifyProductSyncOriginEnum.STANDARD_PRODUCT_SYNC.value,
        source_entity_id=None,
        created_by_id="usr_1",
        status=ShopifyProductSyncItemStatusEnum.PENDING,
        requested_operation=None,
        shopify_product_id=None,
        shopify_variant_id=None,
        error_code=None,
        error_message=None,
        inventory_result_json=None,
    )
    shops = [
        SimpleNamespace(client_id="shpint_1", access_token_encrypted="encrypted-success"),
        SimpleNamespace(client_id="shpint_2", access_token_encrypted="encrypted-fail"),
    ]
    session = _FakeSession([success_row, failed_row], shops)
    emitted: dict = {}
    event_types: list[ShopifyIntegrationEventTypeEnum] = []

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

    async def _fake_create_event(_session, **kwargs):
        event_types.append(kwargs["event_type"])

    monkeypatch.setattr(handler_module, "task_db_session", _fake_task_db_session)
    monkeypatch.setattr(handler_module, "sync_one_product_sync_item", _fake_sync_one_product_sync_item)
    monkeypatch.setattr(handler_module, "emit_to_workspace_room", _fake_emit_to_workspace_room)
    monkeypatch.setattr(
        handler_module,
        "create_shopify_integration_event",
        _fake_create_event,
    )

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
    assert event_types == [
        ShopifyIntegrationEventTypeEnum.PRODUCT_SYNC,
        ShopifyIntegrationEventTypeEnum.PRODUCT_SYNC,
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_shopify_process_products_rolls_back_before_recording_an_unexpected_error(monkeypatch) -> None:
    row = SimpleNamespace(
        client_id="shpsi_1",
        workspace_id="ws_1",
        frontend_client_id="frontend_1",
        shop_integration_id="shpint_1",
        sync_origin=ShopifyProductSyncOriginEnum.STANDARD_PRODUCT_SYNC.value,
        source_entity_id=None,
        created_by_id="usr_1",
        status=ShopifyProductSyncItemStatusEnum.PENDING,
        requested_operation=None,
        shopify_product_id=None,
        shopify_variant_id=None,
        error_code=None,
        error_message=None,
        inventory_result_json=None,
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

    async def _fake_create_event(_session, **_kwargs):
        return None

    monkeypatch.setattr(handler_module, "task_db_session", _fake_task_db_session)
    monkeypatch.setattr(handler_module, "sync_one_product_sync_item", _fake_sync_one_product_sync_item)
    monkeypatch.setattr(handler_module, "emit_to_workspace_room", _fake_emit_to_workspace_room)
    monkeypatch.setattr(
        handler_module,
        "create_shopify_integration_event",
        _fake_create_event,
    )

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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retryable_shopify_error_propagates_to_execution_retry(
    monkeypatch,
) -> None:
    row = SimpleNamespace(
        client_id="shpsi_retry",
        workspace_id="ws_1",
        frontend_client_id="frontend_retry",
        shop_integration_id="shpint_1",
        sync_origin=ShopifyProductSyncOriginEnum.STANDARD_PRODUCT_SYNC.value,
        status=ShopifyProductSyncItemStatusEnum.PROCESSING,
    )
    shop = SimpleNamespace(
        client_id="shpint_1",
        access_token_encrypted="encrypted-token",
    )
    session = _FakeSession([row], [shop])

    @asynccontextmanager
    async def _fake_task_db_session():
        yield session

    async def _retryable(*_args, **_kwargs):
        raise ShopifyGraphQLRetryableError(
            "Lost Shopify response.",
            error_code="shopify_timeout",
        )

    monkeypatch.setattr(handler_module, "task_db_session", _fake_task_db_session)
    monkeypatch.setattr(
        handler_module,
        "sync_one_product_sync_item",
        _retryable,
    )

    with pytest.raises(ShopifyGraphQLRetryableError):
        await handler_module.handle_shopify_process_products(
            {
                "workspace_id": "ws_1",
                "requested_by_user_id": "usr_1",
                "sync_item_client_ids": ["shpsi_retry"],
            },
            "task_shopify_products_retry",
        )

    assert session.rollbacks == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unknown_origin_fails_before_any_shopify_mutation(monkeypatch) -> None:
    row = SimpleNamespace(
        client_id="shpsi_future",
        sync_origin="future_producer",
    )
    session = _FakeSession([row], [])
    mutation_called = False

    @asynccontextmanager
    async def _fake_task_db_session():
        yield session

    async def _unexpected_sync(*_args, **_kwargs):
        nonlocal mutation_called
        mutation_called = True

    monkeypatch.setattr(handler_module, "task_db_session", _fake_task_db_session)
    monkeypatch.setattr(
        handler_module,
        "sync_one_product_sync_item",
        _unexpected_sync,
    )

    with pytest.raises(RuntimeError, match="Unsupported Shopify product sync origin"):
        await handler_module.handle_shopify_process_products(
            {
                "workspace_id": "ws_1",
                "requested_by_user_id": "usr_1",
                "sync_item_client_ids": ["shpsi_future"],
            },
            "task_shopify_products_future",
        )

    assert mutation_called is False
    assert session.execute_calls == 1
