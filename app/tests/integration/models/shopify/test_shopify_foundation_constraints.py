from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationStatusEnum,
    ShopifyProductSyncItemStatusEnum,
    ShopifyWebhookPayloadFormatEnum,
    ShopifyWebhookSubscriptionStatusEnum,
)
from beyo_manager.models.tables.shopify.shopify_oauth_state import ShopifyOAuthState
from beyo_manager.models.tables.shopify.shopify_product_sync_item import ShopifyProductSyncItem
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.shopify.shopify_webhook_intake import ShopifyWebhookIntake
from beyo_manager.models.tables.shopify.shopify_webhook_subscription import ShopifyWebhookSubscription
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace


async def _seed_workspace_and_user(db_session):
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    other_workspace = Workspace(client_id=f"ws_{suffix}_other", name=f"Other {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user-{suffix}",
        email=f"user-{suffix}@example.com",
        password="hashed",
    )
    db_session.add_all([workspace, other_workspace, user])
    await db_session.flush()
    return workspace, other_workspace, user, suffix


def _shop_integration(
    *,
    suffix: str,
    workspace_id: str,
    shop_domain: str,
    status: ShopifyIntegrationStatusEnum,
    is_deleted: bool = False,
) -> ShopifyShopIntegration:
    return ShopifyShopIntegration(
        client_id=f"shpint_{suffix}_{status.value}",
        workspace_id=workspace_id,
        shop_domain=shop_domain,
        provider="shopify",
        status=status,
        api_version="2026-01",
        is_deleted=is_deleted,
    )


