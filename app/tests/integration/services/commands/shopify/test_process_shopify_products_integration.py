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
    ShopifyInventoryModeEnum,
    ShopifyProductSyncOriginEnum,
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
                        "inventory_quantities": [
                            {
                                "shop_integration_id": active_one.client_id,
                                "location_id": "gid://shopify/Location/1",
                                "quantity": 0,
                            }
                        ],
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

    # One event per distinct target shop, so a subordinate caller can annotate its own event
    # without re-querying by metadata. Compared as a set: the command returns them in
    # target order, while this query has no ORDER BY.
    assert set(result.pop("event_client_ids")) == {event.client_id for event in events}
    # Same reason as the events assertion above: the command returns the sync items
    # in target order while this query has no ORDER BY, so an ordered comparison is
    # a flake waiting for a different heap order.
    assert set(result.pop("sync_item_client_ids")) == {row.client_id for row in rows}
    assert result == {
        "queued": True,
        "task_id": "task_shopify_products_1",
        "target_count": 2,
    }
    assert len(rows) == 2
    assert {row.shop_integration_id for row in rows} == {active_one.client_id, active_two.client_id}
    assert all(row.status == ShopifyProductSyncItemStatusEnum.PENDING for row in rows)
    assert all(row.inventory_mode == ShopifyInventoryModeEnum.SET for row in rows)
    assert all(
        row.sync_origin
        == ShopifyProductSyncOriginEnum.STANDARD_PRODUCT_SYNC.value
        for row in rows
    )
    assert all(row.source_entity_type is None for row in rows)
    assert all(row.source_entity_id is None for row in rows)
    payload_by_shop = {
        row.shop_integration_id: row.normalized_payload_json
        for row in rows
    }
    assert payload_by_shop[active_one.client_id]["inventory"] == {
        "quantities": [
            {
                "location_id": "gid://shopify/Location/1",
                "quantity": 0,
            }
        ]
    }
    assert "inventory" not in payload_by_shop[active_two.client_id]
    assert len(events) == 2
    assert captured["task_type"] == TaskType.SHOPIFY_PROCESS_PRODUCTS
    assert captured["payload"]["workspace_id"] == workspace.client_id
    assert captured["payload"]["requested_by_user_id"] == user.client_id
    # Unordered for the same reason as above: `rows` comes from a query with no ORDER BY.
    assert sorted(captured["payload"]["sync_item_client_ids"]) == sorted(row.client_id for row in rows)
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


# --- Worker product form: item link + SKU fill -------------------------------------------


async def _seed_item(db_session, *, workspace_id: str, user_id: str, sku: str | None = None):
    from beyo_manager.models.tables.items.item import Item

    item = Item(
        client_id=f"itm_{uuid4().hex[:10]}",
        workspace_id=workspace_id,
        created_by_id=user_id,
        sku=sku,
    )
    db_session.add(item)
    await db_session.flush()
    return item


def _patch_task_factory(monkeypatch) -> dict:
    captured: dict = {"calls": 0}

    async def _fake_create_instant_task(**kwargs):
        captured["calls"] += 1
        captured.update(kwargs)
        return SimpleNamespace(client_id="task_shopify_products_item")

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.process_shopify_products.create_instant_task",
        _fake_create_instant_task,
    )
    return captured


async def _seed_item_scenario(db_session, *, item_sku: str | None):
    workspace, _other, user = await _seed_workspace_and_user(db_session)
    shop = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
    )
    item = await _seed_item(
        db_session, workspace_id=workspace.client_id, user_id=user.client_id, sku=item_sku
    )
    await db_session.commit()
    return workspace, user, shop, item


def _item_request(item_client_id: str, *, sku: str | None) -> dict:
    return {
        "items": [
            {
                "client_id": item_client_id,
                "item_client_id": item_client_id,
                "title": "Chair",
                "sku": sku,
                "item_article_number": "ART-1",
            }
        ]
    }


@pytest.mark.integration
async def test_process_fills_empty_item_sku_and_links_sync_rows_to_item(db_session, monkeypatch) -> None:
    from beyo_manager.models.tables.items.item import Item

    workspace, user, shop, item = await _seed_item_scenario(db_session, item_sku=None)
    captured = _patch_task_factory(monkeypatch)

    await process_shopify_products(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data=_item_request(item.client_id, sku="SKU-NEW"),
        )
    )

    refreshed = (
        await db_session.execute(select(Item).where(Item.client_id == item.client_id))
    ).scalar_one()
    await db_session.refresh(refreshed)
    assert refreshed.sku == "SKU-NEW"
    rows = (
        await db_session.execute(
            select(ShopifyProductSyncItem).where(ShopifyProductSyncItem.workspace_id == workspace.client_id)
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].source_entity_type == "item"
    assert rows[0].source_entity_id == item.client_id
    assert rows[0].shop_integration_id == shop.client_id
    assert captured["calls"] == 1


@pytest.mark.integration
async def test_process_never_overwrites_existing_item_sku(db_session, monkeypatch) -> None:
    from beyo_manager.models.tables.items.item import Item

    workspace, user, _shop, item = await _seed_item_scenario(db_session, item_sku="SKU-OLD")
    captured = _patch_task_factory(monkeypatch)

    await process_shopify_products(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data=_item_request(item.client_id, sku="SKU-OTHER"),
        )
    )

    refreshed = (
        await db_session.execute(select(Item).where(Item.client_id == item.client_id))
    ).scalar_one()
    await db_session.refresh(refreshed)
    assert refreshed.sku == "SKU-OLD"
    assert captured["calls"] == 1


@pytest.mark.integration
async def test_process_refuses_sku_used_by_another_item_and_queues_nothing(db_session, monkeypatch) -> None:
    from beyo_manager.errors.validation import ConflictError

    workspace, user, _shop, item = await _seed_item_scenario(db_session, item_sku=None)
    workspace_id, user_id, item_client_id = workspace.client_id, user.client_id, item.client_id
    await _seed_item(db_session, workspace_id=workspace_id, user_id=user_id, sku="SKU-TAKEN")
    await db_session.commit()
    captured = _patch_task_factory(monkeypatch)

    with pytest.raises(ConflictError, match="SKU-TAKEN"):
        await process_shopify_products(
            _ctx(
                db_session,
                workspace_id=workspace_id,
                user_id=user_id,
                incoming_data=_item_request(item_client_id, sku="SKU-TAKEN"),
            )
        )

    assert captured["calls"] == 0
    rows = (
        await db_session.execute(
            select(ShopifyProductSyncItem).where(ShopifyProductSyncItem.workspace_id == workspace_id)
        )
    ).scalars().all()
    assert rows == []


@pytest.mark.integration
async def test_process_rejects_unknown_item(db_session, monkeypatch) -> None:
    workspace, user, _shop, _item = await _seed_item_scenario(db_session, item_sku=None)
    captured = _patch_task_factory(monkeypatch)

    with pytest.raises(NotFound, match="Item not found"):
        await process_shopify_products(
            _ctx(
                db_session,
                workspace_id=workspace.client_id,
                user_id=user.client_id,
                incoming_data=_item_request("itm_missing", sku="SKU-1"),
            )
        )
    assert captured["calls"] == 0
