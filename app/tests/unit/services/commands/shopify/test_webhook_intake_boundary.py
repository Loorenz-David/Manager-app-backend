from __future__ import annotations

import inspect

from beyo_manager.routers.api_v1 import shopify_webhooks
from beyo_manager.services.commands.shopify import enqueue_or_record_shopify_webhook


def test_shopify_webhook_router_does_not_reference_execution_runtime_directly() -> None:
    blocked_terms = {
        "shopify_process_webhook",
        "queue:shopify",
        "redis",
        "worker",
        "task_type",
        "create_instant_task",
    }
    router_source = inspect.getsource(shopify_webhooks).lower()

    for blocked_term in blocked_terms:
        assert blocked_term not in router_source


def test_phase5_webhook_intake_boundary_references_only_approved_enqueue_boundary() -> None:
    command_source = inspect.getsource(enqueue_or_record_shopify_webhook)
    command_source_lower = command_source.lower()

    assert command_source.count("create_instant_task(") == 1
    assert "TaskType.SHOPIFY_PROCESS_WEBHOOK" in command_source
    assert command_source.index("create_shopify_integration_event(") < command_source.index("create_instant_task(")

    for blocked_term in {"queue:shopify", "redis", "run_worker", "handler_map"}:
        assert blocked_term not in command_source_lower
