from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.shopify.shopify_metafield_preference import ShopifyMetafieldPreference
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.shopify.create_shopify_metafield_preferences import (
    create_shopify_metafield_preferences,
)
from beyo_manager.services.context import ServiceContext


def _gid(number: str) -> str:
    return f"gid://shopify/MetafieldDefinition/{number}"


def _ctx(db_session, *, workspace_id: str, user_id: str, preferences: list[dict]) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": user_id, "role_name": "admin"},
        incoming_data={"item_category_id": "placeholder", "preferences": preferences},
        session=db_session,
    )


async def _seed_fixture(db_session, *, include_inactive: bool = False):
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    other_workspace = Workspace(client_id=f"ws_other_{suffix}", name=f"Other {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user-{suffix}",
        email=f"user-{suffix}@example.com",
        password="hashed",
    )
    category = ItemCategory(
        client_id=f"itc_{suffix}",
        workspace_id=workspace.client_id,
        name=f"Category {suffix}",
        major_category=ItemMajorCategoryEnum.SEAT,
        created_by_id=user.client_id,
    )
    now = datetime.now(timezone.utc)

    def _shop(client_id: str, workspace_id: str, domain: str, status: ShopifyIntegrationStatusEnum):
        return ShopifyShopIntegration(
            client_id=client_id,
            workspace_id=workspace_id,
            shop_domain=domain,
            status=status,
            api_version="2026-01",
            access_token_encrypted=f"encrypted-{client_id}",
            created_by_id=user.client_id,
            updated_by_id=user.client_id,
            created_at=now,
            updated_at=now,
        )

    shop_a = _shop(f"shpint_{suffix}_a", workspace.client_id, f"command-a-{suffix}.myshopify.com", ShopifyIntegrationStatusEnum.ACTIVE)
    shop_b = _shop(f"shpint_{suffix}_b", workspace.client_id, f"command-b-{suffix}.myshopify.com", ShopifyIntegrationStatusEnum.ACTIVE)
    inactive = _shop(f"shpint_{suffix}_inactive", workspace.client_id, f"command-inactive-{suffix}.myshopify.com", ShopifyIntegrationStatusEnum.DISABLED)
    foreign = _shop(f"shpint_{suffix}_foreign", other_workspace.client_id, f"command-foreign-{suffix}.myshopify.com", ShopifyIntegrationStatusEnum.ACTIVE)
    db_session.add_all([workspace, other_workspace, user])
    await db_session.flush()
    db_session.add_all([category, shop_a, shop_b, inactive, foreign])
    await db_session.commit()
    return workspace, other_workspace, user, category, shop_a, shop_b, inactive, foreign


def _selection(
    shop_id: str,
    definition_id: str,
    sequence_order: int,
    *,
    client_id: str | None = None,
) -> dict:
    selection = {
        "shop_integration_id": shop_id,
        "shopify_metafield_definition_id": definition_id,
        "sequence_order": sequence_order,
    }
    if client_id is not None:
        selection["client_id"] = client_id
    return selection


def _definition(definition_id: str, *, owner_type: str = "PRODUCT") -> dict:
    return {
        "id": definition_id,
        "ownerType": owner_type,
        "name": "Seat height",
        "namespace": "custom",
        "key": "seat_height",
        "description": None,
        "type": {"name": "dimension"},
        "validations": [],
    }


async def _run(db_session, *, workspace_id: str, user_id: str, category_id: str, selections: list[dict]):
    ctx = _ctx(db_session, workspace_id=workspace_id, user_id=user_id, preferences=selections)
    ctx.incoming_data["item_category_id"] = category_id
    return await create_shopify_metafield_preferences(ctx)


