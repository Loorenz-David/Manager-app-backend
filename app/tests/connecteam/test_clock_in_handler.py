from __future__ import annotations

from datetime import datetime, timezone

import pytest

from beyo_manager.domain.connecteam.enums import ConnecteamProcessingOutcomeEnum
from beyo_manager.errors.validation import ConflictError
from beyo_manager.services.tasks.connecteam.handlers import handle_clock_in as module


pytestmark = pytest.mark.asyncio


async def test_clock_in_calls_intent_aware_primitive_with_event_timestamp(
    connecteam_worker, connecteam_event, monkeypatch
) -> None:
    calls = []
    logs = []

    async def fake_clock_in(session, workspace_id, user_id, occurred_at, *, changed_by_id):
        calls.append((session, workspace_id, user_id, occurred_at, changed_by_id))

    monkeypatch.setattr(module, "clock_in_shift_for_user", fake_clock_in)
    monkeypatch.setattr(module, "log_event", lambda event_type, **extra: logs.append((event_type, extra)))

    result = await module.execute(
        session="session",
        worker=connecteam_worker,
        event=connecteam_event,
    )

    assert result.outcome == ConnecteamProcessingOutcomeEnum.CLOCK_IN_APPLIED.value
    assert calls == [
        (
            "session",
            "ws_test",
            "usr_worker",
            datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc),
            "usr_worker",
        )
    ]
    assert logs[-1][0] == "connecteam_clock_in_applied"
    assert logs[-1][1]["occurred_at"] == "2026-07-20T08:00:00+00:00"


async def test_duplicate_clock_in_is_terminal_noop(connecteam_worker, connecteam_event, monkeypatch) -> None:
    logs = []

    async def duplicate_clock_in(*args, **kwargs):
        raise ConflictError("Worker is already clocked in.")

    monkeypatch.setattr(module, "clock_in_shift_for_user", duplicate_clock_in)
    monkeypatch.setattr(module, "log_event", lambda event_type, **extra: logs.append((event_type, extra)))

    result = await module.execute(
        session=object(),
        worker=connecteam_worker,
        event=connecteam_event,
    )

    assert result.outcome == ConnecteamProcessingOutcomeEnum.ALREADY_CLOCKED_IN.value
    assert logs[-1] == (
        "connecteam_clock_event_noop",
        {
            "provider": "connecteam",
            "event_key": "connecteam:req-test",
            "request_id": "req-test",
            "connecteam_event_type": "clock_in",
            "activity_type": "shift",
            "connecteam_user_id": "connecteam-worker",
            "time_clock_id": "clock-test",
            "time_activity_id": "activity-test",
            "workspace_id": "ws_test",
            "internal_user_id": "usr_worker",
            "occurred_at": "2026-07-20T08:00:00+00:00",
            "noop_reason": "already_clocked_in",
            "processing_status": "already_clocked_in",
        },
    )


async def test_clock_in_uses_received_at_when_occurred_at_is_absent(
    connecteam_worker, event_for, monkeypatch
) -> None:
    captured = {}

    async def fake_clock_in(session, workspace_id, user_id, occurred_at, *, changed_by_id):
        captured["occurred_at"] = occurred_at

    monkeypatch.setattr(module, "clock_in_shift_for_user", fake_clock_in)
    monkeypatch.setattr(module, "log_event", lambda *args, **kwargs: None)

    event = event_for("clock_in", occurred_at=None)
    await module.execute(session=object(), worker=connecteam_worker, event=event)

    assert captured["occurred_at"] == datetime(2026, 7, 20, 8, 0, 2, tzinfo=timezone.utc)
