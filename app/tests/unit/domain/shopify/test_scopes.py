from beyo_manager.domain.shopify.scopes import (
    compare_requested_and_granted_scopes,
    has_all_required_scopes,
    normalize_scope,
    normalize_scopes,
    parse_scope_config,
)


def test_normalize_scope_and_parse_scope_config_dedupe_and_sort() -> None:
    assert normalize_scope(" Read_Orders ") == "read_orders"
    assert parse_scope_config("write_products, read_orders,read_orders") == (
        "read_orders",
        "write_products",
    )


def test_normalize_scopes_ignores_blank_values() -> None:
    assert normalize_scopes([" read_orders ", "", "read_products"]) == (
        "read_orders",
        "read_products",
    )


def test_compare_requested_and_granted_scopes_reports_missing_and_extra() -> None:
    comparison = compare_requested_and_granted_scopes(
        ["read_orders", "read_products"],
        ["read_orders", "write_products"],
    )

    assert comparison.requested == ("read_orders", "read_products")
    assert comparison.granted == ("read_orders", "write_products")
    assert comparison.missing == ()
    assert comparison.extra == ("write_products",)
    assert comparison.is_outdated is False


def test_has_all_required_scopes_is_true_when_granted_covers_requested() -> None:
    assert has_all_required_scopes(
        ["read_orders", "read_products"],
        ["read_products", "read_orders", "write_products"],
    )


def test_has_all_required_scopes_treats_write_scope_as_covering_matching_read_scope() -> None:
    assert has_all_required_scopes(
        ["read_customers", "read_orders", "read_products"],
        ["write_customers", "write_orders", "write_products"],
    )


def test_compare_requested_and_granted_scopes_keeps_unrelated_read_scope_missing() -> None:
    comparison = compare_requested_and_granted_scopes(
        ["read_inventory", "read_products"],
        ["write_products"],
    )

    assert comparison.requested == ("read_inventory", "read_products")
    assert comparison.granted == ("write_products",)
    assert comparison.missing == ("read_inventory",)
    assert comparison.extra == ("write_products",)
    assert comparison.is_outdated is True
