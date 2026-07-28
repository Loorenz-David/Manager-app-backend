from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from beyo_manager.domain.execution.enums import ExecutionTaskStateEnum, TaskType
from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventTypeEnum,
    ShopifyIntegrationStatusEnum,
    ShopifyInventoryModeEnum,
)
from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.execution.execution_task import ExecutionTask
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.shopify.shopify_integration_event import (
    ShopifyIntegrationEvent,
)
from beyo_manager.models.tables.shopify.shopify_product_sync_item import (
    ShopifyProductSyncItem,
)
from beyo_manager.models.tables.shopify.shopify_shop_integration import (
    ShopifyShopIntegration,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.tasks.create_task import create_task
from beyo_manager.services.context import ServiceContext


async def _seed_context(db_session, *, role_name: str = "seller") -> ServiceContext:
    suffix = uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    workspace = Workspace(
        client_id=f"ws_{suffix}",
        name=f"Workspace {suffix}",
    )
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    shop = ShopifyShopIntegration(
        workspace_id=workspace.client_id,
        shop_domain=f"shop-{suffix}.myshopify.com",
        provider="shopify",
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        access_token_encrypted="encrypted-token",
        granted_scopes=[
            "read_products",
            "write_products",
            "read_locations",
            "write_inventory",
        ],
        requested_scopes=[],
        api_version="2026-01",
        installed_at=now,
        last_connected_at=now,
        created_by_id=user.client_id,
        updated_by_id=user.client_id,
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    db_session.add(shop)
    await db_session.flush()
    return ServiceContext(
        identity={
            "workspace_id": workspace.client_id,
            "user_id": user.client_id,
            "role_name": role_name,
            "username": user.username,
        },
        incoming_data={
            "task_type": "pre_order",
            "title": "Pre-order chair",
            "shopify_preorder": {
                "shop_integration_id": shop.client_id,
                "product": {
                    "title": "Oak chair",
                    "sku": "SKU-PREORDER-1",
                    "price": "5200.00",
                    # No `quantity` metafield — the backend derives it from `inventory`.
                    "metafields": {
                        "notes": "handle with care",
                    },
                },
                "inventory": [
                    {
                        "location_id": "gid://shopify/Location/1",
                        "quantity": 2,
                    }
                ],
            },
        },
        session=db_session,
    )


async def _disable_event_dispatch(monkeypatch) -> None:
    async def _noop_dispatch(_events):
        return None

    monkeypatch.setattr(
        "beyo_manager.services.commands.tasks.create_task.event_bus.dispatch",
        _noop_dispatch,
    )


@pytest.mark.integration
async def test_create_task_commits_preorder_intent_atomically_without_shopify_http(
    db_session,
    monkeypatch,
) -> None:
    ctx = await _seed_context(db_session)
    await _disable_event_dispatch(monkeypatch)
    graphql_calls = 0

    async def _unexpected_graphql(**_kwargs):
        nonlocal graphql_calls
        graphql_calls += 1
        raise AssertionError("Shopify HTTP must not run during create_task")

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.graphql_client.execute_shopify_graphql",
        _unexpected_graphql,
    )

    result = await create_task(ctx)
    sync_item = (
        await db_session.execute(
            select(ShopifyProductSyncItem).where(
                ShopifyProductSyncItem.frontend_client_id == result["client_id"]
            )
        )
    ).scalar_one()
    execution_task = (
        await db_session.execute(
            select(ExecutionTask).where(
                ExecutionTask.client_id
                == result["shopify_preorder"]["shopify_task_id"],
                ExecutionTask.task_type == TaskType.SHOPIFY_PROCESS_PRODUCTS,
            )
        )
    ).scalar_one()
    event = (
        await db_session.execute(
            select(ShopifyIntegrationEvent).where(
                ShopifyIntegrationEvent.event_type
                == ShopifyIntegrationEventTypeEnum.PREORDER,
                ShopifyIntegrationEvent.workspace_id == ctx.workspace_id,
            )
        )
    ).scalar_one()

    assert result["shopify_preorder"]["preorder_operation_id"] == sync_item.client_id
    assert result["shopify_preorder"]["shopify_task_id"] == execution_task.client_id
    assert sync_item.inventory_mode == ShopifyInventoryModeEnum.SET
    assert sync_item.normalized_payload_json["product"]["status"] == "UNLISTED"
    # `custom.quantity` is derived from the inventory selection (one location, quantity 2), not
    # taken from the caller. The fixture supplies a different metafield to prove the caller's
    # other metafields still pass through.
    metafields = {entry["key"]: entry for entry in sync_item.normalized_payload_json["metafields"]}
    assert metafields["quantity"]["value"] == "2"
    assert metafields["quantity"]["type"] == "single_line_text_field"
    assert metafields["notes"]["value"] == "handle with care"
    # Absolute targets for inventorySetQuantities, shared with ordinary product sync.
    assert sync_item.normalized_payload_json["inventory"]["quantities"] == [
        {"location_id": "gid://shopify/Location/1", "quantity": 2}
    ]
    assert "adjustments" not in sync_item.normalized_payload_json["inventory"]
    assert execution_task.state == ExecutionTaskStateEnum.OPEN
    assert event.metadata_json["task_id"] == result["client_id"]
    assert graphql_calls == 0


@pytest.mark.integration
async def test_create_task_rolls_back_task_sync_item_and_execution_task_together(
    db_session,
    monkeypatch,
) -> None:
    execution_task_count_before = await db_session.scalar(
        select(func.count()).select_from(ExecutionTask)
    )
    ctx = await _seed_context(db_session)
    await _disable_event_dispatch(monkeypatch)

    async def _fail_after_preorder_is_staged(**_kwargs):
        raise RuntimeError("later task write failed")

    monkeypatch.setattr(
        "beyo_manager.services.commands.tasks.create_task._create_history_record_in_session",
        _fail_after_preorder_is_staged,
    )

    with pytest.raises(RuntimeError, match="later task write failed"):
        await create_task(ctx)
    await db_session.rollback()

    assert (
        await db_session.scalar(
            select(func.count()).select_from(Task).where(
                Task.workspace_id == ctx.workspace_id
            )
        )
        == 0
    )
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(ShopifyProductSyncItem)
            .where(ShopifyProductSyncItem.workspace_id == ctx.workspace_id)
        )
        == 0
    )
    assert (
        await db_session.scalar(select(func.count()).select_from(ExecutionTask))
        == execution_task_count_before
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    ("task_type", "role_name", "error"),
    [
        ("internal", "seller", ValidationError),
        ("pre_order", "worker", PermissionDenied),
    ],
)
async def test_create_task_rejects_invalid_preorder_gate_before_writes(
    db_session,
    monkeypatch,
    task_type: str,
    role_name: str,
    error: type[Exception],
) -> None:
    ctx = await _seed_context(db_session, role_name=role_name)
    ctx.incoming_data["task_type"] = task_type
    await _disable_event_dispatch(monkeypatch)

    with pytest.raises(error):
        await create_task(ctx)

    assert (
        await db_session.scalar(
            select(func.count()).select_from(Task).where(
                Task.workspace_id == ctx.workspace_id
            )
        )
        == 0
    )
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(ShopifyProductSyncItem)
            .where(ShopifyProductSyncItem.workspace_id == ctx.workspace_id)
        )
        == 0
    )


