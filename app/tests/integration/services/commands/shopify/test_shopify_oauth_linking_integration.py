from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlparse
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventTypeEnum,
    ShopifyIntegrationStatusEnum,
    ShopifyOAuthStateStatusEnum,
)
from beyo_manager.models.tables.execution.execution_payload import ExecutionPayload
from beyo_manager.models.tables.execution.execution_task import ExecutionTask
from beyo_manager.models.tables.shopify.shopify_integration_event import ShopifyIntegrationEvent
from beyo_manager.models.tables.shopify.shopify_oauth_state import ShopifyOAuthState
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.shopify._callback_errors import ShopifyOAuthCallbackError
from beyo_manager.services.commands.shopify.create_shopify_install_url import create_shopify_install_url
from beyo_manager.services.commands.shopify.enqueue_shopify_webhook_sync_after_install import (
    enqueue_shopify_webhook_sync_after_install,
)
from beyo_manager.services.commands.shopify.handle_shopify_oauth_callback import handle_shopify_oauth_callback
from beyo_manager.services.commands.shopify.link_or_update_shopify_shop import link_or_update_shopify_shop
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.crypto.field_encryption import decrypt_field
from beyo_manager.services.infra.shopify.oauth_client import ShopifyOAuthTokenExchangeResult


def _ctx(db_session, *, workspace_id: str, user_id: str, incoming_data: dict) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "manager",
            "username": "tester",
        },
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


def _suffix() -> str:
    return uuid4().hex[:8]


def _configure_shopify_settings(monkeypatch) -> None:
    monkeypatch.setattr("beyo_manager.config.settings.shopify_client_id", "client-id")
    monkeypatch.setattr("beyo_manager.config.settings.shopify_client_secret", "client-secret")
    monkeypatch.setattr("beyo_manager.config.settings.shopify_app_scopes", "read_orders,write_products")
    monkeypatch.setattr("beyo_manager.config.settings.shopify_redirect_uri", "https://backend.example.com/api/v1/integrations/shopify/oauth/callback")
    monkeypatch.setattr("beyo_manager.config.settings.shopify_oauth_redirect_url", "https://frontend.example.com/shopify/result")
    monkeypatch.setattr("beyo_manager.config.settings.shopify_api_version", "2026-01")
    monkeypatch.setattr(
        "beyo_manager.config.settings.field_encryption_key",
        "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
    )


def _build_signed_callback_query(secret: str, params: dict[str, str]) -> tuple[str, dict[str, str]]:
    message = "&".join(f"{key}={value}" for key, value in sorted(params.items()))
    digest = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    raw_query = urlencode([*params.items(), ("hmac", digest)])
    query_data = dict(parse_qsl(raw_query, keep_blank_values=True))
    query_data["raw_query_string"] = raw_query
    return raw_query, query_data


def _parse_redirect_query(redirect_url: str) -> dict[str, str]:
    return dict(parse_qsl(urlparse(redirect_url).query, keep_blank_values=True))


async def _fetch_shopify_execution_tasks(db_session, shop_integration_id: str) -> list[tuple[ExecutionTask, ExecutionPayload]]:
    rows = (
        await db_session.execute(
            select(ExecutionTask, ExecutionPayload)
            .join(ExecutionPayload, ExecutionPayload.execution_task_id == ExecutionTask.client_id)
            .where(
                ExecutionTask.task_type == TaskType.SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP,
                ExecutionPayload.payload["shop_integration_id"].as_string() == shop_integration_id,
            )
            .order_by(ExecutionTask.created_at.asc())
        )
    ).all()
    return list(rows)


