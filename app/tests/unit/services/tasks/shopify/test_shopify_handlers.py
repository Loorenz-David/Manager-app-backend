from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.tasks.shopify import handle_shopify_remove_webhooks_for_shop as remove_module
from beyo_manager.services.tasks.shopify import handle_shopify_sync_webhooks_for_shop as sync_module


async def _fake_session_generator(session) -> AsyncIterator[object]:
    yield session


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_shopify_sync_webhooks_for_shop_delegates_with_service_context(monkeypatch) -> None:
    calls: dict[str, object] = {}
    session = SimpleNamespace()

    async def _fake_sync(ctx) -> None:
        calls["identity"] = ctx.identity
        calls["incoming_data"] = ctx.incoming_data
        calls["session"] = ctx.session

    monkeypatch.setattr(sync_module, "get_db_session", lambda: _fake_session_generator(session))
    monkeypatch.setattr(sync_module, "sync_shopify_webhook_subscriptions_for_shop", _fake_sync)

    await sync_module.handle_shopify_sync_webhooks_for_shop(
        {"shop_integration_id": "shpint_sync"},
        "task_sync",
    )

    assert calls == {
        "identity": {},
        "incoming_data": {"shop_integration_id": "shpint_sync"},
        "session": session,
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_shopify_sync_webhooks_for_shop_propagates_command_error(monkeypatch) -> None:
    session = SimpleNamespace()

    async def _fake_sync(_ctx) -> None:
        raise ValidationError("retry me")

    monkeypatch.setattr(sync_module, "get_db_session", lambda: _fake_session_generator(session))
    monkeypatch.setattr(sync_module, "sync_shopify_webhook_subscriptions_for_shop", _fake_sync)

    with pytest.raises(ValidationError, match="retry me"):
        await sync_module.handle_shopify_sync_webhooks_for_shop(
            {"shop_integration_id": "shpint_sync"},
            "task_sync",
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_shopify_remove_webhooks_for_shop_delegates_with_service_context(monkeypatch) -> None:
    calls: dict[str, object] = {}
    session = SimpleNamespace()

    async def _fake_remove(ctx) -> None:
        calls["identity"] = ctx.identity
        calls["incoming_data"] = ctx.incoming_data
        calls["session"] = ctx.session

    monkeypatch.setattr(remove_module, "get_db_session", lambda: _fake_session_generator(session))
    monkeypatch.setattr(remove_module, "remove_shopify_webhooks_for_shop", _fake_remove)

    await remove_module.handle_shopify_remove_webhooks_for_shop(
        {"shop_integration_id": "shpint_remove"},
        "task_remove",
    )

    assert calls == {
        "identity": {},
        "incoming_data": {"shop_integration_id": "shpint_remove"},
        "session": session,
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_shopify_remove_webhooks_for_shop_propagates_command_error(monkeypatch) -> None:
    session = SimpleNamespace()

    async def _fake_remove(_ctx) -> None:
        raise ValidationError("remove failed")

    monkeypatch.setattr(remove_module, "get_db_session", lambda: _fake_session_generator(session))
    monkeypatch.setattr(remove_module, "remove_shopify_webhooks_for_shop", _fake_remove)

    with pytest.raises(ValidationError, match="remove failed"):
        await remove_module.handle_shopify_remove_webhooks_for_shop(
            {"shop_integration_id": "shpint_remove"},
            "task_remove",
        )
