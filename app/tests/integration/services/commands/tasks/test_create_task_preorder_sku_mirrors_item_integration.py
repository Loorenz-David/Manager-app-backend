from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.shopify.shopify_product_sync_item import ShopifyProductSyncItem
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.sku_templates.create_sku_template import create_sku_template
from beyo_manager.services.commands.tasks.create_task import create_task
from beyo_manager.services.context import ServiceContext


def _ctx(session, *, workspace_id: str, user_id: str, incoming_data: dict) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "manager",
            "username": "tester",
        },
        incoming_data=incoming_data,
        session=session,
    )


async def _seed_workspace_user_and_shop(db_session) -> tuple[Workspace, User, ShopifyShopIntegration]:
    suffix = uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    shop = ShopifyShopIntegration(
        workspace_id=workspace.client_id,
        shop_domain=f"shop-{suffix}.myshopify.com",
        provider="shopify",
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        access_token_encrypted="encrypted-token",
        granted_scopes=["read_products", "write_products", "read_locations", "write_inventory"],
        requested_scopes=[],
        api_version="2026-01",
        installed_at=now,
        last_connected_at=now,
        created_by_id=user.client_id,
        updated_by_id=user.client_id,
        created_at=now,
        updated_at=now,
    )
    db_session.add(shop)
    await db_session.flush()
    return workspace, user, shop


async def _disable_event_dispatch(monkeypatch) -> None:
    async def _noop_dispatch(_events):
        return None

    monkeypatch.setattr("beyo_manager.services.commands.tasks.create_task.event_bus.dispatch", _noop_dispatch)


def _preorder_section(
    shop_id: str, *, sku: str | None = None, title: str | None = "Oak chair"
) -> dict:
    product = {"price": "5200.00"}
    if title is not None:
        product["title"] = title
    if sku is not None:
        product["sku"] = sku
    return {
        "shop_integration_id": shop_id,
        "product": product,
        "inventory": [{"location_id": "gid://shopify/Location/1", "quantity": 2}],
    }


@pytest.mark.integration
async def test_preorder_product_sku_defaults_to_the_auto_assigned_item_sku(db_session, monkeypatch):
    workspace, user, shop = await _seed_workspace_user_and_shop(db_session)
    await _disable_event_dispatch(monkeypatch)
    await create_sku_template(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"task_type": "pre_order", "prefix": "PRE"},
        )
    )

    result = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "task_type": "pre_order",
                "title": "Pre-order chair",
                "item": {"article_number": "ART-1"},
                "shopify_preorder": _preorder_section(shop.client_id),
            },
        )
    )

    assert result["item_sku"] == "PRE-1"
    item = await db_session.get(Item, result["item_id"])
    assert item.sku == "PRE-1"

    sync_item = (
        await db_session.execute(
            select(ShopifyProductSyncItem).where(
                ShopifyProductSyncItem.client_id == result["shopify_preorder"]["preorder_operation_id"]
            )
        )
    ).scalar_one()
    assert sync_item.normalized_payload_json["variant"]["inventoryItem"]["sku"] == "PRE-1"


@pytest.mark.integration
async def test_preorder_product_sku_override_wins_over_the_item_sku(db_session, monkeypatch):
    workspace, user, shop = await _seed_workspace_user_and_shop(db_session)
    await _disable_event_dispatch(monkeypatch)
    await create_sku_template(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"task_type": "pre_order", "prefix": "PRE"},
        )
    )

    result = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "task_type": "pre_order",
                "title": "Pre-order chair",
                "item": {"article_number": "ART-1"},
                "shopify_preorder": _preorder_section(shop.client_id, sku="CUSTOM-OVERRIDE"),
            },
        )
    )

    # The local item still gets the auto-assigned, gapless sku...
    assert result["item_sku"] == "PRE-1"
    item = await db_session.get(Item, result["item_id"])
    assert item.sku == "PRE-1"

    # ...but the caller explicitly asked the Shopify product to carry a different sku, and that wins.
    sync_item = (
        await db_session.execute(
            select(ShopifyProductSyncItem).where(
                ShopifyProductSyncItem.client_id == result["shopify_preorder"]["preorder_operation_id"]
            )
        )
    ).scalar_one()
    assert sync_item.normalized_payload_json["variant"]["inventoryItem"]["sku"] == "CUSTOM-OVERRIDE"


@pytest.mark.integration
async def test_preorder_product_title_defaults_to_the_resolved_sku_when_omitted(db_session, monkeypatch):
    workspace, user, shop = await _seed_workspace_user_and_shop(db_session)
    await _disable_event_dispatch(monkeypatch)
    await create_sku_template(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"task_type": "pre_order", "prefix": "PRE"},
        )
    )

    result = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "task_type": "pre_order",
                "title": "Pre-order chair",
                "item": {"article_number": "ART-1"},
                "shopify_preorder": _preorder_section(shop.client_id, title=None),
            },
        )
    )

    assert result["item_sku"] == "PRE-1"
    sync_item = (
        await db_session.execute(
            select(ShopifyProductSyncItem).where(
                ShopifyProductSyncItem.client_id == result["shopify_preorder"]["preorder_operation_id"]
            )
        )
    ).scalar_one()
    assert sync_item.normalized_payload_json["product"]["title"] == "PRE-1"


@pytest.mark.integration
async def test_preorder_product_title_override_wins_over_the_sku_default(db_session, monkeypatch):
    workspace, user, shop = await _seed_workspace_user_and_shop(db_session)
    await _disable_event_dispatch(monkeypatch)
    await create_sku_template(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"task_type": "pre_order", "prefix": "PRE"},
        )
    )

    result = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "task_type": "pre_order",
                "title": "Pre-order chair",
                "item": {"article_number": "ART-1"},
                "shopify_preorder": _preorder_section(shop.client_id, title="Solid Oak Armchair"),
            },
        )
    )

    assert result["item_sku"] == "PRE-1"
    sync_item = (
        await db_session.execute(
            select(ShopifyProductSyncItem).where(
                ShopifyProductSyncItem.client_id == result["shopify_preorder"]["preorder_operation_id"]
            )
        )
    ).scalar_one()
    assert sync_item.normalized_payload_json["product"]["title"] == "Solid Oak Armchair"