@pytest.mark.integration
async def test_create_shopify_install_url_creates_state_and_normalizes_shop_domain(db_session, monkeypatch) -> None:
    _configure_shopify_settings(monkeypatch)
    workspace, _, user = await _seed_workspace_and_user(db_session)

    result = await create_shopify_install_url(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"shop_domain": "Valid-Shop", "redirect_after_success": "default"},
        )
    )

    state_row = (
        await db_session.execute(select(ShopifyOAuthState).where(ShopifyOAuthState.shop_domain == "valid-shop.myshopify.com"))
    ).scalar_one()

    assert result["shop_domain"] == "valid-shop.myshopify.com"
    assert "state=" in result["install_url"]
    assert state_row.workspace_id == workspace.client_id
    assert state_row.user_id == user.client_id
    assert state_row.status == ShopifyOAuthStateStatusEnum.PENDING
    assert state_row.redirect_after_success == "default"
    assert tuple(state_row.requested_scopes or ()) == ("read_orders", "write_products")


@pytest.mark.integration
async def test_create_shopify_install_url_rejects_invalid_shop_domain(db_session, monkeypatch) -> None:
    _configure_shopify_settings(monkeypatch)
    workspace, _, user = await _seed_workspace_and_user(db_session)

    with pytest.raises(Exception, match="shop_domain"):
        await create_shopify_install_url(
            _ctx(
                db_session,
                workspace_id=workspace.client_id,
                user_id=user.client_id,
                incoming_data={"shop_domain": "not a valid shop"},
            )
        )

    count = await db_session.scalar(select(ShopifyOAuthState).where(ShopifyOAuthState.workspace_id == workspace.client_id))
    assert count is None


@pytest.mark.integration
async def test_handle_shopify_oauth_callback_links_shop_encrypts_token_records_events_and_redirects_safely(
    db_session,
    monkeypatch,
    caplog,
) -> None:
    _configure_shopify_settings(monkeypatch)
    workspace, _, user = await _seed_workspace_and_user(db_session)
    suffix = _suffix()
    shop_domain = f"linked-shop-{suffix}.myshopify.com"
    state_value = f"state-success-{suffix}"
    oauth_state = ShopifyOAuthState(
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=shop_domain,
        state=state_value,
        status=ShopifyOAuthStateStatusEnum.PENDING,
        requested_scopes=["read_orders", "write_products"],
        redirect_after_success="default",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db_session.add(oauth_state)
    await db_session.commit()

    async def _fake_exchange(*, shop_domain: str, code: str) -> ShopifyOAuthTokenExchangeResult:
        assert shop_domain == oauth_state.shop_domain
        assert code == "oauth-code"
        return ShopifyOAuthTokenExchangeResult(
            access_token="offline-access-token",
            granted_scopes=("read_orders", "write_products"),
        )

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.handle_shopify_oauth_callback.exchange_oauth_code_for_offline_token",
        _fake_exchange,
    )

    async def _fake_fetch_shop_name(*, shop_domain: str, access_token_encrypted: str) -> str:
        assert shop_domain == oauth_state.shop_domain
        return "Linked Test Shop"

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.handle_shopify_oauth_callback.fetch_shopify_shop_name",
        _fake_fetch_shop_name,
    )

    _, incoming_data = _build_signed_callback_query(
        "client-secret",
        {
            "code": "oauth-code",
            "shop": shop_domain,
            "state": state_value,
            "timestamp": "123",
        },
    )

    with caplog.at_level(logging.INFO):
        result = await handle_shopify_oauth_callback(
            ServiceContext(identity={}, incoming_data=incoming_data, session=db_session)
        )

    integration = (
        await db_session.execute(select(ShopifyShopIntegration).where(ShopifyShopIntegration.shop_domain == shop_domain))
    ).scalar_one()
    events = (
        await db_session.execute(
            select(ShopifyIntegrationEvent)
            .where(ShopifyIntegrationEvent.shop_integration_id == integration.client_id)
            .order_by(ShopifyIntegrationEvent.created_at.asc())
        )
    ).scalars().all()
    refreshed_state = await db_session.get(ShopifyOAuthState, oauth_state.client_id)
    redirect_query = _parse_redirect_query(result["redirect_url"])

    assert decrypt_field(integration.access_token_encrypted or "") == "offline-access-token"
    assert integration.access_token_encrypted != "offline-access-token"
    assert integration.shop_name == "Linked Test Shop"
    assert integration.status == ShopifyIntegrationStatusEnum.ACTIVE
    assert integration.requested_scopes == ["read_orders", "write_products"]
    assert integration.granted_scopes == ["read_orders", "write_products"]
    assert [event.event_type for event in events] == [
        ShopifyIntegrationEventTypeEnum.INSTALL,
        ShopifyIntegrationEventTypeEnum.WEBHOOK_SYNC,
    ]
    task_rows = await _fetch_shopify_execution_tasks(db_session, integration.client_id)
    assert len(task_rows) == 1
    assert task_rows[0][0].task_type == TaskType.SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP
    assert task_rows[0][1].payload == {"shop_integration_id": integration.client_id}
    assert refreshed_state.status == ShopifyOAuthStateStatusEnum.CONSUMED
    assert refreshed_state.consumed_at is not None
    assert redirect_query == {
        "success": "true",
        "shop_domain": shop_domain,
    }
    assert "oauth-code" not in caplog.text
    assert "offline-access-token" not in caplog.text
    assert "client-secret" not in caplog.text
    assert "hmac" not in caplog.text.lower()
    assert state_value not in result["redirect_url"]


