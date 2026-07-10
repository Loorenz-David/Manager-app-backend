from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pytest

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.shopify import (
    ShopifyProcessProductsPayload,
    ShopifyProcessWebhookPayload,
    ShopifyReconcileShopPayload,
    ShopifyRemoveWebhooksForShopPayload,
    ShopifySyncWebhooksForShopPayload,
)
from beyo_manager.services.infra.execution.task_router import QUEUE_MAP

# Resolved relative to this file, not the process cwd — a plain "app/migrations/..."
# string only works when pytest happens to be invoked from the repo root, not from
# app/ (this project's own pytest.ini/Makefile working directory).
_MIGRATIONS_VERSIONS_DIR = Path(__file__).resolve().parents[4] / "migrations" / "versions"


@pytest.mark.unit
def test_shopify_task_types_exist_with_expected_values() -> None:
    assert TaskType.SHOPIFY_PROCESS_WEBHOOK.value == "shopify_process_webhook"
    assert TaskType.SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP.value == "shopify_sync_webhooks_for_shop"
    assert TaskType.SHOPIFY_REMOVE_WEBHOOKS_FOR_SHOP.value == "shopify_remove_webhooks_for_shop"
    assert TaskType.SHOPIFY_RECONCILE_SHOP.value == "shopify_reconcile_shop"
    assert TaskType.SHOPIFY_PROCESS_PRODUCTS.value == "shopify_process_products"


@pytest.mark.unit
def test_shopify_payloads_round_trip_via_asdict() -> None:
    payloads = [
        ShopifyProcessWebhookPayload(webhook_intake_id="shpwhi_123"),
        ShopifySyncWebhooksForShopPayload(shop_integration_id="shpint_123"),
        ShopifyRemoveWebhooksForShopPayload(shop_integration_id="shpint_456"),
        ShopifyReconcileShopPayload(shop_integration_id="shpint_789"),
        ShopifyProcessProductsPayload(
            workspace_id="ws_1",
            requested_by_user_id="usr_1",
            sync_item_client_ids=["shpsi_1", "shpsi_2"],
        ),
    ]

    for payload in payloads:
        assert type(payload)(**asdict(payload)) == payload


@pytest.mark.unit
def test_all_shopify_task_types_route_to_shopify_queue() -> None:
    shopify_task_types = {
        TaskType.SHOPIFY_PROCESS_WEBHOOK,
        TaskType.SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP,
        TaskType.SHOPIFY_REMOVE_WEBHOOKS_FOR_SHOP,
        TaskType.SHOPIFY_RECONCILE_SHOP,
        TaskType.SHOPIFY_PROCESS_PRODUCTS,
    }

    for task_type in shopify_task_types:
        assert QUEUE_MAP[task_type] == "queue:shopify"


@pytest.mark.unit
def test_no_non_shopify_task_type_routes_to_shopify_queue() -> None:
    shopify_task_types = {
        TaskType.SHOPIFY_PROCESS_WEBHOOK,
        TaskType.SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP,
        TaskType.SHOPIFY_REMOVE_WEBHOOKS_FOR_SHOP,
        TaskType.SHOPIFY_RECONCILE_SHOP,
        TaskType.SHOPIFY_PROCESS_PRODUCTS,
    }

    non_shopify_routed = {
        task_type
        for task_type, queue_name in QUEUE_MAP.items()
        if queue_name == "queue:shopify" and task_type not in shopify_task_types
    }

    assert non_shopify_routed == set()


@pytest.mark.unit
def test_shopify_task_type_migration_adds_all_expected_enum_values() -> None:
    migration_path = _MIGRATIONS_VERSIONS_DIR / "c3f7a9d2e4b1_add_shopify_execution_task_types.py"
    source = migration_path.read_text()

    assert "down_revision: Union[str, None] = \"677ed7131bb2\"" in source
    assert "ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'shopify_process_webhook'" in source
    assert "ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'shopify_sync_webhooks_for_shop'" in source
    assert "ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'shopify_remove_webhooks_for_shop'" in source
    assert "ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'shopify_reconcile_shop'" in source


@pytest.mark.unit
def test_shopify_product_sync_task_type_migration_adds_expected_enum_value() -> None:
    migration_path = _MIGRATIONS_VERSIONS_DIR / "f2c3d4e5f6a7_add_shopify_process_products_task_type.py"
    source = migration_path.read_text()

    assert "down_revision: Union[str, None] = \"e1b2c3d4e5f6\"" in source
    assert "ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'shopify_process_products'" in source