@pytest.mark.integration
async def test_create_preferences_across_two_shops_preserves_request_order_and_credentials(db_session, monkeypatch) -> None:
    workspace, _other, user, category, shop_a, shop_b, _inactive, _foreign = await _seed_fixture(db_session)
    definition_a = _gid("command-a")
    definition_b = _gid("command-b")
    calls: list[dict] = []

    async def _fake_fetch(**kwargs):
        calls.append(kwargs)
        return _definition(kwargs["definition_id"])

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.create_shopify_metafield_preferences.fetch_shopify_metafield_definition_by_id",
        _fake_fetch,
    )
    selections = [
        _selection(shop_b.client_id, definition_b, 7),
        _selection(shop_a.client_id, definition_a, 2),
    ]

    results = await _run(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        category_id=category.client_id,
        selections=selections,
    )

    assert [(result["shop_integration_id"], result["sequence_order"]) for result in results] == [
        (shop_b.client_id, 7),
        (shop_a.client_id, 2),
    ]
    assert {(call["shop_domain"], call["access_token_encrypted"]) for call in calls} == {
        (shop_a.shop_domain, shop_a.access_token_encrypted),
        (shop_b.shop_domain, shop_b.access_token_encrypted),
    }
    rows = (
        await db_session.execute(
            select(ShopifyMetafieldPreference).where(
                ShopifyMetafieldPreference.workspace_id == workspace.client_id
            )
        )
    ).scalars().all()
    assert {row.shop_integration_id for row in rows} == {shop_a.client_id, shop_b.client_id}


@pytest.mark.integration
async def test_create_allows_multiple_definitions_for_one_shop(db_session, monkeypatch) -> None:
    workspace, _other, user, category, shop_a, _shop_b, _inactive, _foreign = await _seed_fixture(db_session)
    definitions = [_gid("same-shop-1"), _gid("same-shop-2")]

    async def _fake_fetch(**kwargs):
        return _definition(kwargs["definition_id"])

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.create_shopify_metafield_preferences.fetch_shopify_metafield_definition_by_id",
        _fake_fetch,
    )
    await _run(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        category_id=category.client_id,
        selections=[
            _selection(shop_a.client_id, definitions[0], 0),
            _selection(shop_a.client_id, definitions[1], 1),
        ],
    )
    rows = (
        await db_session.execute(
            select(ShopifyMetafieldPreference).where(
                ShopifyMetafieldPreference.shop_integration_id == shop_a.client_id
            )
        )
    ).scalars().all()
    assert len(rows) == 2


@pytest.mark.integration
async def test_create_uses_client_supplied_id_for_new_preference(db_session, monkeypatch) -> None:
    workspace, _other, user, category, shop_a, _shop_b, _inactive, _foreign = await _seed_fixture(db_session)
    client_id = "shpmfp_01J00000000000000000000000"

    async def _fake_fetch(**kwargs):
        return _definition(kwargs["definition_id"])

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.create_shopify_metafield_preferences.fetch_shopify_metafield_definition_by_id",
        _fake_fetch,
    )
    results = await _run(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        category_id=category.client_id,
        selections=[
            _selection(
                shop_a.client_id,
                _gid("client-supplied-id"),
                0,
                client_id=client_id,
            )
        ],
    )

    assert results[0]["client_id"] == client_id
    assert await db_session.get(ShopifyMetafieldPreference, client_id) is not None


@pytest.mark.integration
async def test_second_shop_validation_failure_rolls_back_the_batch(db_session, monkeypatch) -> None:
    workspace, _other, user, category, shop_a, shop_b, _inactive, _foreign = await _seed_fixture(db_session)
    workspace_id = workspace.client_id

    async def _fake_fetch(**kwargs):
        if kwargs["shop_domain"] == shop_b.shop_domain:
            return None
        return _definition(kwargs["definition_id"])

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.create_shopify_metafield_preferences.fetch_shopify_metafield_definition_by_id",
        _fake_fetch,
    )
    with pytest.raises(NotFound):
        await _run(
            db_session,
            workspace_id=workspace_id,
            user_id=user.client_id,
            category_id=category.client_id,
            selections=[
                _selection(shop_a.client_id, _gid("valid"), 0),
                _selection(shop_b.client_id, _gid("missing"), 1),
            ],
        )
    rows = (
        await db_session.execute(
            select(ShopifyMetafieldPreference).where(
                ShopifyMetafieldPreference.workspace_id == workspace_id
            )
        )
    ).scalars().all()
    assert rows == []