@pytest.mark.integration
async def test_enqueue_shopify_webhook_sync_after_install_creates_event_and_task(
    db_session,
    monkeypatch,
) -> None:
    _configure_shopify_settings(monkeypatch)
    workspace, _, user = await _seed_workspace_and_user(db_session)
    shop_domain = f"boundary-shop-{_suffix()}.myshopify.com"
    integration = ShopifyShopIntegration(
        workspace_id=workspace.client_id,
        shop_domain=shop_domain,
        provider="shopify",
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        access_token_encrypted="encrypted-token",
        granted_scopes=["read_orders"],
        requested_scopes=["read_orders"],
        api_version="2026-01",
        installed_at=datetime.now(timezone.utc) - timedelta(days=1),
        last_connected_at=datetime.now(timezone.utc) - timedelta(days=1),
        created_by_id=user.client_id,
        updated_by_id=user.client_id,
    )
    db_session.add(integration)
    await db_session.commit()

    result = await enqueue_shopify_webhook_sync_after_install(
        ServiceContext(
            identity={},
            incoming_data={
                "workspace_id": workspace.client_id,
                "user_id": user.client_id,
                "shop_integration_id": integration.client_id,
                "shop_domain": shop_domain,
            },
            session=db_session,
        )
    )

    task_rows = await _fetch_shopify_execution_tasks(db_session, integration.client_id)
    events = (
        await db_session.execute(
            select(ShopifyIntegrationEvent).where(
                ShopifyIntegrationEvent.shop_integration_id == integration.client_id,
                ShopifyIntegrationEvent.event_type == ShopifyIntegrationEventTypeEnum.WEBHOOK_SYNC,
            )
        )
    ).scalars().all()

    assert result == {
        "shop_integration_id": integration.client_id,
        "sync_status": "pending",
    }
    assert len(events) == 1
    assert len(task_rows) == 1
    assert task_rows[0][1].payload == {"shop_integration_id": integration.client_id}


