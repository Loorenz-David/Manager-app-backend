from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.shopify.shopify_metafield_preference import ShopifyMetafieldPreference
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.shopify.create_shopify_metafield_preferences import (
    create_shopify_metafield_preferences,
)
from beyo_manager.services.commands.shopify.delete_shopify_metafield_preferences import (
    delete_shopify_metafield_preferences,
)
from beyo_manager.services.context import ServiceContext


async def _seed_fixture(db_session):
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_del_{suffix}", name=f"Delete workspace {suffix}")
    other_workspace = Workspace(client_id=f"ws_del_other_{suffix}", name=f"Other {suffix}")
    user = User(
        client_id=f"usr_del_{suffix}",
        username=f"delete-user-{suffix}",
        email=f"delete-user-{suffix}@example.com",
        password="hashed",
    )
    other_user = User(
        client_id=f"usr_del_other_{suffix}",
        username=f"delete-other-{suffix}",
        email=f"delete-other-{suffix}@example.com",
        password="hashed",
    )
    await db_session.merge(workspace)
    await db_session.merge(other_workspace)
    db_session.add_all([user, other_user])
    await db_session.flush()

    now = datetime.now(timezone.utc)
    category = ItemCategory(
        client_id=f"itc_del_{suffix}",
        workspace_id=workspace.client_id,
        name=f"Delete category {suffix}",
        major_category=ItemMajorCategoryEnum.SEAT,
        created_by_id=user.client_id,
    )
    other_category = ItemCategory(
        client_id=f"itc_del_other_{suffix}",
        workspace_id=other_workspace.client_id,
        name=f"Other category {suffix}",
        major_category=ItemMajorCategoryEnum.SEAT,
        created_by_id=other_user.client_id,
    )
    shop = ShopifyShopIntegration(
        client_id=f"shpint_del_{suffix}",
        workspace_id=workspace.client_id,
        shop_domain=f"delete-{suffix}.myshopify.com",
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        api_version="2026-01",
        access_token_encrypted="delete-token",
        created_at=now,
        updated_at=now,
    )
    other_shop = ShopifyShopIntegration(
        client_id=f"shpint_del_other_{suffix}",
        workspace_id=other_workspace.client_id,
        shop_domain=f"delete-other-{suffix}.myshopify.com",
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        api_version="2026-01",
        access_token_encrypted="other-token",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([category, other_category, shop, other_shop])
    await db_session.flush()

    def _preference(shop_id: str, category_id: str, definition: str, owner: str) -> ShopifyMetafieldPreference:
        return ShopifyMetafieldPreference(
            client_id=f"shpmfp_del_{uuid4().hex[:10]}",
            workspace_id=workspace.client_id if owner == user.client_id else other_workspace.client_id,
            item_category_id=category_id,
            shop_integration_id=shop_id,
            shopify_metafield_definition_id=f"gid://shopify/MetafieldDefinition/{definition}",
            sequence_order=0,
            created_by_id=owner,
        )

    preferences = [
        _preference(shop.client_id, category.client_id, "one", user.client_id),
        _preference(shop.client_id, category.client_id, "two", user.client_id),
        _preference(shop.client_id, category.client_id, "three", user.client_id),
    ]
    other_preference = _preference(
        other_shop.client_id, other_category.client_id, "foreign", other_user.client_id
    )
    db_session.add_all([*preferences, other_preference])
    await db_session.commit()
    return workspace, other_workspace, user, category, shop, preferences, other_preference


def _ctx(db_session, *, workspace_id: str, user_id: str, client_ids: list[str]) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": user_id, "role_name": "seller"},
        incoming_data={"client_ids": client_ids},
        session=db_session,
    )


@pytest.mark.integration
async def test_delete_batch_soft_deletes_only_requested_rows(db_session) -> None:
    workspace, _other, user, _category, _shop, preferences, _foreign = await _seed_fixture(db_session)
    requested = [preferences[0].client_id, preferences[1].client_id]

    result = await delete_shopify_metafield_preferences(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, client_ids=requested)
    )

    assert result == {}
    rows = (
        await db_session.execute(
            select(ShopifyMetafieldPreference).where(
                ShopifyMetafieldPreference.workspace_id == workspace.client_id
            )
        )
    ).scalars().all()
    by_id = {row.client_id: row for row in rows}
    for client_id in requested:
        assert by_id[client_id].is_deleted is True
        assert by_id[client_id].deleted_at is not None
        assert by_id[client_id].deleted_by_id == user.client_id
    assert by_id[preferences[2].client_id].is_deleted is False


