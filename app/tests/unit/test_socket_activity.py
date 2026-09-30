"""Socket human activity: view_entity / leave_entity record; connect and disconnect do not."""

from __future__ import annotations

import jwt
import pytest

from beyo_manager.config import settings
from beyo_manager.sockets import handlers
from beyo_manager.sockets.connection_meta import ConnectionMeta
from beyo_manager.sockets.manager import ConnectionManager

pytestmark = pytest.mark.unit


@pytest.fixture
def records(monkeypatch):
    calls = []

    async def _record(**kwargs):
        calls.append(kwargs)
        return True

    monkeypatch.setattr(handlers, "record_human_activity", _record)
    return calls


@pytest.fixture
def side_effects(monkeypatch):
    """Stub presence and the view tasks; returns what the handlers did."""
    done = []

    async def _no_task(**kwargs):
        done.append(kwargs["task_type"])

    class _Session:
        async def commit(self):
            return None

    async def _session():
        yield _Session()

    monkeypatch.setattr(handlers, "mark_viewing", lambda *a: done.append("viewing"))
    monkeypatch.setattr(handlers, "mark_left", lambda *a: done.append("left"))
    monkeypatch.setattr(handlers, "create_instant_task", _no_task)
    monkeypatch.setattr(handlers, "get_db_session", _session)
    return done


@pytest.fixture
def connected(monkeypatch):
    meta = ConnectionMeta(user_id="usr_1", workspace_id="ws_1", username="u", app_scope="floor")
    monkeypatch.setattr(handlers.manager, "get", lambda sid: meta if sid == "sid-1" else None)
    return meta


_TASK = {"entity_type": "task", "entity_client_id": "tsk_1"}


async def test_view_entity_records_socket_activity_in_the_connection_scope(records, side_effects, connected):
    await handlers._handle_view_entity("sid-1", _TASK)

    assert records == [{"app_scope": "floor", "source": "socket", "user_id": "usr_1"}]
    assert "viewing" in side_effects


async def test_leave_entity_records_socket_activity(records, side_effects, connected):
    await handlers._handle_leave_entity("sid-1", _TASK)

    assert records == [{"app_scope": "floor", "source": "socket", "user_id": "usr_1"}]
    assert "left" in side_effects


async def test_unknown_connection_or_invalid_entity_does_not_record(records, side_effects, connected):
    await handlers._handle_view_entity("sid-unknown", _TASK)
    await handlers._handle_view_entity("sid-1", {"entity_type": "nope", "entity_client_id": "x"})
    await handlers._handle_leave_entity("sid-1", {"entity_type": "task", "entity_client_id": ""})

    assert records == []


async def test_recording_failure_does_not_break_the_handler(side_effects, connected, monkeypatch):
    async def _boom(**_kwargs):
        raise RuntimeError("recorder exploded")

    monkeypatch.setattr(handlers, "record_human_activity", _boom)

    await handlers._handle_view_entity("sid-1", _TASK)

    assert side_effects[0] == "viewing"  # presence and the view task still happened
    assert len(side_effects) == 2


async def test_connect_keeps_the_app_scope_and_does_not_record(records, monkeypatch):
    connected: list[ConnectionMeta] = []

    async def _connect(sid, meta):
        connected.append(meta)

    async def _not_blocklisted(_jti):
        return False

    async def _online(_user_id):
        return None

    monkeypatch.setattr(handlers, "is_token_blocklisted", _not_blocklisted)
    monkeypatch.setattr(handlers.manager, "connect", _connect)
    monkeypatch.setattr(handlers, "set_user_online", _online)
    token = jwt.encode(
        {"user_id": "usr_1", "workspace_id": "ws_1", "app_scope": "manager", "jti": "j"},
        settings.jwt_secret_key,
        algorithm="HS256",
    )

    assert await handlers._handle_connect("sid-1", {}, {"token": token}) is True

    [meta] = connected
    assert meta.app_scope == "manager"
    assert records == []


async def test_disconnect_does_not_record(records, side_effects, monkeypatch):
    meta = ConnectionMeta(user_id="usr_1", workspace_id="ws_1", username="u", app_scope="floor")

    async def _disconnect(_sid):
        return meta

    async def _offline(_user_id):
        return None

    monkeypatch.setattr(handlers.manager, "disconnect", _disconnect)
    monkeypatch.setattr(handlers.manager, "is_user_connected", lambda _u: False)
    monkeypatch.setattr(handlers, "delete_user_online", _offline)

    await handlers._handle_disconnect("sid-1")

    assert records == []


def test_connection_counts_are_sockets_and_distinct_users():
    manager = ConnectionManager()
    manager._connections = {
        "a": ConnectionMeta(user_id="usr_1", workspace_id="w", username="u"),
        "b": ConnectionMeta(user_id="usr_1", workspace_id="w", username="u"),
        "c": ConnectionMeta(user_id="usr_2", workspace_id="w", username="v"),
    }

    assert manager.connection_counts() == (3, 2)
    assert ConnectionManager().connection_counts() == (0, 0)
