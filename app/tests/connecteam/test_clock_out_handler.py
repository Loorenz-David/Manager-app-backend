from __future__ import annotations

import pytest

from beyo_manager.domain.connecteam.enums import ConnecteamProcessingOutcomeEnum
from beyo_manager.errors.validation import ConflictError
from beyo_manager.services.tasks.connecteam.handlers import handle_clock_out as module


pytestmark = pytest.mark.asyncio


async def test_clock_out_applied_logs_transitioned_step_count(
    connecteam_worker, event_for, monkeypatch
) -> None:
    logs = []

    async def fake_clock_out(*args, **kwargs):
        return 3

    monkeypatch.setattr(module, "clock_out_shift_for_user", fake_clock_out)
    monkeypatch.setattr(module, "log_event", lambda event_type, **extra: logs.append((event_type, extra)))

    result = await module.execute(
        session=object(),
        worker=connecteam_worker,
        event=event_for("clock_out"),
    )

    assert result.outcome == ConnecteamProcessingOutcomeEnum.CLOCK_OUT_APPLIED.value
    assert result.transitioned_steps == 3
    assert logs[-1][0] == "connecteam_clock_out_applied"
    assert logs[-1][1]["transitioned_steps"] == 3
    assert logs[-1][1]["auto_clock_out"] is False


async def test_clock_out_without_open_shift_is_terminal_noop(
    connecteam_worker, event_for, monkeypatch
) -> None:
    logs = []

    async def no_open_shift(*args, **kwargs):
        raise ConflictError("Worker is not clocked in.")

    monkeypatch.setattr(module, "clock_out_shift_for_user", no_open_shift)
    monkeypatch.setattr(module, "log_event", lambda event_type, **extra: logs.append((event_type, extra)))

    result = await module.execute(
        session=object(),
        worker=connecteam_worker,
        event=event_for("clock_out"),
    )

    assert result.outcome == ConnecteamProcessingOutcomeEnum.NO_OPEN_SHIFT.value
    assert logs[-1][1]["noop_reason"] == "no_open_shift"
    assert logs[-1][1]["auto_clock_out"] is False
