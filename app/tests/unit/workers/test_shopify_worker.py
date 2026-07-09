from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.services.tasks.shopify.handle_shopify_process_webhook import (
    handle_shopify_process_webhook,
)
from beyo_manager.services.tasks.shopify.handle_shopify_remove_webhooks_for_shop import (
    handle_shopify_remove_webhooks_for_shop,
)
from beyo_manager.services.tasks.shopify.handle_shopify_sync_webhooks_for_shop import (
    handle_shopify_sync_webhooks_for_shop,
)
from beyo_manager.workers import shopify_worker


def test_shopify_worker_registers_only_shopify_handlers() -> None:
    assert set(shopify_worker.HANDLER_MAP) == {
        TaskType.SHOPIFY_PROCESS_WEBHOOK,
        TaskType.SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP,
        TaskType.SHOPIFY_REMOVE_WEBHOOKS_FOR_SHOP,
        TaskType.SHOPIFY_RECONCILE_SHOP,
    }


def test_shopify_worker_handler_map_points_to_expected_functions() -> None:
    assert shopify_worker.HANDLER_MAP[TaskType.SHOPIFY_PROCESS_WEBHOOK] is handle_shopify_process_webhook
    assert (
        shopify_worker.HANDLER_MAP[TaskType.SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP]
        is handle_shopify_sync_webhooks_for_shop
    )
    assert (
        shopify_worker.HANDLER_MAP[TaskType.SHOPIFY_REMOVE_WEBHOOKS_FOR_SHOP]
        is handle_shopify_remove_webhooks_for_shop
    )
    assert (
        shopify_worker.HANDLER_MAP[TaskType.SHOPIFY_RECONCILE_SHOP]
        is handle_shopify_sync_webhooks_for_shop
    )
