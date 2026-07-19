from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from beyo_manager.services.queries.analytics import estimation_sample as module


@pytest.mark.asyncio
async def test_loader_groups_positive_trusted_completed_step_durations(monkeypatch):
    start = datetime(2026, 7, 1, tzinfo=timezone.utc)
    contributions = [
        SimpleNamespace(
            is_open=False,
            step_is_deleted=False,
            step_is_completed=True,
            marked_wrong=False,
            entered_at=start + timedelta(hours=1),
            working_section_id="section",
            state="working",
            step_id="step",
            seconds=12.5,
        ),
        SimpleNamespace(
            is_open=False,
            step_is_deleted=False,
            step_is_completed=True,
            marked_wrong=False,
            entered_at=start + timedelta(hours=2),
            working_section_id="section",
            state="working",
            step_id="step",
            seconds=7.5,
        ),
        SimpleNamespace(
            is_open=False,
            step_is_deleted=False,
            step_is_completed=True,
            marked_wrong=True,
            entered_at=start + timedelta(hours=3),
            working_section_id="section",
            state="working",
            step_id="flagged",
            seconds=0.0,
        ),
        SimpleNamespace(
            is_open=True,
            step_is_deleted=False,
            step_is_completed=True,
            marked_wrong=False,
            entered_at=start + timedelta(hours=4),
            working_section_id="section",
            state="working",
            step_id="open",
            seconds=100.0,
        ),
    ]

    async def fake_compute(*_args, **_kwargs):
        return contributions

    monkeypatch.setattr(module, "compute_record_contributions", fake_compute)
    result = await module.load_trusted_step_duration_sample(
        SimpleNamespace(),
        "workspace",
        "user",
        start,
        start + timedelta(days=1),
        start + timedelta(days=2),
    )

    assert result == {("section", "working"): [20.0]}
