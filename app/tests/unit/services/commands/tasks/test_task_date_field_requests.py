from datetime import datetime, timezone

import pytest

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.tasks.requests import (
    parse_update_task_request,
    parse_update_task_ready_by_at_request,
    parse_update_task_schedule_request,
)


@pytest.mark.unit
def test_parse_update_task_request_accepts_task_type():
    request = parse_update_task_request(
        {
            "client_id": "tsk_1",
            "task_type": "return",
        }
    )

    assert request.client_id == "tsk_1"
    assert request.task_type.value == "return"


@pytest.mark.unit
def test_parse_update_task_ready_by_at_request_accepts_null_and_datetime():
    request = parse_update_task_ready_by_at_request(
        {
            "client_id": "tsk_1",
            "ready_by_at": "2026-06-25T12:30:00Z",
        }
    )

    assert request.client_id == "tsk_1"
    assert request.ready_by_at == datetime(2026, 6, 25, 12, 30, tzinfo=timezone.utc)


@pytest.mark.unit
def test_parse_update_task_schedule_request_accepts_null_schedule():
    request = parse_update_task_schedule_request(
        {
            "client_id": "tsk_1",
            "scheduled_start_at": None,
            "scheduled_end_at": None,
        }
    )

    assert request.client_id == "tsk_1"
    assert request.scheduled_start_at is None
    assert request.scheduled_end_at is None


@pytest.mark.unit
def test_parse_update_task_schedule_request_rejects_invalid_datetime():
    with pytest.raises(ValidationError):
        parse_update_task_schedule_request(
            {
                "client_id": "tsk_1",
                "scheduled_start_at": "not-a-datetime",
            }
        )
