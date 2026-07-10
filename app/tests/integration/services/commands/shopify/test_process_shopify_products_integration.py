from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventTypeEnum,
    ShopifyIntegrationStatusEnum,
    ShopifyProductSyncItemStatusEnum,
)
from beyo_manager.models.tables.shopify.shopify_integration_event import ShopifyIntegrationEvent
from beyo_manager.models.tables.shopify.shopify_product_sync_item import ShopifyProductSyncItem
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.shopify.process_shopify_products import process_shopify_products
from beyo_manager.services.context import ServiceContext
from beyo_manager.errors.not_found import NotFound


def _ctx(db_session, *, workspace_id: str, user_id: str, incoming_data: dict) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": user_id, "role_name": "admin"},
        incoming_data=incoming_data,
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
    user_id: str,
    status: ShopifyIntegrationStatusEnum,
) -> ShopifyShopIntegration:
    suffix = uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    integration = ShopifyShopIntegration(
        workspace_id=workspace_id,
        shop_domain=f"shop-{suffix}.myshopify.com",
        provider="shopify",
        status=status,
        access_token_encrypted="encrypted-token",
        granted_scopes=["write_products"],
        requested_scopes=["write_products"],
        api_version="2026-01",
        installed_at=now,
        last_connected_at=now,
        created_by_id=user_id,
        updated_by_id=user_id,
        created_at=now,
        updated_at=now,
    )
    db_session.add(integration)
    await db_session.flush()
    return integration


@pytest.mark.integration
async def test_process_shopify_products_fans_out_to_all_active_workspace_shops_and_enqueues_one_task(
    db_session,
    monkeypatch,
) -> None:
    workspace, other_workspace, user = await _seed_workspace_and_user(db_session)
    active_one = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
    )
    active_two = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
    )
    await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.DISABLED,
    )
    await _seed_integration(
        db_session,
        workspace_id=other_workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
    )
    await db_session.commit()

    captured: dict = {}
    graphql_calls = {"count": 0}

    async def _fake_create_instant_task(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(client_id="task_shopify_products_1")

    async def _unexpected_graphql_call(**_kwargs):
        graphql_calls["count"] += 1
        raise AssertionError("Shopify GraphQL should not be called synchronously by the command")

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.process_shopify_products.create_instant_task",
        _fake_create_instant_task,
    )
    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.graphql_client.execute_shopify_graphql",
        _unexpected_graphql_call,
    )

    result = await process_shopify_products(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "items": [
                    {
                        "client_id": "frontend_1",
                        "title": "Chair",
                        "sku": "SKU-123",
                        "metafields": {"origin": "warehouse"},
                    }
                ]
            },
        )
    )

    rows = (
        await db_session.execute(
            select(ShopifyProductSyncItem).where(ShopifyProductSyncItem.workspace_id == workspace.client_id)
        )
    ).scalars().all()
    events = (
        await db_session.execute(
            select(ShopifyIntegrationEvent).where(
                ShopifyIntegrationEvent.workspace_id == workspace.client_id,
                ShopifyIntegrationEvent.event_type == ShopifyIntegrationEventTypeEnum.PRODUCT_SYNC,
            )
        )
    ).scalars().all()

    assert result == {
        "queued": True,
        "task_id": "task_shopify_products_1",
        "sync_item_client_ids": [row.client_id for row in rows],
        "target_count": 2,
    }
    assert len(rows) == 2
    assert {row.shop_integration_id for row in rows} == {active_one.client_id, active_two.client_id}
    assert all(row.status == ShopifyProductSyncItemStatusEnum.PENDING for row in rows)
    assert len(events) == 2
    assert captured["task_type"] == TaskType.SHOPIFY_PROCESS_PRODUCTS
    assert captured["payload"]["workspace_id"] == workspace.client_id
    assert captured["payload"]["requested_by_user_id"] == user.client_id
    assert captured["payload"]["sync_item_client_ids"] == [row.client_id for row in rows]
    assert captured["event_client_id"] in {event.client_id for event in events}
    assert graphql_calls["count"] == 0


@pytest.mark.integration
async def test_process_shopify_products_rejects_foreign_or_inactive_explicit_shop_targets(
    db_session,
    monkeypatch,
) -> None:
    workspace, other_workspace, user = await _seed_workspace_and_user(db_session)
    inactive = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.DISABLED,
    )
    foreign = await _seed_integration(
        db_session,
        workspace_id=other_workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
    )
    active = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
    )
    await db_session.commit()

    async def _fake_create_instant_task(**_kwargs):
        return SimpleNamespace(client_id="task_should_not_exist")

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.process_shopify_products.create_instant_task",
        _fake_create_instant_task,
    )

    with pytest.raises(NotFound, match="Shopify shop integration not found"):
        await process_shopify_products(
            _ctx(
                db_session,
                workspace_id=workspace.client_id,
                user_id=user.client_id,
                incoming_data={
                    "items": [
                        {
                            "client_id": "frontend_1",
                            "title": "Chair",
                            "sku": "SKU-123",
                            "target_shop_integration_ids": [active.client_id, inactive.client_id, foreign.client_id],
                        }
                    ]
                },
            )
        )


@pytest.mark.integration
async def test_process_shopify_products_dedupes_duplicate_target_shop_integration_ids(
    db_session,
    monkeypatch,
) -> None:
    workspace, _other_workspace, user = await _seed_workspace_and_user(db_session)
    active = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
    )
    await db_session.commit()

    async def _fake_create_instant_task(**_kwargs):
        return SimpleNamespace(client_id="task_dedupe_1")

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.process_shopify_products.create_instant_task",
        _fake_create_instant_task,
    )

    result = await process_shopify_products(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "items": [
                    {
                        "client_id": "frontend_1",
                        "title": "Chair",
                        "sku": "SKU-123",
                        "target_shop_integration_ids": [active.client_id, active.client_id],
                    }
                ]
            },
        )
    )

    rows = (
        await db_session.execute(
            select(ShopifyProductSyncItem).where(ShopifyProductSyncItem.workspace_id == workspace.client_id)
        )
    ).scalars().all()

    assert len(rows) == 1
    assert result["target_count"] == 1