@pytest.mark.integration
async def test_handle_shopify_oauth_callback_rejects_expired_state(db_session, monkeypatch) -> None:
    _configure_shopify_settings(monkeypatch)
    workspace, _, user = await _seed_workspace_and_user(db_session)
    suffix = _suffix()
    shop_domain = f"expired-shop-{suffix}.myshopify.com"
    state_value = f"state-expired-{suffix}"
    db_session.add(
        ShopifyOAuthState(
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            shop_domain=shop_domain,
            state=state_value,
            status=ShopifyOAuthStateStatusEnum.PENDING,
            requested_scopes=["read_orders"],
            redirect_after_success="default",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
    )
    await db_session.commit()
    _, incoming_data = _build_signed_callback_query(
        "client-secret",
        {
            "code": "oauth-code",
            "shop": shop_domain,
            "state": state_value,
        },
    )

    with pytest.raises(ShopifyOAuthCallbackError) as exc_info:
        await handle_shopify_oauth_callback(ServiceContext(identity={}, incoming_data=incoming_data, session=db_session))

    assert exc_info.value.error_code == "state_expired"


@pytest.mark.integration
async def test_handle_shopify_oauth_callback_rejects_replay_after_success(db_session, monkeypatch) -> None:
    _configure_shopify_settings(monkeypatch)
    workspace, _, user = await _seed_workspace_and_user(db_session)
    suffix = _suffix()
    shop_domain = f"replay-shop-{suffix}.myshopify.com"
    state_value = f"state-replay-{suffix}"
    db_session.add(
        ShopifyOAuthState(
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            shop_domain=shop_domain,
            state=state_value,
            status=ShopifyOAuthStateStatusEnum.PENDING,
            requested_scopes=["read_orders"],
            redirect_after_success="default",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
    )
    await db_session.commit()

    async def _fake_exchange(*, shop_domain: str, code: str) -> ShopifyOAuthTokenExchangeResult:
        return ShopifyOAuthTokenExchangeResult(access_token="token-replay", granted_scopes=("read_orders",))

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.handle_shopify_oauth_callback.exchange_oauth_code_for_offline_token",
        _fake_exchange,
    )

    async def _fake_fetch_shop_name(*, shop_domain: str, access_token_encrypted: str) -> str | None:
        return None

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.handle_shopify_oauth_callback.fetch_shopify_shop_name",
        _fake_fetch_shop_name,
    )

    _, incoming_data = _build_signed_callback_query(
        "client-secret",
        {
            "code": "oauth-code",
            "shop": shop_domain,
            "state": state_value,
        },
    )

    await handle_shopify_oauth_callback(ServiceContext(identity={}, incoming_data=incoming_data, session=db_session))

    with pytest.raises(ShopifyOAuthCallbackError) as exc_info:
        await handle_shopify_oauth_callback(ServiceContext(identity={}, incoming_data=incoming_data, session=db_session))

    assert exc_info.value.error_code == "state_already_consumed"


