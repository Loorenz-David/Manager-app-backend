from __future__ import annotations

import pytest

from beyo_manager.domain.shopify.customer_lookup import (
    filter_shopify_order_line_item_exact_matches,
    normalize_shopify_customer_lookup_result,
)


def _order_node(**overrides) -> dict:
    base = {
        "id": "gid://shopify/Order/1",
        "name": "#1001",
        "email": "order@example.com",
        "phone": "111",
        "customer": {
            "id": "gid://shopify/Customer/1",
            "displayName": "Customer Name",
            "defaultEmailAddress": {"emailAddress": "customer@example.com"},
            "defaultPhoneNumber": {"phoneNumber": "222"},
            "defaultAddress": {
                "firstName": "Default",
                "lastName": "Person",
                "address1": "Default 1",
                "address2": "Default 2",
                "city": "Default City",
                "province": "Default Province",
                "provinceCode": "DP",
                "zip": "99999",
                "phone": "555",
                "latitude": 55.5,
                "longitude": 13.5,
            },
        },
        "shippingAddress": {
            "firstName": "Shipping",
            "lastName": "Name",
            "address1": "Ship Street",
            "address2": "Ship Suite",
            "city": "Ship City",
            "province": "Ship Province",
            "provinceCode": "SP",
            "zip": "12345",
            "phone": "333",
            "latitude": 59.1,
            "longitude": 18.2,
            "company": "Ignored Company",
        },
        "billingAddress": {
            "firstName": "Billing",
            "lastName": "Name",
            "address1": "Bill Street",
            "address2": "Bill Suite",
            "city": "Bill City",
            "province": "Bill Province",
            "provinceCode": "BP",
            "zip": "54321",
            "phone": "444",
            "latitude": 58.1,
            "longitude": 17.2,
        },
        "lineItems": {
            "edges": [
                {
                    "node": {
                        "sku": "SKU-123",
                        "variant": {"id": "gid://shopify/ProductVariant/1", "sku": "SKU-123", "barcode": "BAR-123"},
                    }
                }
            ]
        },
    }
    base.update(overrides)
    return base


@pytest.mark.unit
def test_filter_shopify_order_line_item_exact_matches_uses_exact_sku() -> None:
    orders = [_order_node(), _order_node(id="gid://shopify/Order/2", lineItems={"edges": [{"node": {"sku": "SKU-123-EXTRA", "variant": {"barcode": "BAR-123"}}}]})]

    matched = filter_shopify_order_line_item_exact_matches(orders, identity_type="sku", identity_value="SKU-123")

    assert [order["id"] for order in matched] == ["gid://shopify/Order/1"]


@pytest.mark.unit
def test_filter_shopify_order_line_item_exact_matches_uses_exact_barcode_on_variant() -> None:
    orders = [
        _order_node(),
        _order_node(
            id="gid://shopify/Order/2",
            lineItems={
                "edges": [
                    {"node": {"sku": "SKU-123", "variant": {"barcode": "BAR-999"}}},
                    {"node": {"sku": "OTHER", "variant": {"barcode": "BAR-123-EXTRA"}}},
                ]
            },
        ),
    ]

    matched = filter_shopify_order_line_item_exact_matches(orders, identity_type="barcode", identity_value="BAR-123")

    assert [order["id"] for order in matched] == ["gid://shopify/Order/1"]


@pytest.mark.unit
def test_normalize_shopify_customer_lookup_result_prefers_customer_contact_and_shipping_address() -> None:
    result = normalize_shopify_customer_lookup_result(
        _order_node(),
        shop_integration_id="shpint_1",
        shop_domain="shop-a.myshopify.com",
        match_type="sku",
        matched_value="SKU-123",
    )

    assert result.shop_integration_id == "shpint_1"
    assert result.display_name == "Customer Name"
    assert result.primary_email == "customer@example.com"
    assert result.primary_phone_number == "222"
    assert result.address.street_address == "Ship Street"
    assert result.address.post_code == "12345"
    assert result.address.city == "Ship City"
    assert result.address.district == "Ship Province"
    assert result.address.coordinates.latitude == 59.1
    assert result.address.coordinates.longitude == 18.2


@pytest.mark.unit
@pytest.mark.parametrize(
    ("customer", "shipping", "billing", "expected_name"),
    [
        ({"displayName": "  ", "defaultAddress": {}}, {"firstName": "Ship", "lastName": "Name"}, {"firstName": "Bill", "lastName": "Name"}, "Ship Name"),
        (None, {"firstName": " ", "lastName": " "}, {"firstName": "Bill", "lastName": "Name"}, "Bill Name"),
        ({"displayName": " ", "defaultAddress": {"firstName": "Default", "lastName": "Only"}}, {"firstName": None, "lastName": None}, {"firstName": "", "lastName": ""}, "Default Only"),
        ({"displayName": " ", "defaultAddress": {}}, {"firstName": "Prince", "lastName": ""}, {"firstName": "", "lastName": ""}, "Prince"),
        ({"displayName": " ", "defaultAddress": {}}, {"firstName": "", "lastName": ""}, {"firstName": "", "lastName": ""}, None),
    ],
)
def test_normalize_shopify_customer_lookup_result_applies_display_name_fallbacks(
    customer: dict | None,
    shipping: dict,
    billing: dict,
    expected_name: str | None,
) -> None:
    result = normalize_shopify_customer_lookup_result(
        _order_node(customer=customer, shippingAddress=shipping, billingAddress=billing),
        shop_integration_id="shpint_1",
        shop_domain="shop-a.myshopify.com",
        match_type="barcode",
        matched_value="BAR-123",
    )

    assert result.display_name == expected_name


