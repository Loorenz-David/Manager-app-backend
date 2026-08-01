"""`dispatch` must deliver from every process, not only from the API.

The bug this guards against was silent by construction: a worker's handler list was empty,
so `dispatch` looped over nothing and returned successfully. No exception, no log, no failing
test — `notification:new` was discarded from the first commit until 2026-08.

Three properties hold the fix together, and each is tested here:

1. importing the events package — anything at all from it — registers the handlers,
2. `realtime_push` publishes through Redis when the process holds no websockets,
3. an empty handler list is loud.
"""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import AsyncMock

import pytest

from beyo_manager.services.infra.events import bootstrap, event_bus, realtime_push
from beyo_manager.services.infra.events.domain_event import (
    BatchWorkspaceEvent,
    ConversationRoomEvent,
    UserEvent,
    WorkspaceEvent,
)


pytestmark = pytest.mark.unit


# --- 1. registration happens on import, in any process -----------------------------------


@pytest.mark.parametrize(
    "import_line",
    [
        # The obvious one.
        "from beyo_manager.services.infra.events import dispatch",
        # The one that matters: a submodule-only import still runs the package __init__, so a
        # module that never imports `dispatch` by name cannot end up without handlers either.
        "from beyo_manager.services.infra.events.build_event import build_user_event",
        # What a worker entry point actually pulls in.
        "from beyo_manager.services.tasks.notifications.create_notifications import handle_create_notifications",
    ],
)
def test_importing_the_events_package_registers_handlers_in_a_fresh_process(import_line):
    """Runs in a subprocess on purpose.

    Import-time behaviour cannot be tested in-process — this interpreter imported the package
    long before the test ran. A fresh interpreter is the only honest check, and a fresh
    interpreter is exactly what a systemd worker unit is.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            f"{import_line}\n"
            "from beyo_manager.services.infra.events import event_bus\n"
            "print(len(event_bus._handlers))",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "3", result.stderr


def test_registering_twice_does_not_duplicate_handlers():
    """`create_app` still calls it explicitly at startup; it must be a no-op by then."""
    before = list(event_bus._handlers)
    bootstrap.register_default_handlers()
    assert event_bus._handlers == before


# --- 2. the transport follows the process ------------------------------------------------


@pytest.fixture
def as_worker(monkeypatch):
    """A process holding no websocket connections — every worker unit."""
    monkeypatch.setattr(realtime_push, "owns_socket_server", lambda: False)


@pytest.fixture
def as_api(monkeypatch):
    monkeypatch.setattr(realtime_push, "owns_socket_server", lambda: True)


async def test_worker_publishes_a_user_event_through_redis(as_worker, monkeypatch):
    emit = AsyncMock()
    monkeypatch.setattr(realtime_push, "emit_to_user_room", emit)

    await realtime_push.push_to_user("usr_1", "notification:new", {"client_id": "ntf_1"})

    emit.assert_awaited_once_with(
        user_id="usr_1", event="notification:new", payload={"client_id": "ntf_1"}
    )


async def test_api_process_delivers_a_user_event_locally(as_api, monkeypatch):
    """No Redis round trip for clients this process already holds."""
    send = AsyncMock()
    monkeypatch.setattr(realtime_push.manager, "send_to_user", send)
    emit = AsyncMock()
    monkeypatch.setattr(realtime_push, "emit_to_user_room", emit)

    await realtime_push.push_to_user("usr_1", "notification:new", {"client_id": "ntf_1"})

    send.assert_awaited_once_with("usr_1", "notification:new", {"client_id": "ntf_1"})
    emit.assert_not_awaited()


async def test_worker_publishes_workspace_batch_items_as_a_list(as_worker, monkeypatch):
    emit = AsyncMock()
    monkeypatch.setattr(realtime_push, "emit_to_workspace_room", emit)
    items = [{"client_id": "tst_1", "new_state": "paused"}]

    await realtime_push.push_workspace_event_items("ws_1", "task:step-state-changed", items)

    emit.assert_awaited_once_with(
        workspace_id="ws_1", event="task:step-state-changed", payload=items
    )


async def test_worker_publishes_workspace_batch_ids_in_the_same_envelope_as_the_api(
    as_worker, monkeypatch
):
    """`push_workspace_batch` wraps ids as `{"ids": [...]}`. The wrapping must not depend on
    which process ran it, or clients would parse two shapes for one event name."""
    emit = AsyncMock()
    monkeypatch.setattr(realtime_push, "emit_to_workspace_room", emit)

    await realtime_push.push_workspace_batch("ws_1", "item:updated", ["itm_1", "itm_2"])

    emit.assert_awaited_once_with(
        workspace_id="ws_1", event="item:updated", payload={"ids": ["itm_1", "itm_2"]}
    )


async def test_worker_publishes_to_a_conversation_room(as_worker, monkeypatch):
    emit = AsyncMock()
    monkeypatch.setattr(realtime_push, "emit_to_conversation_room", emit)

    await realtime_push.push_to_conversation("cnv_1", "conversation:message-created", {"a": 1})

    emit.assert_awaited_once_with(
        conversation_client_id="cnv_1", event="conversation:message-created", payload={"a": 1}
    )


# --- the whole chain, which is what actually regressed ------------------------------------


@pytest.mark.parametrize(
    "event, transport, expected",
    [
        (
            UserEvent(event_name="notification:new", client_id="ntf_1", user_id="usr_1"),
            "emit_to_user_room",
            {"user_id": "usr_1", "event": "notification:new", "payload": {"client_id": "ntf_1"}},
        ),
        (
            WorkspaceEvent(event_name="task:state-changed", client_id="tsk_1", workspace_id="ws_1"),
            "emit_to_workspace_room",
            {
                "workspace_id": "ws_1",
                "event": "task:state-changed",
                "payload": {"client_id": "tsk_1"},
            },
        ),
        (
            BatchWorkspaceEvent(
                event_name="task:step-state-changed",
                workspace_id="ws_1",
                items=[{"client_id": "tst_1"}],
            ),
            "emit_to_workspace_room",
            {
                "workspace_id": "ws_1",
                "event": "task:step-state-changed",
                "payload": [{"client_id": "tst_1"}],
            },
        ),
        (
            ConversationRoomEvent(
                event_name="conversation:message-created",
                client_id="msg_1",
                conversation_id="cnv_1",
                workspace_id="ws_1",
            ),
            "emit_to_conversation_room",
            {
                "conversation_client_id": "cnv_1",
                "event": "conversation:message-created",
                "payload": {"client_id": "msg_1"},
            },
        ),
    ],
    ids=["user", "workspace", "batch", "conversation"],
)
async def test_dispatch_from_a_worker_reaches_the_socket_transport(
    as_worker, monkeypatch, event, transport, expected
):
    """Bus → handler → transport, in a process with no websockets. This is the exact path
    that returned successfully while delivering nothing."""
    emit = AsyncMock()
    monkeypatch.setattr(realtime_push, transport, emit)

    await event_bus.dispatch([event])

    emit.assert_awaited_once_with(**expected)


# --- 3. an empty handler list is loud ----------------------------------------------------


async def test_dispatch_warns_instead_of_dropping_events_in_silence(monkeypatch, caplog):
    monkeypatch.setattr(event_bus, "_handlers", [])
    event = WorkspaceEvent(event_name="task:state-changed", client_id="tsk_1", workspace_id="ws_1")

    with caplog.at_level("WARNING"):
        await event_bus.dispatch([event])

    assert "no handlers registered" in caplog.text
    assert "task:state-changed" in caplog.text


async def test_dispatching_nothing_is_not_a_warning(monkeypatch, caplog):
    monkeypatch.setattr(event_bus, "_handlers", [])

    with caplog.at_level("WARNING"):
        await event_bus.dispatch([])

    assert caplog.text == ""
