from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.shopify.shopify_metafield_preference import (
    ShopifyMetafieldPreference,
)
from beyo_manager.models.tables.shopify.shopify_shop_integration import (
    ShopifyShopIntegration,
)
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.shopify.update_shopify_metafield_preference_sequence_order import (
    update_shopify_metafield_preference_sequence_order,
)
from beyo_manager.services.context import ServiceContext


def _preference(
    *,
    client_id: str,
    workspace_id: str,
    category_id: str,
    shop_id: str,
    sequence_order: int,
    user_id: str,
    is_deleted: bool = False,
) -> ShopifyMetafieldPreference:
    return ShopifyMetafieldPreference(
        client_id=client_id,
        workspace_id=workspace_id,
        item_category_id=category_id,
        shop_integration_id=shop_id,
        shopify_metafield_definition_id=(
            f"gid://shopify/MetafieldDefinition/{client_id}"
        ),
        sequence_order=sequence_order,
        created_by_id=user_id,
        is_deleted=is_deleted,
        deleted_at=datetime.now(timezone.utc) if is_deleted else None,
        deleted_by_id=user_id if is_deleted else None,
    )


async def _seed_fixture(db_session):
    suffix = uuid4().hex[:8]
    workspace = Workspace(
        client_id=f"ws_seq_{suffix}", name=f"Sequence workspace {suffix}"
    )
    other_workspace = Workspace(
        client_id=f"ws_seq_other_{suffix}",
        name=f"Other sequence workspace {suffix}",
    )
    user = User(
        client_id=f"usr_seq_{suffix}",
        username=f"sequence-user-{suffix}",
        email=f"sequence-user-{suffix}@example.com",
        password="hashed",
    )
    other_user = User(
        client_id=f"usr_seq_other_{suffix}",
        username=f"sequence-other-{suffix}",
        email=f"sequence-other-{suffix}@example.com",
        password="hashed",
    )
    db_session.add_all([workspace, other_workspace, user, other_user])
    await db_session.flush()

    now = datetime.now(timezone.utc)
    category = ItemCategory(
        client_id=f"itc_seq_{suffix}",
        workspace_id=workspace.client_id,
        name=f"Sequence category {suffix}",
        major_category=ItemMajorCategoryEnum.SEAT,
        created_by_id=user.client_id,
    )
    second_category = ItemCategory(
        client_id=f"itc_seq_second_{suffix}",
        workspace_id=workspace.client_id,
        name=f"Second sequence category {suffix}",
        major_category=ItemMajorCategoryEnum.SEAT,
        created_by_id=user.client_id,
    )
    other_category = ItemCategory(
        client_id=f"itc_seq_other_{suffix}",
        workspace_id=other_workspace.client_id,
        name=f"Other sequence category {suffix}",
        major_category=ItemMajorCategoryEnum.SEAT,
        created_by_id=other_user.client_id,
    )

    def _shop(client_id: str, workspace_id: str, domain: str):
        return ShopifyShopIntegration(
            client_id=client_id,
            workspace_id=workspace_id,
            shop_domain=domain,
            status=ShopifyIntegrationStatusEnum.ACTIVE,
            api_version="2026-01",
            access_token_encrypted=f"token-{client_id}",
            created_at=now,
            updated_at=now,
        )

    shop = _shop(
        f"shpint_seq_{suffix}",
        workspace.client_id,
        f"sequence-{suffix}.myshopify.com",
    )
    second_shop = _shop(
        f"shpint_seq_second_{suffix}",
        workspace.client_id,
        f"sequence-second-{suffix}.myshopify.com",
    )
    other_shop = _shop(
        f"shpint_seq_other_{suffix}",
        other_workspace.client_id,
        f"sequence-other-{suffix}.myshopify.com",
    )
    db_session.add_all(
        [category, second_category, other_category, shop, second_shop, other_shop]
    )
    await db_session.flush()

    siblings = [
        _preference(
            client_id=f"shpmfp_seq_{position}_{suffix}",
            workspace_id=workspace.client_id,
            category_id=category.client_id,
            shop_id=shop.client_id,
            sequence_order=position,
            user_id=user.client_id,
        )
        for position in range(5)
    ]
    target = siblings[2]
    other_shop_preference = _preference(
        client_id=f"shpmfp_seq_second_shop_{suffix}",
        workspace_id=workspace.client_id,
        category_id=category.client_id,
        shop_id=second_shop.client_id,
        sequence_order=3,
        user_id=user.client_id,
    )
    other_category_preference = _preference(
        client_id=f"shpmfp_seq_second_category_{suffix}",
        workspace_id=workspace.client_id,
        category_id=second_category.client_id,
        shop_id=shop.client_id,
        sequence_order=3,
        user_id=user.client_id,
    )
    foreign_preference = _preference(
        client_id=f"shpmfp_seq_other_{suffix}",
        workspace_id=other_workspace.client_id,
        category_id=other_category.client_id,
        shop_id=other_shop.client_id,
        sequence_order=2,
        user_id=other_user.client_id,
    )
    deleted_preference = _preference(
        client_id=f"shpmfp_seq_deleted_{suffix}",
        workspace_id=workspace.client_id,
        category_id=category.client_id,
        shop_id=shop.client_id,
        sequence_order=3,
        user_id=user.client_id,
        is_deleted=True,
    )
    db_session.add_all(
        [
            *siblings,
            other_shop_preference,
            other_category_preference,
            foreign_preference,
            deleted_preference,
        ]
    )
    await db_session.commit()
    return {
        "workspace": workspace,
        "user": user,
        "target": target,
        "siblings": siblings,
        "other_shop_preference": other_shop_preference,
        "other_category_preference": other_category_preference,
        "foreign_preference": foreign_preference,
        "deleted_preference": deleted_preference,
    }