@pytest.mark.unit
@pytest.mark.parametrize(
    ("customer", "order_email", "expected_email"),
    [
        ({"defaultEmailAddress": {"emailAddress": "customer@example.com"}}, "order@example.com", "customer@example.com"),
        ({"defaultEmailAddress": None}, "order@example.com", "order@example.com"),
        ({"defaultEmailAddress": {"emailAddress": " "}}, " ", None),
    ],
)
def test_normalize_shopify_customer_lookup_result_applies_email_fallbacks(
    customer: dict,
    order_email: str,
    expected_email: str | None,
) -> None:
    result = normalize_shopify_customer_lookup_result(
        _order_node(customer=customer, email=order_email),
        shop_integration_id="shpint_1",
        shop_domain="shop-a.myshopify.com",
        match_type="sku",
        matched_value="SKU-123",
    )

    assert result.primary_email == expected_email


@pytest.mark.unit
@pytest.mark.parametrize(
    ("customer", "order_phone", "shipping_phone", "billing_phone", "expected_phone"),
    [
        ({"defaultPhoneNumber": {"phoneNumber": "222"}, "defaultAddress": {"phone": "555"}}, "111", "333", "444", "222"),
        ({"defaultPhoneNumber": None, "defaultAddress": {"phone": "555"}}, "111", "333", "444", "111"),
        ({"defaultPhoneNumber": None, "defaultAddress": {"phone": "555"}}, " ", "333", "444", "333"),
        ({"defaultPhoneNumber": None, "defaultAddress": {"phone": "555"}}, " ", " ", "444", "444"),
        ({"defaultPhoneNumber": None, "defaultAddress": {"phone": "555"}}, " ", " ", " ", "555"),
        ({"defaultPhoneNumber": None, "defaultAddress": {"phone": " "}}, " ", " ", " ", None),
    ],
)
def test_normalize_shopify_customer_lookup_result_applies_phone_fallbacks(
    customer: dict,
    order_phone: str,
    shipping_phone: str,
    billing_phone: str,
    expected_phone: str | None,
) -> None:
    shipping_address = {"phone": shipping_phone}
    billing_address = {"phone": billing_phone}
    result = normalize_shopify_customer_lookup_result(
        _order_node(
            customer=customer,
            phone=order_phone,
            shippingAddress=shipping_address,
            billingAddress=billing_address,
        ),
        shop_integration_id="shpint_1",
        shop_domain="shop-a.myshopify.com",
        match_type="sku",
        matched_value="SKU-123",
    )

    assert result.primary_phone_number == expected_phone


@pytest.mark.unit
def test_normalize_shopify_customer_lookup_result_falls_back_to_billing_then_default_address() -> None:
    billing_result = normalize_shopify_customer_lookup_result(
        _order_node(
            shippingAddress={},
            billingAddress={"address1": "Bill Street", "zip": "22222", "city": "Bill City", "province": "Bill Province", "provinceCode": "BP"},
        ),
        shop_integration_id="shpint_1",
        shop_domain="shop-a.myshopify.com",
        match_type="sku",
        matched_value="SKU-123",
    )
    default_result = normalize_shopify_customer_lookup_result(
        _order_node(
            shippingAddress={},
            billingAddress={},
            customer={"defaultAddress": {"address2": "Default Fallback", "zip": "33333", "city": "Default City", "province": "Default Province"}},
        ),
        shop_integration_id="shpint_1",
        shop_domain="shop-a.myshopify.com",
        match_type="sku",
        matched_value="SKU-123",
    )

    assert billing_result.address.street_address == "Bill Street"
    assert billing_result.address.district == "Bill Province"
    assert default_result.address.street_address == "Default Fallback"
    assert default_result.address.district == "Default Province"


@pytest.mark.unit
def test_normalize_shopify_customer_lookup_result_returns_empty_address_when_none_present() -> None:
    result = normalize_shopify_customer_lookup_result(
        _order_node(customer={}, shippingAddress={}, billingAddress={}),
        shop_integration_id="shpint_1",
        shop_domain="shop-a.myshopify.com",
        match_type="barcode",
        matched_value="BAR-123",
    )

    assert result.address.street_address is None
    assert result.address.post_code is None
    assert result.address.city is None
    assert result.address.district is None
    assert result.address.coordinates.latitude is None
    assert result.address.coordinates.longitude is None


@pytest.mark.unit
def test_normalize_shopify_customer_lookup_result_never_uses_company_for_district() -> None:
    result = normalize_shopify_customer_lookup_result(
        _order_node(
            shippingAddress={
                "address1": "Ship Street",
                "zip": "12345",
                "city": "Ship City",
                "province": " ",
                "provinceCode": " ",
                "company": "Should Not Leak",
            }
        ),
        shop_integration_id="shpint_1",
        shop_domain="shop-a.myshopify.com",
        match_type="sku",
        matched_value="SKU-123",
    )

    assert result.address.district is None


@pytest.mark.unit
def test_normalize_shopify_customer_lookup_result_district_never_falls_back_to_province_code() -> None:
    result = normalize_shopify_customer_lookup_result(
        _order_node(
            shippingAddress={
                "address1": "Ship Street",
                "zip": "12345",
                "city": "Ship City",
                "province": " ",
                "provinceCode": "SP",
            }
        ),
        shop_integration_id="shpint_1",
        shop_domain="shop-a.myshopify.com",
        match_type="sku",
        matched_value="SKU-123",
    )

    assert result.address.district is None