@pytest.mark.integration
async def test_handle_shopify_oauth_callback_rejects_invalid_hmac(db_session, monkeypatch) -> None:
    _configure_shopify_settings(monkeypatch)
    workspace, _, user = await _seed_workspace_and_user(db_session)
    suffix = _suffix()
    shop_domain = f"invalid-hmac-{suffix}.myshopify.com"
    state_value = f"state-invalid-hmac-{suffix}"
    db_session.add(
        ShopifyOAuthState(
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            shop_domain=shop_domain,
            state=state_value,
            status=ShopifyOAuthStateStatusEnum.PENDING,
            requested_scopes=["read_orders"],
            redirect_after_success="default",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
    )
    await db_session.commit()

    incoming_data = {
        "code": "oauth-code",
        "shop": shop_domain,
        "state": state_value,
        "hmac": "bad-signature",
        "raw_query_string": f"code=oauth-code&shop={shop_domain}&state={state_value}&hmac=bad-signature",
    }

    with pytest.raises(ShopifyOAuthCallbackError) as exc_info:
        await handle_shopify_oauth_callback(ServiceContext(identity={}, incoming_data=incoming_data, session=db_session))

    assert exc_info.value.error_code == "invalid_signature"


@pytest.mark.integration
async def test_handle_shopify_oauth_callback_updates_existing_same_workspace_integration_on_relink(
    db_session,
    monkeypatch,
) -> None:
    _configure_shopify_settings(monkeypatch)
    workspace, _, user = await _seed_workspace_and_user(db_session)
    suffix = _suffix()
    shop_domain = f"relink-shop-{suffix}.myshopify.com"
    state_value = f"state-relink-{suffix}"
    existing = ShopifyShopIntegration(
        workspace_id=workspace.client_id,
        shop_domain=shop_domain,
        provider="shopify",
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        access_token_encrypted="old-token",
        granted_scopes=["read_orders"],
        requested_scopes=["read_orders"],
        api_version="2025-10",
        installed_at=datetime.now(timezone.utc) - timedelta(days=1),
        last_connected_at=datetime.now(timezone.utc) - timedelta(days=1),
        created_by_id=user.client_id,
        updated_by_id=user.client_id,
    )
    oauth_state = ShopifyOAuthState(
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=shop_domain,
        state=state_value,
        status=ShopifyOAuthStateStatusEnum.PENDING,
        requested_scopes=["read_orders", "write_products"],
        redirect_after_success="default",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db_session.add_all([existing, oauth_state])
    await db_session.commit()

    async def _fake_exchange(*, shop_domain: str, code: str) -> ShopifyOAuthTokenExchangeResult:
        return ShopifyOAuthTokenExchangeResult(
            access_token="new-offline-token",
            granted_scopes=("read_orders",),
        )

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.handle_shopify_oauth_callback.exchange_oauth_code_for_offline_token",
        _fake_exchange,
    )

    async def _fake_fetch_shop_name(*, shop_domain: str, access_token_encrypted: str) -> str:
        return "Relinked Test Shop"

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.handle_shopify_oauth_callback.fetch_shopify_shop_name",
        _fake_fetch_shop_name,
    )

    _, incoming_data = _build_signed_callback_query(
        "client-secret",
        {
            "code": "oauth-code",
            "shop": shop_domain,
            "state": state_value,
        },
    )

    await handle_shopify_oauth_callback(ServiceContext(identity={}, incoming_data=incoming_data, session=db_session))

    refreshed = await db_session.get(ShopifyShopIntegration, existing.client_id)
    assert refreshed is not None
    assert refreshed.client_id == existing.client_id
    assert decrypt_field(refreshed.access_token_encrypted or "") == "new-offline-token"
    assert refreshed.shop_name == "Relinked Test Shop"
    assert refreshed.status == ShopifyIntegrationStatusEnum.SCOPES_OUTDATED

    reauth_event = (
        await db_session.execute(
            select(ShopifyIntegrationEvent).where(
                ShopifyIntegrationEvent.shop_integration_id == existing.client_id,
                ShopifyIntegrationEvent.event_type == ShopifyIntegrationEventTypeEnum.REAUTHORIZE,
            )
        )
    ).scalar_one()
    assert reauth_event.message == "Shopify shop reauthorized successfully."


@pytest.mark.integration
async def test_link_or_update_shopify_shop_rejects_active_shop_in_other_workspace(db_session, monkeypatch) -> None:
    _configure_shopify_settings(monkeypatch)
    workspace, other_workspace, user = await _seed_workspace_and_user(db_session)
    suffix = _suffix()
    shop_domain = f"global-conflict-{suffix}.myshopify.com"
    db_session.add(
        ShopifyShopIntegration(
            workspace_id=other_workspace.client_id,
            shop_domain=shop_domain,
            provider="shopify",
            status=ShopifyIntegrationStatusEnum.ACTIVE,
            access_token_encrypted="encrypted",
            granted_scopes=["read_orders"],
            requested_scopes=["read_orders"],
            api_version="2026-01",
            installed_at=datetime.now(timezone.utc),
            last_connected_at=datetime.now(timezone.utc),
            created_by_id=user.client_id,
        )
    )
    await db_session.commit()

    with pytest.raises(Exception, match="already linked"):
        await link_or_update_shopify_shop(
            ServiceContext(
                identity={},
                incoming_data={
                    "workspace_id": workspace.client_id,
                    "user_id": user.client_id,
                    "shop_domain": shop_domain,
                    "access_token": "offline-token",
                    "requested_scopes": ["read_orders"],
                    "granted_scopes": ["read_orders"],
                    "api_version": "2026-01",
                },
                session=db_session,
            )
        )
