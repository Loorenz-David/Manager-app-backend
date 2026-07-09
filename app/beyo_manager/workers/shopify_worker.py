import asyncio

from beyo_manager.core.logging.config import configure_logging
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.models.database import init_db
from beyo_manager.services.infra.execution.worker_base import run_worker
from beyo_manager.services.tasks.shopify.handle_shopify_process_webhook import (
    handle_shopify_process_webhook,
)
from beyo_manager.services.tasks.shopify.handle_shopify_remove_webhooks_for_shop import (
    handle_shopify_remove_webhooks_for_shop,
)
from beyo_manager.services.tasks.shopify.handle_shopify_sync_webhooks_for_shop import (
    handle_shopify_sync_webhooks_for_shop,
)

HANDLER_MAP = {
    TaskType.SHOPIFY_PROCESS_WEBHOOK: handle_shopify_process_webhook,
    TaskType.SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP: handle_shopify_sync_webhooks_for_shop,
    TaskType.SHOPIFY_REMOVE_WEBHOOKS_FOR_SHOP: handle_shopify_remove_webhooks_for_shop,
    TaskType.SHOPIFY_RECONCILE_SHOP: handle_shopify_sync_webhooks_for_shop,
}


async def main() -> None:
    configure_logging()
    await init_db()
    await run_worker("queue:shopify", HANDLER_MAP)


if __name__ == "__main__":
    asyncio.run(main())