@pytest.mark.integration
async def test_product_category_defaults_to_the_task_item_category_name(
    db_session,
    monkeypatch,
) -> None:
    """Shopify's productType falls back to the item's category, so a seller who already
    categorised the item does not restate it in the Shopify section."""
    ctx = await _seed_context(db_session)
    category = ItemCategory(
        client_id=f"itc_{uuid4().hex[:8]}",
        workspace_id=ctx.workspace_id,
        name="Armchair",
        major_category=ItemMajorCategoryEnum.SEAT,
    )
    db_session.add(category)
    await db_session.flush()

    ctx.incoming_data["item"] = {
        "sku": "SKU-PREORDER-1",
        "item_category_id": category.client_id,
    }
    await _disable_event_dispatch(monkeypatch)

    result = await create_task(ctx)

    sync_item = (
        await db_session.execute(
            select(ShopifyProductSyncItem).where(
                ShopifyProductSyncItem.client_id
                == result["shopify_preorder"]["preorder_operation_id"]
            )
        )
    ).scalar_one()
    assert sync_item.normalized_payload_json["product"]["productType"] == "Armchair"


@pytest.mark.integration
async def test_explicit_product_category_wins_over_the_item_category(
    db_session,
    monkeypatch,
) -> None:
    # Unlike the quantity metafield, product_category is a product attribute a seller may
    # legitimately want to differ from the internal category, so an explicit value is honoured.
    ctx = await _seed_context(db_session)
    category = ItemCategory(
        client_id=f"itc_{uuid4().hex[:8]}",
        workspace_id=ctx.workspace_id,
        name="Armchair",
        major_category=ItemMajorCategoryEnum.SEAT,
    )
    db_session.add(category)
    await db_session.flush()

    ctx.incoming_data["item"] = {
        "sku": "SKU-PREORDER-1",
        "item_category_id": category.client_id,
    }
    ctx.incoming_data["shopify_preorder"]["product"]["product_category"] = "Custom Sofa"
    await _disable_event_dispatch(monkeypatch)

    result = await create_task(ctx)

    sync_item = (
        await db_session.execute(
            select(ShopifyProductSyncItem).where(
                ShopifyProductSyncItem.client_id
                == result["shopify_preorder"]["preorder_operation_id"]
            )
        )
    ).scalar_one()
    assert sync_item.normalized_payload_json["product"]["productType"] == "Custom Sofa"


@pytest.mark.integration
async def test_no_item_section_leaves_product_type_unset(
    db_session,
    monkeypatch,
) -> None:
    ctx = await _seed_context(db_session)
    ctx.incoming_data.pop("item", None)
    await _disable_event_dispatch(monkeypatch)

    result = await create_task(ctx)

    sync_item = (
        await db_session.execute(
            select(ShopifyProductSyncItem).where(
                ShopifyProductSyncItem.client_id
                == result["shopify_preorder"]["preorder_operation_id"]
            )
        )
    ).scalar_one()
    assert "productType" not in sync_item.normalized_payload_json["product"]
