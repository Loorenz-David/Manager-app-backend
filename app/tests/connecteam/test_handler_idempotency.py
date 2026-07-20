from __future__ import annotations

import pytest

from beyo_manager.domain.connecteam.enums import ConnecteamProcessingOutcomeEnum
from beyo_manager.errors.validation import ConflictError
from beyo_manager.services.tasks.connecteam.handlers import handle_clock_in as module


pytestmark = pytest.mark.asyncio


async def test_retry_after_commit_lands_on_conflict_noop(
    connecteam_worker, connecteam_event, monkeypatch
) -> None:
    calls = 0

    async def first_then_conflict(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ConflictError("Worker is already clocked in.")

    monkeypatch.setattr(module, "clock_in_shift_for_user", first_then_conflict)
    monkeypatch.setattr(module, "log_event", lambda *args, **kwargs: None)

    first = await module.execute(session=object(), worker=connecteam_worker, event=connecteam_event)
    second = await module.execute(session=object(), worker=connecteam_worker, event=connecteam_event)

    assert first.outcome == ConnecteamProcessingOutcomeEnum.CLOCK_IN_APPLIED.value
    assert second.outcome == ConnecteamProcessingOutcomeEnum.ALREADY_CLOCKED_IN.value


async def test_unexpected_handler_failure_propagates(
    connecteam_worker, connecteam_event, monkeypatch
) -> None:
    failure = RuntimeError("database unavailable")

    async def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(module, "clock_in_shift_for_user", fail)

    with pytest.raises(RuntimeError) as exc_info:
        await module.execute(session=object(), worker=connecteam_worker, event=connecteam_event)
    assert exc_info.value is failure