@pytest.mark.integration
async def test_delete_is_all_or_nothing_for_invalid_id(db_session) -> None:
    workspace, _other, user, _category, _shop, preferences, _foreign = await _seed_fixture(db_session)
    workspace_id = workspace.client_id
    user_id = user.client_id
    valid_id = preferences[0].client_id
    with pytest.raises(NotFound):
        await delete_shopify_metafield_preferences(
            _ctx(
                db_session,
                workspace_id=workspace_id,
                user_id=user_id,
                client_ids=[valid_id, "shpmfp_missing"],
            )
        )

    row = await db_session.get(ShopifyMetafieldPreference, valid_id)
    assert row is not None and row.is_deleted is False


@pytest.mark.integration
async def test_delete_is_workspace_scoped_and_rejects_already_deleted_rows(db_session) -> None:
    workspace, other_workspace, user, _category, _shop, preferences, foreign = await _seed_fixture(db_session)
    workspace_id = workspace.client_id
    other_workspace_id = other_workspace.client_id
    user_id = user.client_id
    first_id = preferences[0].client_id
    foreign_id = foreign.client_id
    with pytest.raises(NotFound):
        await delete_shopify_metafield_preferences(
            _ctx(
                db_session,
                workspace_id=workspace_id,
                user_id=user_id,
                client_ids=[foreign_id],
            )
        )
    await delete_shopify_metafield_preferences(
        _ctx(db_session, workspace_id=workspace_id, user_id=user_id, client_ids=[first_id])
    )
    with pytest.raises(NotFound):
        await delete_shopify_metafield_preferences(
            _ctx(db_session, workspace_id=workspace_id, user_id=user_id, client_ids=[first_id])
        )
    foreign_row = await db_session.get(ShopifyMetafieldPreference, foreign_id)
    assert foreign_row is not None and foreign_row.workspace_id == other_workspace_id and foreign_row.is_deleted is False


@pytest.mark.integration
async def test_delete_then_create_restores_same_row(db_session, monkeypatch) -> None:
    workspace, _other, user, category, shop, preferences, _foreign = await _seed_fixture(db_session)
    preference = preferences[0]
    await delete_shopify_metafield_preferences(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, client_ids=[preference.client_id])
    )

    async def _fake_fetch(**kwargs):
        return {
            "id": kwargs["definition_id"],
            "ownerType": "PRODUCT",
            "name": "Restored",
            "namespace": "custom",
            "key": "restored",
            "description": None,
            "type": {"name": "single_line_text_field"},
            "validations": [],
        }

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.create_shopify_metafield_preferences.fetch_shopify_metafield_definition_by_id",
        _fake_fetch,
    )
    result = await create_shopify_metafield_preferences(
        ServiceContext(
            identity={"workspace_id": workspace.client_id, "user_id": user.client_id, "role_name": "seller"},
            incoming_data={
                "item_category_id": category.client_id,
                "preferences": [{
                    "shop_integration_id": shop.client_id,
                    "shopify_metafield_definition_id": preference.shopify_metafield_definition_id,
                    "sequence_order": 4,
                }],
            },
            session=db_session,
        )
    )

    assert len(result) == 1
    restored = await db_session.get(ShopifyMetafieldPreference, preference.client_id)
    assert restored is not None and restored.is_deleted is False
    count = (
        await db_session.execute(
            select(ShopifyMetafieldPreference).where(
                ShopifyMetafieldPreference.workspace_id == workspace.client_id,
                ShopifyMetafieldPreference.shop_integration_id == shop.client_id,
                ShopifyMetafieldPreference.item_category_id == category.client_id,
                ShopifyMetafieldPreference.shopify_metafield_definition_id == preference.shopify_metafield_definition_id,
            )
        )
    ).scalars().all()
    assert len(count) == 1
