from __future__ import annotations

import inspect

from beyo_manager.services.commands.shopify import (
    _webhook_sync,
    enqueue_shopify_webhook_sync_after_install,
    handle_shopify_oauth_callback,
)


def test_phase2_webhook_sync_boundaries_do_not_reference_real_sync_commands() -> None:
    target_names = {
        "sync_shopify_webhook_subscriptions_for_shop",
        "remove_shopify_webhooks_for_shop",
    }
    combined_source = "\n".join(
        [
            inspect.getsource(_webhook_sync),
            inspect.getsource(enqueue_shopify_webhook_sync_after_install),
            inspect.getsource(handle_shopify_oauth_callback),
        ]
    )

    for target_name in target_names:
        assert target_name not in combined_source
