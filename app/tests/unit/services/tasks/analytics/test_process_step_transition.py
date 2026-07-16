from datetime import date
from types import SimpleNamespace

import pytest

from beyo_manager.services.tasks.analytics import process_step_transition as module


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_working_close_uses_credited_user_and_still_updates_section(monkeypatch):
    calls = {}

    async def fake_increment_user_daily(session, payload, work_date, worker_display_name, **kwargs):
        calls["user_daily"] = {
            "credited_user_id": payload.credited_user_id,
            "worker_display_name": worker_display_name,
            "kwargs": kwargs,
        }

    async def fake_increment_user_lifetime(session, payload, worker_display_name, **kwargs):
        calls["user_lifetime"] = {
            "credited_user_id": payload.credited_user_id,
            "worker_display_name": worker_display_name,
            "kwargs": kwargs,
        }

    async def fake_increment_user_section_daily(session, payload, work_date, worker_display_name, **kwargs):
        calls["user_section_daily"] = {
            "credited_user_id": payload.credited_user_id,
            "worker_display_name": worker_display_name,
            "kwargs": kwargs,
        }

    async def fake_increment_section_daily(session, payload, work_date, **kwargs):
        calls["section_daily"] = {
            "working_section_id": payload.working_section_id,
            "kwargs": kwargs,
        }

    async def fake_compute_cost_minor(session, worker_id, workspace_id, interval_seconds):
        calls["cost_minor"] = {
            "worker_id": worker_id,
            "workspace_id": workspace_id,
            "interval_seconds": interval_seconds,
        }
        return 123

    monkeypatch.setattr(module, "_increment_user_daily", fake_increment_user_daily)
    monkeypatch.setattr(module, "_increment_user_lifetime", fake_increment_user_lifetime)
    monkeypatch.setattr(module, "_increment_user_section_daily", fake_increment_user_section_daily)
    monkeypatch.setattr(module, "_increment_section_daily", fake_increment_section_daily)
    monkeypatch.setattr(module, "_compute_cost_minor", fake_compute_cost_minor)

    payload = SimpleNamespace(
        workspace_id="ws_1",
        credited_user_id="usr_credit",
        assigned_worker_id="usr_assigned",
        working_section_id="sec_1",
        working_section_name_snapshot="Section A",
        entered_at="2026-05-26T10:00:00+00:00",
    )

    await module._apply_working_close(
        session=SimpleNamespace(),
        payload=payload,
        interval_seconds=60,
        worker_display_name="Credited Worker",
    )

    assert calls["cost_minor"]["worker_id"] == "usr_credit"
    assert calls["user_daily"]["credited_user_id"] == "usr_credit"
    assert calls["user_lifetime"]["credited_user_id"] == "usr_credit"
    assert calls["user_section_daily"]["credited_user_id"] == "usr_credit"
    assert calls["section_daily"]["working_section_id"] == "sec_1"
    assert calls["user_daily"]["kwargs"]["working_seconds"] == 60


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
