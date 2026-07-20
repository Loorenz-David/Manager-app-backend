from __future__ import annotations

import pytest

from beyo_manager.domain.connecteam.enums import ConnecteamEventTypeEnum
from beyo_manager.services.queries.users.resolve_connecteam_worker import ResolvedConnecteamWorker
from beyo_manager.services.tasks.connecteam import handle_connecteam_process_time_activity as module
from beyo_manager.services.tasks.connecteam.handlers.handle_clock_in import ConnecteamHandlerResult


pytestmark = pytest.mark.asyncio


class _Session:
    def __init__(self):
        self.begin_calls = 0
        self.write_calls = 0
        self.in_transaction = False

    def begin(self):
        self.begin_calls += 1
        return self

    async def __aenter__(self):
        self.in_transaction = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.in_transaction = False
        return False

    def add(self, *args, **kwargs):
        self.write_calls += 1


async def _session_source(session):
    yield session


def _raw(event_type: str, activity_type: str = "shift", user_id: str | None = "worker") -> dict:
    return {
        "event_key": "connecteam:test",
        "provider": "connecteam",
        "event_type": event_type,
        "activity_type": activity_type,
        "request_id": "request",
        "company_id": "company",
        "connecteam_user_id": user_id,
        "time_clock_id": "clock",
        "time_activity_id": "activity",
        "occurred_at": "2026-07-20T08:00:00Z",
        "received_at": "2026-07-20T08:00:01Z",
        "payload": {},
    }


async def test_manual_break_never_reaches_resolution_or_writes(monkeypatch) -> None:
    session = _Session()
    monkeypatch.setattr(module, "get_db_session", lambda: _session_source(session))
    monkeypatch.setattr(module, "log_event", lambda *args, **kwargs: None)

    await module.handle_connecteam_process_time_activity(
        _raw("clock_in", activity_type="manual_break"), "task_manual_break"
    )

    assert session.begin_calls == 0
    assert session.write_calls == 0


async def test_unmapped_worker_has_no_action_writes(monkeypatch) -> None:
    session = _Session()

    async def no_worker(*args, **kwargs):
        return None

    monkeypatch.setattr(module, "get_db_session", lambda: _session_source(session))
    monkeypatch.setattr(module, "resolve_connecteam_worker", no_worker)
    monkeypatch.setattr(module, "log_event", lambda *args, **kwargs: None)

    await module.handle_connecteam_process_time_activity(_raw("clock_in"), "task_unmapped")

    assert session.begin_calls == 1
    assert session.write_calls == 0


async def test_resolution_and_clock_action_share_one_transaction(monkeypatch) -> None:
    session = _Session()
    resolved = ResolvedConnecteamWorker(
        work_profile_id="profile",
        user_id="user",
        workspace_id="workspace",
    )
    transaction_flags = []

    async def resolve(*args, **kwargs):
        transaction_flags.append(session.in_transaction)
        return resolved

    async def handler(*, session, worker, event):
        del worker, event
        transaction_flags.append(session.in_transaction)
        return ConnecteamHandlerResult(outcome="clock_in_applied")

    monkeypatch.setattr(module, "get_db_session", lambda: _session_source(session))
    monkeypatch.setattr(module, "resolve_connecteam_worker", resolve)
    monkeypatch.setitem(module.HANDLER_MAP, ConnecteamEventTypeEnum.CLOCK_IN, handler)
    monkeypatch.setattr(module, "log_event", lambda *args, **kwargs: None)

    await module.handle_connecteam_process_time_activity(_raw("clock_in"), "task_mapped")

    assert session.begin_calls == 1
    assert transaction_flags == [True, True]
