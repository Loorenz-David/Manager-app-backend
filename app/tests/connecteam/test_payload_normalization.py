from __future__ import annotations

import json

import pytest

from beyo_manager.domain.connecteam.normalize_time_activity_event import normalize_time_activity_event
from beyo_manager.errors.validation import ValidationError


def _payload(event_type: str = "clock_in", activity_type: str = "shift") -> dict:
    return {
        "requestId": "request-1",
        "eventType": event_type,
        "activityType": activity_type,
        "data": {"userId": "worker-1", "timeClockId": "clock-1", "timeActivityId": "activity-1"},
        "newField": {"future": True},
    }


def test_normalizes_nested_event_and_preserves_additive_fields() -> None:
    payload = _payload()
    event = normalize_time_activity_event(json.dumps(payload).encode(), payload)
    assert event.event_key == "connecteam:request-1"
    assert event.connecteam_user_id == "worker-1"
    assert event.payload["newField"]["future"] is True


def test_manual_break_is_classified() -> None:
    payload = _payload(activity_type="manual_break")
    assert normalize_time_activity_event(json.dumps(payload).encode(), payload).activity_type == "manual_break"


def test_supported_event_without_user_is_rejected() -> None:
    payload = _payload()
    del payload["data"]["userId"]
    with pytest.raises(ValidationError):
        normalize_time_activity_event(json.dumps(payload).encode(), payload)

