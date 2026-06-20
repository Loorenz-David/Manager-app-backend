import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from beyo_manager.services.infra.audit import audited_events as _audited_events_module
from beyo_manager.services.infra.events.domain_event import (
    BatchWorkspaceEvent,
    UserEvent,
    WorkspaceEvent,
)


async def _call_handle(event):
    from beyo_manager.services.infra.events.handlers.audit_handler import handle
    await handle(event)


@pytest.mark.unit
async def test_skip_non_audited_event():
    event = WorkspaceEvent(
        event_name="non:audited",
        client_id="res_1",
        workspace_id="ws_1",
    )
    with patch.object(
        _audited_events_module, "get_audited_events", return_value=frozenset()
    ):
        with patch(f"beyo_manager.services.infra.events.handlers.audit_handler.get_audited_events",
                   return_value=frozenset()):
            # Should return without writing — no DB call
            await _call_handle(event)  # must not raise


@pytest.mark.unit
async def test_skip_batch_workspace_event():
    event = BatchWorkspaceEvent(
        event_name="task:step-created",
        workspace_id="ws_1",
        items=[{"client_id": "tsp_1"}],
    )
    with patch(
        f"beyo_manager.services.infra.events.handlers.audit_handler.get_audited_events",
        return_value=frozenset({"task:step-created"}),
    ) as audited_events_mock:
        await _call_handle(event)

    audited_events_mock.assert_not_called()


@pytest.mark.unit
async def test_skip_missing_workspace_id(caplog):
    event = UserEvent(
        event_name="auth:signed-in",
        client_id="usr_1",
        user_id="usr_1",
    )
    with patch(
        f"beyo_manager.services.infra.events.handlers.audit_handler.get_audited_events",
        return_value=frozenset({"auth:signed-in"}),
    ):
        with caplog.at_level(logging.WARNING):
            await _call_handle(event)
    assert "skipped" in caplog.text


@pytest.mark.unit
async def test_write_on_valid_audited_event():
    event = WorkspaceEvent(
        event_name="auth:signed-in",
        client_id="usr_1",
        workspace_id="ws_1",
    )
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        f"beyo_manager.services.infra.events.handlers.audit_handler.get_audited_events",
        return_value=frozenset({"auth:signed-in"}),
    ):
        with patch(f"beyo_manager.models.database.get_db_session") as mock_db:
            async def _gen():
                yield mock_session
            mock_db.return_value = _gen()

            write_mock = AsyncMock()
            with patch(
                f"beyo_manager.services.infra.audit.write_audit.write_audit_from_event",
                write_mock,
            ):
                await _call_handle(event)

    write_mock.assert_awaited_once()
    _, kwargs = write_mock.call_args
    assert kwargs["event_name"] == "auth:signed-in"
    assert kwargs["workspace_id"] == "ws_1"