@pytest.mark.integration
async def test_foreign_and_inactive_integrations_are_rejected_before_shopify_calls(db_session, monkeypatch) -> None:
    workspace, _other, user, category, _shop_a, _shop_b, inactive, foreign = await _seed_fixture(db_session)
    workspace_id = workspace.client_id
    user_id = user.client_id
    category_id = category.client_id
    inactive_id = inactive.client_id
    foreign_id = foreign.client_id
    calls: list[dict] = []

    async def _fake_fetch(**kwargs):
        calls.append(kwargs)
        return _definition(kwargs["definition_id"])

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.create_shopify_metafield_preferences.fetch_shopify_metafield_definition_by_id",
        _fake_fetch,
    )
    with pytest.raises(NotFound):
        await _run(
            db_session,
            workspace_id=workspace_id,
                user_id=user_id,
                category_id=category_id,
                selections=[_selection(foreign_id, _gid("foreign"), 0)],
        )
    with pytest.raises(ValidationError):
        await _run(
            db_session,
            workspace_id=workspace_id,
                user_id=user_id,
                category_id=category_id,
                selections=[_selection(inactive_id, _gid("inactive"), 0)],
        )
    assert calls == []


@pytest.mark.integration
async def test_repeated_create_is_idempotent_and_same_sequence_is_a_noop(db_session, monkeypatch) -> None:
    workspace, _other, user, category, shop_a, shop_b, _inactive, _foreign = await _seed_fixture(db_session)
    definition_a = _gid("idempotent-a")
    definition_b = _gid("idempotent-b")

    async def _fake_fetch(**kwargs):
        return _definition(kwargs["definition_id"])

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.create_shopify_metafield_preferences.fetch_shopify_metafield_definition_by_id",
        _fake_fetch,
    )
    selections = [
        _selection(shop_a.client_id, definition_a, 0),
        _selection(shop_b.client_id, definition_b, 1),
    ]
    await _run(db_session, workspace_id=workspace.client_id, user_id=user.client_id, category_id=category.client_id, selections=selections)
    await _run(db_session, workspace_id=workspace.client_id, user_id=user.client_id, category_id=category.client_id, selections=selections)
    rows = (
        await db_session.execute(
            select(ShopifyMetafieldPreference)
            .where(ShopifyMetafieldPreference.workspace_id == workspace.client_id)
            .order_by(ShopifyMetafieldPreference.shop_integration_id)
        )
    ).scalars().all()
    assert len(rows) == 2
    first_updated_at = {row.shop_integration_id: row.updated_at for row in rows}

    await _run(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        category_id=category.client_id,
        selections=[_selection(shop_a.client_id, definition_a, 5), _selection(shop_b.client_id, definition_b, 1)],
    )
    rows_after_change = (
        await db_session.execute(
            select(ShopifyMetafieldPreference).where(
                ShopifyMetafieldPreference.workspace_id == workspace.client_id
            )
        )
    ).scalars().all()
    by_shop = {row.shop_integration_id: row for row in rows_after_change}
    assert by_shop[shop_a.client_id].sequence_order == 5
    assert by_shop[shop_b.client_id].sequence_order == 1

    changed_shop_b_timestamp = by_shop[shop_b.client_id].updated_at
    await _run(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        category_id=category.client_id,
        selections=[_selection(shop_a.client_id, definition_a, 5), _selection(shop_b.client_id, definition_b, 1)],
    )
    rows_after_noop = (
        await db_session.execute(
            select(ShopifyMetafieldPreference).where(
                ShopifyMetafieldPreference.workspace_id == workspace.client_id
            )
        )
    ).scalars().all()
    by_shop_after_noop = {row.shop_integration_id: row for row in rows_after_noop}
    assert by_shop_after_noop[shop_b.client_id].updated_at == changed_shop_b_timestamp
    assert by_shop_after_noop[shop_a.client_id].updated_at != first_updated_at[shop_a.client_id]
