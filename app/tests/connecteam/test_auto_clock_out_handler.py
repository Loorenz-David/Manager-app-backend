from __future__ import annotations

import pytest

from beyo_manager.domain.connecteam.enums import ConnecteamProcessingOutcomeEnum
from beyo_manager.services.tasks.connecteam.handlers import handle_auto_clock_out as module
from beyo_manager.services.tasks.connecteam.handlers import handle_clock_out


pytestmark = pytest.mark.asyncio


async def test_auto_clock_out_uses_same_close_primitive_and_marks_log(
    connecteam_worker, event_for, monkeypatch
) -> None:
    calls = []
    logs = []

    async def fake_clock_out(*args, **kwargs):
        calls.append((args, kwargs))
        return 1

    monkeypatch.setattr(handle_clock_out, "clock_out_shift_for_user", fake_clock_out)
    monkeypatch.setattr(handle_clock_out, "log_event", lambda event_type, **extra: logs.append((event_type, extra)))

    result = await module.execute(
        session="session",
        worker=connecteam_worker,
        event=event_for("auto_clock_out"),
    )

    assert result.outcome == ConnecteamProcessingOutcomeEnum.CLOCK_OUT_APPLIED.value
    assert result.transitioned_steps == 1
    assert calls[0][1]["changed_by_id"] == "usr_worker"
    assert logs[-1][0] == "connecteam_clock_out_applied"
    assert logs[-1][1]["auto_clock_out"] is True
