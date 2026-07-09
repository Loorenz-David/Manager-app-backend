from __future__ import annotations

import pytest

from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum
from beyo_manager.errors.external_service import ExternalServiceError, ShopifyGraphQLRetryableError
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.shopify.lookup_shopify_customers_by_product_identity import (
    lookup_shopify_customers_by_product_identity,
    parse_shopify_product_identity_lookup_request,
)


class _FakeScalarResult:
    def __init__(self, rows: list[ShopifyShopIntegration]) -> None:
        self._rows = rows

    def all(self) -> list[ShopifyShopIntegration]:
        return self._rows


class _FakeExecuteResult:
    def __init__(self, rows: list[ShopifyShopIntegration]) -> None:
        self._rows = rows

    def scalars(self) -> _FakeScalarResult:
        return _FakeScalarResult(self._rows)


class _FakeSession:
    def __init__(self, rows: list[ShopifyShopIntegration]) -> None:
        self._rows = rows

    async def execute(self, _query) -> _FakeExecuteResult:
        return _FakeExecuteResult(self._rows)


def _ctx(*, workspace_id: str, incoming_data: dict, rows: list[ShopifyShopIntegration]) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "role_name": "admin", "user_id": "usr_1"},
        incoming_data=incoming_data,
        session=_FakeSession(rows=rows),
    )


def _integration(
    *,
    client_id: str,
    workspace_id: str,
    shop_domain: str,
    granted_scopes: list[str] | None,
    status: ShopifyIntegrationStatusEnum = ShopifyIntegrationStatusEnum.ACTIVE,
) -> ShopifyShopIntegration:
    return ShopifyShopIntegration(
        client_id=client_id,
        workspace_id=workspace_id,
        shop_domain=shop_domain,
        provider="shopify",
        status=status,
        access_token_encrypted="encrypted-token",
        granted_scopes=granted_scopes,
        requested_scopes=["read_orders", "read_products", "read_customers"],
        api_version="2026-01",
    )