@pytest.mark.integration
async def test_active_like_shop_domain_is_globally_unique(db_session) -> None:
    workspace, other_workspace, _, suffix = await _seed_workspace_and_user(db_session)
    db_session.add_all(
        [
            _shop_integration(
                suffix=f"{suffix}_one",
                workspace_id=workspace.client_id,
                shop_domain="global-dup.myshopify.com",
                status=ShopifyIntegrationStatusEnum.ACTIVE,
            ),
            _shop_integration(
                suffix=f"{suffix}_two",
                workspace_id=other_workspace.client_id,
                shop_domain="global-dup.myshopify.com",
                status=ShopifyIntegrationStatusEnum.NEEDS_REAUTH,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.integration
async def test_error_status_still_blocks_new_active_link(db_session) -> None:
    workspace, other_workspace, _, suffix = await _seed_workspace_and_user(db_session)
    db_session.add_all(
        [
            _shop_integration(
                suffix=f"{suffix}_error",
                workspace_id=workspace.client_id,
                shop_domain="blocked-error.myshopify.com",
                status=ShopifyIntegrationStatusEnum.ERROR,
            ),
            _shop_integration(
                suffix=f"{suffix}_active",
                workspace_id=other_workspace.client_id,
                shop_domain="blocked-error.myshopify.com",
                status=ShopifyIntegrationStatusEnum.ACTIVE,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.integration
async def test_inactive_or_deleted_rows_do_not_block_new_active_link(db_session) -> None:
    workspace, other_workspace, _, suffix = await _seed_workspace_and_user(db_session)
    disabled_domain = f"inactive-ok-{suffix}.myshopify.com"
    deleted_domain = f"inactive-deleted-{suffix}.myshopify.com"
    db_session.add_all(
        [
            _shop_integration(
                suffix=f"{suffix}_disabled",
                workspace_id=workspace.client_id,
                shop_domain=disabled_domain,
                status=ShopifyIntegrationStatusEnum.DISABLED,
            ),
            _shop_integration(
                suffix=f"{suffix}_deleted",
                workspace_id=workspace.client_id,
                shop_domain=deleted_domain,
                status=ShopifyIntegrationStatusEnum.ACTIVE,
                is_deleted=True,
            ),
        ]
    )
    await db_session.commit()

    db_session.add_all(
        [
            _shop_integration(
                suffix=f"{suffix}_new_one",
                workspace_id=other_workspace.client_id,
                shop_domain=disabled_domain,
                status=ShopifyIntegrationStatusEnum.ACTIVE,
            ),
            _shop_integration(
                suffix=f"{suffix}_new_two",
                workspace_id=other_workspace.client_id,
                shop_domain=deleted_domain,
                status=ShopifyIntegrationStatusEnum.ACTIVE,
            ),
        ]
    )
    await db_session.commit()


@pytest.mark.integration
async def test_duplicate_oauth_state_is_rejected(db_session) -> None:
    workspace, _, user, suffix = await _seed_workspace_and_user(db_session)
    db_session.add_all(
        [
            ShopifyOAuthState(
                client_id=f"shpoau_{suffix}_one",
                workspace_id=workspace.client_id,
                user_id=user.client_id,
                shop_domain="oauth.myshopify.com",
                state="state-dup",
                expires_at=datetime(2026, 7, 8, tzinfo=timezone.utc),
            ),
            ShopifyOAuthState(
                client_id=f"shpoau_{suffix}_two",
                workspace_id=workspace.client_id,
                user_id=user.client_id,
                shop_domain="oauth.myshopify.com",
                state="state-dup",
                expires_at=datetime(2026, 7, 8, 0, 1, tzinfo=timezone.utc),
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.integration
async def test_duplicate_subscription_topic_is_rejected(db_session) -> None:
    workspace, _, _, suffix = await _seed_workspace_and_user(db_session)
    integration = _shop_integration(
        suffix=f"{suffix}_base",
        workspace_id=workspace.client_id,
        shop_domain="subs.myshopify.com",
        status=ShopifyIntegrationStatusEnum.ACTIVE,
    )
    db_session.add(integration)
    await db_session.flush()
    db_session.add_all(
        [
            ShopifyWebhookSubscription(
                client_id=f"shpwhs_{suffix}_one",
                workspace_id=workspace.client_id,
                shop_integration_id=integration.client_id,
                topic="orders/create",
                callback_url="https://example.com/webhooks/shopify",
                payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
                status=ShopifyWebhookSubscriptionStatusEnum.ACTIVE,
            ),
            ShopifyWebhookSubscription(
                client_id=f"shpwhs_{suffix}_two",
                workspace_id=workspace.client_id,
                shop_integration_id=integration.client_id,
                topic="orders/create",
                callback_url="https://example.com/webhooks/shopify",
                payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
                status=ShopifyWebhookSubscriptionStatusEnum.PENDING,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.integration
async def test_duplicate_webhook_dedupe_key_is_rejected(db_session) -> None:
    workspace, _, _, suffix = await _seed_workspace_and_user(db_session)
    integration = _shop_integration(
        suffix=f"{suffix}_base",
        workspace_id=workspace.client_id,
        shop_domain="intake.myshopify.com",
        status=ShopifyIntegrationStatusEnum.ACTIVE,
    )
    db_session.add(integration)
    await db_session.flush()
    db_session.add_all(
        [
            ShopifyWebhookIntake(
                client_id=f"shpwhi_{suffix}_one",
                workspace_id=workspace.client_id,
                shop_integration_id=integration.client_id,
                shop_domain=integration.shop_domain,
                topic="orders/create",
                dedupe_key="dedupe-1",
            ),
            ShopifyWebhookIntake(
                client_id=f"shpwhi_{suffix}_two",
                workspace_id=workspace.client_id,
                shop_integration_id=integration.client_id,
                shop_domain=integration.shop_domain,
                topic="orders/create",
                dedupe_key="dedupe-1",
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.integration
async def test_shopify_product_sync_item_enforces_foreign_keys_and_default_status(db_session) -> None:
    workspace, _, user, suffix = await _seed_workspace_and_user(db_session)
    integration = _shop_integration(
        suffix=f"{suffix}_sync",
        workspace_id=workspace.client_id,
        shop_domain=f"sync-{suffix}.myshopify.com",
        status=ShopifyIntegrationStatusEnum.ACTIVE,
    )
    db_session.add(integration)
    await db_session.flush()

    sync_item = ShopifyProductSyncItem(
        client_id=f"shpsi_{suffix}",
        workspace_id=workspace.client_id,
        shop_integration_id=integration.client_id,
        frontend_client_id="frontend_1",
        normalized_payload_json={"product": {"title": "Chair"}, "variant": {"barcode": "BAR-1"}, "metafields": []},
        created_by_id=user.client_id,
    )
    db_session.add(sync_item)
    await db_session.commit()

    assert sync_item.status == ShopifyProductSyncItemStatusEnum.PENDING

    db_session.add(
        ShopifyProductSyncItem(
            client_id=f"shpsi_{suffix}_bad",
            workspace_id=workspace.client_id,
            shop_integration_id="missing_shop",
            frontend_client_id="frontend_2",
            normalized_payload_json={"product": {"title": "Table"}, "variant": {"barcode": "BAR-2"}, "metafields": []},
            created_by_id=user.client_id,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()
