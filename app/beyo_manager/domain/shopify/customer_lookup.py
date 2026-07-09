from __future__ import annotations

from typing import Literal

from beyo_manager.domain.shopify.results import (
    ShopifyCustomerLookupAddressResult,
    ShopifyCustomerLookupCoordinatesResult,
    ShopifyCustomerLookupResult,
)

IdentityType = Literal["sku", "barcode"]


def filter_shopify_order_line_item_exact_matches(
    order_nodes: list[dict],
    *,
    identity_type: IdentityType,
    identity_value: str,
) -> list[dict]:
    matched_orders: list[dict] = []
    for order_node in order_nodes:
        if _order_has_exact_line_item_match(order_node, identity_type=identity_type, identity_value=identity_value):
            matched_orders.append(order_node)
    return matched_orders


def normalize_shopify_customer_lookup_result(
    order_node: dict,
    *,
    shop_integration_id: str,
    shop_domain: str,
    match_type: IdentityType,
    matched_value: str,
) -> ShopifyCustomerLookupResult:
    customer = order_node.get("customer") or {}
    shipping_address = order_node.get("shippingAddress") or {}
    billing_address = order_node.get("billingAddress") or {}
    default_address = customer.get("defaultAddress") or {}

    return ShopifyCustomerLookupResult(
        shop_integration_id=shop_integration_id,
        shop_domain=shop_domain,
        match_type=match_type,
        matched_value=matched_value,
        order_id=_clean_str(order_node.get("id")),
        order_name=_clean_str(order_node.get("name")),
        customer_id=_clean_str(customer.get("id")),
        display_name=_first_non_blank(
            _clean_str(customer.get("displayName")),
            _build_name(shipping_address),
            _build_name(billing_address),
            _build_name(default_address),
        ),
        primary_phone_number=_first_non_blank(
            _clean_str((customer.get("defaultPhoneNumber") or {}).get("phoneNumber")),
            _clean_str(order_node.get("phone")),
            _clean_str(shipping_address.get("phone")),
            _clean_str(billing_address.get("phone")),
            _clean_str(default_address.get("phone")),
        ),
        primary_email=_first_non_blank(
            _clean_str((customer.get("defaultEmailAddress") or {}).get("emailAddress")),
            _clean_str(order_node.get("email")),
        ),
        address=_normalize_address(shipping_address, billing_address, default_address),
    )


def _order_has_exact_line_item_match(
    order_node: dict,
    *,
    identity_type: IdentityType,
    identity_value: str,
) -> bool:
    expected = _clean_str(identity_value)
    if expected is None:
        return False

    line_item_edges = (order_node.get("lineItems") or {}).get("edges") or []
    for edge in line_item_edges:
        line_item = (edge or {}).get("node") or {}
        if identity_type == "sku":
            if _clean_str(line_item.get("sku")) == expected:
                return True
            continue

        variant = line_item.get("variant") or {}
        if _clean_str(variant.get("barcode")) == expected:
            return True
    return False


def _normalize_address(*addresses: dict) -> ShopifyCustomerLookupAddressResult:
    address = {}
    for candidate in addresses:
        if any(_clean_str(candidate.get(key)) is not None for key in ("address1", "address2", "zip", "city", "province", "provinceCode")):
            address = candidate
            break

    latitude = _coerce_float(address.get("latitude"))
    longitude = _coerce_float(address.get("longitude"))

    return ShopifyCustomerLookupAddressResult(
        street_address=_first_non_blank(_clean_str(address.get("address1")), _clean_str(address.get("address2"))),
        post_code=_clean_str(address.get("zip")),
        coordinates=ShopifyCustomerLookupCoordinatesResult(latitude=latitude, longitude=longitude),
        city=_clean_str(address.get("city")),
        district=_clean_str(address.get("province")),
    )


def _build_name(address: dict) -> str | None:
    first_name = _clean_str(address.get("firstName"))
    last_name = _clean_str(address.get("lastName"))
    if first_name and last_name:
        return f"{first_name} {last_name}"
    return first_name or last_name


def _first_non_blank(*values: str | None) -> str | None:
    for value in values:
        if value is not None:
            return value
    return None


def _clean_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _coerce_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None