@pytest.mark.unit
def test_parse_shopify_product_identity_lookup_request_rejects_blank_input() -> None:
    with pytest.raises(ValidationError) as exc_info:
        parse_shopify_product_identity_lookup_request({"sku": " ", "article_number": ""})

    assert "At least one of sku or article_number is required." in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lookup_shopify_customers_by_product_identity_uses_sku_first_and_reports_missing_scopes(monkeypatch) -> None:
    workspace_id = "ws_1"
    matching = _integration(
        client_id="shpint_match",
        workspace_id=workspace_id,
        shop_domain="matching-shop.myshopify.com",
        granted_scopes=["read_orders", "read_products", "read_customers"],
    )
    missing_scope = _integration(
        client_id="shpint_missing",
        workspace_id=workspace_id,
        shop_domain="missing-shop.myshopify.com",
        granted_scopes=["read_orders", "read_products"],
    )

    async def _fake_fetch(**kwargs):
        if kwargs["shop_domain"] != matching.shop_domain:
            raise AssertionError("Shops without required scopes must not be queried.")
        assert kwargs["identity_type"] == "sku"
        return [
            {
                "id": "gid://shopify/Order/1",
                "name": "#1001",
                "email": "order@example.com",
                "phone": "111",
                "customer": {
                    "id": "gid://shopify/Customer/1",
                    "displayName": "Customer Name",
                    "defaultEmailAddress": {"emailAddress": "customer@example.com"},
                    "defaultPhoneNumber": {"phoneNumber": "222"},
                    "defaultAddress": {},
                },
                "shippingAddress": {
                    "address1": "Ship Street",
                    "zip": "12345",
                    "city": "Ship City",
                    "province": "Ship Province",
                },
                "billingAddress": {},
                "lineItems": {"edges": [{"node": {"sku": "SKU-123", "variant": {"barcode": "BAR-123"}}}]},
            }
        ]

    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.lookup_shopify_customers_by_product_identity.fetch_shopify_orders_by_product_identity",
        _fake_fetch,
    )

    result = await lookup_shopify_customers_by_product_identity(
        _ctx(
            workspace_id=workspace_id,
            incoming_data={"sku": "SKU-123", "article_number": "BAR-123"},
            rows=[matching, missing_scope],
        )
    )

    assert len(result["customer_matches"]) == 1
    assert result["customer_matches"][0]["shop_integration_id"] == matching.client_id
    assert result["customer_matches"][0]["match_type"] == "sku"
    assert result["failed_shops"] == [
        {
            "shop_integration_id": missing_scope.client_id,
            "shop_domain": missing_scope.shop_domain,
            "error_code": "missing_required_scope",
        }
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lookup_shopify_customers_by_product_identity_skips_missing_access_token_without_attempting_fetch(monkeypatch) -> None:
    workspace_id = "ws_1"
    tokenless = _integration(
        client_id="shpint_missing_token",
        workspace_id=workspace_id,
        shop_domain="tokenless-shop.myshopify.com",
        granted_scopes=["read_orders", "read_products", "read_customers"],
    )
    tokenless.access_token_encrypted = "   "

    async def _fake_fetch(**kwargs):
        raise AssertionError("Shops without access tokens must not be queried.")

    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.lookup_shopify_customers_by_product_identity.fetch_shopify_orders_by_product_identity",
        _fake_fetch,
    )

    result = await lookup_shopify_customers_by_product_identity(
        _ctx(workspace_id=workspace_id, incoming_data={"sku": "SKU-123"}, rows=[tokenless])
    )

    assert result["customer_matches"] == []
    assert result["failed_shops"] == [
        {
            "shop_integration_id": tokenless.client_id,
            "shop_domain": tokenless.shop_domain,
            "error_code": "missing_access_token",
        }
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lookup_shopify_customers_by_product_identity_falls_back_to_barcode_when_sku_has_no_matches(monkeypatch) -> None:
    workspace_id = "ws_1"
    integration = _integration(
        client_id="shpint_1",
        workspace_id=workspace_id,
        shop_domain="shop-a.myshopify.com",
        granted_scopes=["read_orders", "read_products", "read_customers"],
    )
    calls: list[tuple[str, str]] = []

    async def _fake_fetch(**kwargs):
        calls.append((kwargs["identity_type"], kwargs["identity_value"]))
        if kwargs["identity_type"] == "sku":
            return []
        return [
            {
                "id": "gid://shopify/Order/2",
                "name": "#1002",
                "email": "order@example.com",
                "phone": None,
                "customer": None,
                "shippingAddress": {
                    "firstName": "Guest",
                    "lastName": "Buyer",
                    "address1": "Guest Street",
                    "zip": "12345",
                    "city": "Stockholm",
                    "provinceCode": "AB",
                },
                "billingAddress": {},
                "lineItems": {"edges": [{"node": {"sku": "SKU-123", "variant": {"barcode": "BAR-123"}}}]},
            }
        ]

    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.lookup_shopify_customers_by_product_identity.fetch_shopify_orders_by_product_identity",
        _fake_fetch,
    )

    result = await lookup_shopify_customers_by_product_identity(
        _ctx(
            workspace_id=workspace_id,
            incoming_data={"sku": "SKU-123", "article_number": "BAR-123"},
            rows=[integration],
        )
    )

    assert calls == [("sku", "SKU-123"), ("barcode", "BAR-123")]
    assert result["customer_matches"][0]["shop_integration_id"] == integration.client_id
    assert result["customer_matches"][0]["match_type"] == "barcode"
    assert result["customer_matches"][0]["display_name"] == "Guest Buyer"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lookup_shopify_customers_by_product_identity_raises_when_all_attempted_shops_fail(monkeypatch) -> None:
    workspace_id = "ws_1"
    first = _integration(
        client_id="shpint_1",
        workspace_id=workspace_id,
        shop_domain="shop-a.myshopify.com",
        granted_scopes=["read_orders", "read_products", "read_customers"],
    )
    second = _integration(
        client_id="shpint_2",
        workspace_id=workspace_id,
        shop_domain="shop-b.myshopify.com",
        granted_scopes=["read_orders", "read_products", "read_customers"],
    )

    async def _fake_fetch(**kwargs):
        raise ShopifyGraphQLRetryableError("Timed out.", error_code="timeout")

    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.lookup_shopify_customers_by_product_identity.fetch_shopify_orders_by_product_identity",
        _fake_fetch,
    )

    with pytest.raises(ExternalServiceError) as exc_info:
        await lookup_shopify_customers_by_product_identity(
            _ctx(workspace_id=workspace_id, incoming_data={"sku": "SKU-123"}, rows=[first, second])
        )

    assert str(exc_info.value) == "All Shopify shop lookups failed."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lookup_shopify_customers_by_product_identity_still_raises_all_shops_failed_when_other_shop_is_missing_token(monkeypatch) -> None:
    workspace_id = "ws_1"
    attempted = _integration(
        client_id="shpint_1",
        workspace_id=workspace_id,
        shop_domain="shop-a.myshopify.com",
        granted_scopes=["read_orders", "read_products", "read_customers"],
    )
    tokenless = _integration(
        client_id="shpint_2",
        workspace_id=workspace_id,
        shop_domain="shop-b.myshopify.com",
        granted_scopes=["read_orders", "read_products", "read_customers"],
    )
    tokenless.access_token_encrypted = None

    async def _fake_fetch(**kwargs):
        raise ShopifyGraphQLRetryableError("Timed out.", error_code="timeout")

    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.lookup_shopify_customers_by_product_identity.fetch_shopify_orders_by_product_identity",
        _fake_fetch,
    )

    with pytest.raises(ExternalServiceError) as exc_info:
        await lookup_shopify_customers_by_product_identity(
            _ctx(workspace_id=workspace_id, incoming_data={"sku": "SKU-123"}, rows=[attempted, tokenless])
        )

    assert str(exc_info.value) == "All Shopify shop lookups failed."