def _ctx(
    db_session,
    *,
    workspace_id: str,
    user_id: str,
    client_id: str,
    sequence_order: int,
) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "seller",
        },
        incoming_data={
            "client_id": client_id,
            "sequence_order": sequence_order,
        },
        session=db_session,
    )


async def _move_target(db_session, fixture: dict, sequence_order: int) -> dict:
    return await update_shopify_metafield_preference_sequence_order(
        _ctx(
            db_session,
            workspace_id=fixture["workspace"].client_id,
            user_id=fixture["user"].client_id,
            client_id=fixture["target"].client_id,
            sequence_order=sequence_order,
        )
    )


async def _refresh_all(db_session, rows: list[ShopifyMetafieldPreference]) -> None:
    for row in rows:
        await db_session.refresh(row)


@pytest.mark.integration
async def test_move_down_decrements_only_siblings_inside_window(db_session) -> None:
    fixture = await _seed_fixture(db_session)

    result = await _move_target(db_session, fixture, 4)

    assert result == {"client_id": fixture["target"].client_id, "sequence_order": 4}
    await _refresh_all(db_session, fixture["siblings"])
    assert [row.sequence_order for row in fixture["siblings"]] == [0, 1, 4, 2, 3]
    assert fixture["target"].updated_by_id == fixture["user"].client_id
    assert all(
        fixture["siblings"][index].updated_by_id == fixture["user"].client_id
        for index in (2, 3, 4)
    )


@pytest.mark.integration
async def test_move_up_increments_only_siblings_inside_window(db_session) -> None:
    fixture = await _seed_fixture(db_session)

    await _move_target(db_session, fixture, 0)

    await _refresh_all(db_session, fixture["siblings"])
    assert [row.sequence_order for row in fixture["siblings"]] == [1, 2, 0, 3, 4]
    assert fixture["siblings"][3].updated_by_id is None
    assert fixture["siblings"][4].updated_by_id is None


@pytest.mark.integration
async def test_reorder_does_not_touch_other_shop_category_or_deleted_rows(
    db_session,
) -> None:
    fixture = await _seed_fixture(db_session)
    unaffected = [
        fixture["other_shop_preference"],
        fixture["other_category_preference"],
        fixture["deleted_preference"],
    ]

    await _move_target(db_session, fixture, 4)

    await _refresh_all(db_session, unaffected)
    assert [row.sequence_order for row in unaffected] == [3, 3, 3]
    assert all(row.updated_by_id is None for row in unaffected[:2])


@pytest.mark.integration
@pytest.mark.parametrize(
    "target", ["foreign_preference", "deleted_preference", "missing"]
)
async def test_reorder_is_workspace_scoped_and_excludes_deleted_targets(
    db_session,
    target: str,
) -> None:
    fixture = await _seed_fixture(db_session)
    target_id = "shpmfp_missing" if target == "missing" else fixture[target].client_id

    with pytest.raises(NotFound, match="Shopify metafield preference not found"):
        await update_shopify_metafield_preference_sequence_order(
            _ctx(
                db_session,
                workspace_id=fixture["workspace"].client_id,
                user_id=fixture["user"].client_id,
                client_id=target_id,
                sequence_order=8,
            )
        )
