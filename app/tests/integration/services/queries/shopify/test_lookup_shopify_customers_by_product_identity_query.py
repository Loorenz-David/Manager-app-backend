from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.shopify.lookup_shopify_customers_by_product_identity import (
    lookup_shopify_customers_by_product_identity,
)


def unique_shop_domain(prefix: str = "shop") -> str:
    return f"{prefix}-{uuid4().hex}.myshopify.com"


def _ctx(db_session, *, workspace_id: str, incoming_data: dict | None = None) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "role_name": "admin", "user_id": "usr_1"},
        incoming_data=incoming_data or {},
        session=db_session,
    )


async def _seed_workspace_and_user(db_session) -> tuple[Workspace, Workspace, User]:
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    other_workspace = Workspace(client_id=f"ws_other_{suffix}", name=f"Other {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    db_session.add_all([workspace, other_workspace, user])
    await db_session.flush()
    return workspace, other_workspace, user


async def _seed_integration(
    db_session,
    *,
    workspace_id: str,
    user_id: str | None = None,
    status: ShopifyIntegrationStatusEnum,
    created_at: datetime,
    shop_domain: str,
) -> ShopifyShopIntegration:
    integration = ShopifyShopIntegration(
        workspace_id=workspace_id,
        shop_domain=shop_domain,
        provider="shopify",
        status=status,
        access_token_encrypted="encrypted-token",
        granted_scopes=["read_orders", "read_products", "read_customers"],
        requested_scopes=["read_orders", "read_products", "read_customers"],
        api_version="2026-01",
        installed_at=created_at,
        last_connected_at=created_at,
        created_by_id=user_id,
        updated_by_id=user_id,
        created_at=created_at,
        updated_at=created_at,
    )
    db_session.add(integration)
    await db_session.flush()
    return integration


@pytest.mark.integration
async def test_lookup_shopify_customers_by_product_identity_is_workspace_scoped_and_excludes_soft_deleted_and_inactive_shops(
    db_session,
    monkeypatch,
) -> None:
    workspace, other_workspace, user = await _seed_workspace_and_user(db_session)
    base = datetime(2026, 7, 9, tzinfo=timezone.utc)
    eligible = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        created_at=base,
        shop_domain=unique_shop_domain("eligible"),
    )
    deleted = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        created_at=base,
        shop_domain=unique_shop_domain("deleted"),
    )
    inactive = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.DISABLED,
        created_at=base,
        shop_domain=unique_shop_domain("inactive"),
    )
    other_workspace_shop = await _seed_integration(
        db_session,
        workspace_id=other_workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        created_at=base,
        shop_domain=unique_shop_domain("other"),
    )
    deleted.is_deleted = True
    await db_session.flush()

    calls: list[str] = []

    async def _fake_fetch(**kwargs):
        calls.append(kwargs["shop_domain"])
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
                "lineItems": {"edges": [{"node": {"sku": "SKU-TEST", "variant": {"barcode": "BAR-TEST"}}}]},
            }
        ]

    monkeypatch.setattr(
        "beyo_manager.services.queries.shopify.lookup_shopify_customers_by_product_identity.fetch_shopify_orders_by_product_identity",
        _fake_fetch,
    )

    result = await lookup_shopify_customers_by_product_identity(
        _ctx(db_session, workspace_id=workspace.client_id, incoming_data={"sku": "SKU-TEST"})
    )

    assert calls == [eligible.shop_domain]
    assert len(result["customer_matches"]) == 1
    assert result["customer_matches"][0]["shop_integration_id"] == eligible.client_id
    assert result["failed_shops"] == []
    assert deleted.shop_domain not in calls
    assert inactive.shop_domain not in calls
    assert other_workspace_shop.shop_domain not in calls
