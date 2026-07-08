from beyo_manager.domain.shopify.webhook_registry import (
    SHOPIFY_WEBHOOK_CALLBACK_PATH,
    SHOPIFY_WEBHOOK_REGISTRY,
    get_webhook_definition,
)


def test_webhook_registry_contains_approved_initial_topics() -> None:
    expected_topics = {
        "app/uninstalled",
        "orders/create",
        "orders/updated",
        "orders/paid",
        "orders/cancelled",
        "products/create",
        "products/update",
        "products/delete",
    }

    assert {definition.topic for definition in SHOPIFY_WEBHOOK_REGISTRY} == expected_topics
    assert all(definition.enabled for definition in SHOPIFY_WEBHOOK_REGISTRY)
    assert all(definition.callback_path == SHOPIFY_WEBHOOK_CALLBACK_PATH for definition in SHOPIFY_WEBHOOK_REGISTRY)


def test_get_webhook_definition_returns_expected_scopes() -> None:
    assert get_webhook_definition("app/uninstalled").required_scopes == ()
    assert get_webhook_definition("orders/create").required_scopes == ("read_orders",)
    assert get_webhook_definition("products/delete").required_scopes == ("read_products",)
    assert get_webhook_definition("missing/topic") is None
