from datetime import date
from types import SimpleNamespace

import pytest

from beyo_manager.services.tasks.analytics import process_step_transition as module


# NOTE: time booking (working/pause/ended-shift seconds) is no longer done via
# per-interval increments here — it is recomputed concurrency-averaged by
# reconcile_user_day_time / the sweep. See tests/unit/domain/analytics/test_concurrency.py
# and tests/integration/services/queries/analytics/test_reconcile_user_time.py.


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_step_completed_increments_all_scopes_on_completion_date(monkeypatch):
    calls = {}

    async def fake_user_daily(session, payload, work_date, worker_display_name, **kwargs):
        calls["user_daily"] = (work_date, kwargs)

    async def fake_user_lifetime(session, payload, worker_display_name, **kwargs):
        calls["user_lifetime"] = kwargs

    async def fake_user_section_daily(session, payload, work_date, worker_display_name, **kwargs):
        calls["user_section_daily"] = (work_date, kwargs)

    async def fake_section_daily(session, payload, work_date, **kwargs):
        calls["section_daily"] = (work_date, kwargs)

    monkeypatch.setattr(module, "_increment_user_daily", fake_user_daily)
    monkeypatch.setattr(module, "_increment_user_lifetime", fake_user_lifetime)
    monkeypatch.setattr(module, "_increment_user_section_daily", fake_user_section_daily)
    monkeypatch.setattr(module, "_increment_section_daily", fake_section_daily)

    payload = SimpleNamespace(
        workspace_id="ws_1",
        step_id="tsp_1",
        credited_user_id="usr_1",
        working_section_id="sec_1",
        exited_at="2026-07-15T00:05:00+00:00",
    )
    task_step = SimpleNamespace(total_completed_count=0)

    await module._apply_step_completed(
        session=SimpleNamespace(),
        payload=payload,
        worker_display_name="Worker",
        task_step=task_step,
    )

    assert calls["user_daily"] == (date(2026, 7, 15), {"completed_count": 1})
    assert calls["user_lifetime"] == {"completed_count": 1}
    assert calls["user_section_daily"] == (date(2026, 7, 15), {"completed_count": 1})
    assert calls["section_daily"] == (date(2026, 7, 15), {"completed_count": 1})
    assert task_step.total_completed_count == 1
