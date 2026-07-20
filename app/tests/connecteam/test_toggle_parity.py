from __future__ import annotations

import pytest

from beyo_manager.services.tasks.connecteam.handlers import handle_clock_in
from beyo_manager.services.tasks.connecteam.handlers import handle_clock_out


pytestmark = pytest.mark.asyncio


async def test_webhook_clock_actions_delegate_to_the_toggle_endpoint_primitives(
    connecteam_worker, event_for, monkeypatch
) -> None:
    clock_in_calls = []
    clock_out_calls = []

    async def fake_clock_in(*args, **kwargs):
        clock_in_calls.append((args, kwargs))

    async def fake_clock_out(*args, **kwargs):
        clock_out_calls.append((args, kwargs))
        return 2

    monkeypatch.setattr(handle_clock_in, "clock_in_shift_for_user", fake_clock_in)
    monkeypatch.setattr(handle_clock_out, "clock_out_shift_for_user", fake_clock_out)
    monkeypatch.setattr(handle_clock_in, "log_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(handle_clock_out, "log_event", lambda *args, **kwargs: None)

    await handle_clock_in.execute(
        session="session",
        worker=connecteam_worker,
        event=event_for("clock_in"),
    )
    await handle_clock_out.execute(
        session="session",
        worker=connecteam_worker,
        event=event_for("clock_out"),
    )

    assert clock_in_calls[0][0][1:3] == ("ws_test", "usr_worker")
    assert clock_in_calls[0][1]["changed_by_id"] == "usr_worker"
    assert clock_out_calls[0][0][1:3] == ("ws_test", "usr_worker")
    assert clock_out_calls[0][1]["changed_by_id"] == "usr_worker"
