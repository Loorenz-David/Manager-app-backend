from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.shopify.shopify_metafield_preference import ShopifyMetafieldPreference
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace


async def _seed_base(db_session, *, two_shops: bool = True):
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
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
    shops = [
        ShopifyShopIntegration(
            client_id=f"shpint_{suffix}_a",
            workspace_id=workspace.client_id,
            shop_domain=f"metafield-a-{suffix}.myshopify.com",
            status=ShopifyIntegrationStatusEnum.ACTIVE,
            api_version="2026-01",
            access_token_encrypted="encrypted-a",
        )
    ]
    if two_shops:
        shops.append(
            ShopifyShopIntegration(
                client_id=f"shpint_{suffix}_b",
                workspace_id=workspace.client_id,
                shop_domain=f"metafield-b-{suffix}.myshopify.com",
                status=ShopifyIntegrationStatusEnum.ACTIVE,
                api_version="2026-01",
                access_token_encrypted="encrypted-b",
            )
        )
    db_session.add_all([workspace, user])
    await db_session.flush()
    db_session.add_all([category, *shops])
    await db_session.commit()
    return workspace, user, category, shops, suffix


def _preference(
    *,
    suffix: str,
    workspace_id: str,
    shop_integration_id: str,
    item_category_id: str,
    definition_id: str,
    is_deleted: bool = False,
) -> ShopifyMetafieldPreference:
    return ShopifyMetafieldPreference(
        client_id=f"shpmfp_{suffix}_{uuid4().hex[:6]}",
        workspace_id=workspace_id,
        shop_integration_id=shop_integration_id,
        item_category_id=item_category_id,
        shopify_metafield_definition_id=definition_id,
        sequence_order=0,
        is_deleted=is_deleted,
        deleted_at=datetime.now(timezone.utc) if is_deleted else None,
    )


@pytest.mark.integration
async def test_active_preference_unique_scope_is_enforced(db_session) -> None:
    workspace, _user, category, shops, suffix = await _seed_base(db_session)
    definition_id = "gid://shopify/MetafieldDefinition/shared"
    db_session.add_all(
        [
            _preference(
                suffix=suffix,
                workspace_id=workspace.client_id,
                shop_integration_id=shops[0].client_id,
                item_category_id=category.client_id,
                definition_id=definition_id,
            ),
            _preference(
                suffix=suffix,
                workspace_id=workspace.client_id,
                shop_integration_id=shops[0].client_id,
                item_category_id=category.client_id,
                definition_id=definition_id,
            ),
        ]
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.integration
async def test_same_definition_id_is_independent_per_shop(db_session) -> None:
    workspace, _user, category, shops, suffix = await _seed_base(db_session)
    definition_id = "gid://shopify/MetafieldDefinition/shared"
    db_session.add_all(
        [
            _preference(
                suffix=suffix,
                workspace_id=workspace.client_id,
                shop_integration_id=shops[0].client_id,
                item_category_id=category.client_id,
                definition_id=definition_id,
            ),
            _preference(
                suffix=suffix,
                workspace_id=workspace.client_id,
                shop_integration_id=shops[1].client_id,
                item_category_id=category.client_id,
                definition_id=definition_id,
            ),
        ]
    )
    await db_session.commit()


@pytest.mark.integration
async def test_soft_deleted_preference_does_not_block_new_active_row(db_session) -> None:
    workspace, _user, category, shops, suffix = await _seed_base(db_session, two_shops=False)
    definition_id = "gid://shopify/MetafieldDefinition/restored"
    db_session.add(
        _preference(
            suffix=suffix,
            workspace_id=workspace.client_id,
            shop_integration_id=shops[0].client_id,
            item_category_id=category.client_id,
            definition_id=definition_id,
            is_deleted=True,
        )
    )
    await db_session.commit()
    db_session.add(
        _preference(
            suffix=suffix,
            workspace_id=workspace.client_id,
            shop_integration_id=shops[0].client_id,
            item_category_id=category.client_id,
            definition_id=definition_id,
        )
    )
    await db_session.commit()


@pytest.mark.integration
async def test_preference_foreign_keys_are_enforced(db_session) -> None:
    workspace, _user, category, shops, suffix = await _seed_base(db_session, two_shops=False)
    db_session.add(
        _preference(
            suffix=suffix,
            workspace_id=workspace.client_id,
            shop_integration_id=shops[0].client_id,
            item_category_id="missing_item_category",
            definition_id="gid://shopify/MetafieldDefinition/foreign-key",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
