from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from beyo_manager.domain.tasks.serializers import serialize_task_light


@pytest.mark.unit
def test_serialize_task_light_includes_task_schedule_fields():
    task = SimpleNamespace(
        client_id="tsk_1",
        task_type=SimpleNamespace(value="repair"),
        priority=SimpleNamespace(value="high"),
        state=SimpleNamespace(value="open"),
        return_source=None,
        item_location=None,
        ready_by_at=datetime(2026, 6, 25, 12, 30, tzinfo=timezone.utc),
        scheduled_start_at=datetime(2026, 6, 26, 9, 0, tzinfo=timezone.utc),
        scheduled_end_at=datetime(2026, 6, 26, 11, 0, tzinfo=timezone.utc),
        return_method=None,
    )

    result = serialize_task_light(task)

    assert result["ready_by_at"] == "2026-06-25T12:30:00+00:00"
    assert result["scheduled_start_at"] == "2026-06-26T09:00:00+00:00"
    assert result["scheduled_end_at"] == "2026-06-26T11:00:00+00:00"
