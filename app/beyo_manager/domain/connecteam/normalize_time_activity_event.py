from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from beyo_manager.errors.validation import ValidationError

from .time_activity_event import ConnecteamTimeActivityEvent, build_event_key


def _find(value: Any, names: set[str]) -> Any:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in names and item not in (None, ""):
                return item
        for item in value.values():
            found = _find(item, names)
            if found not in (None, ""):
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find(item, names)
            if found not in (None, ""):
                return found
    return None


def _string(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def normalize_time_activity_event(raw_body: bytes, payload: dict) -> ConnecteamTimeActivityEvent:
    event_type = _string(_find(payload, {"event_type", "eventtype", "event"}))
    if not event_type:
        raise ValidationError("event_type is required")
    event_type = event_type.strip().lower()
    activity_type = (_string(_find(payload, {"activity_type", "activitytype", "activity"})) or "unknown").strip().lower()
    request_id = _string(_find(payload, {"request_id", "requestid", "id"}))
    company_id = _string(_find(payload, {"company_id", "companyid", "company"}))
    user_id = _string(_find(payload, {"user_id", "userid", "connecteam_user_id", "connecteamuserid"}))
    time_clock_id = _string(_find(payload, {"time_clock_id", "timeclockid"}))
    time_activity_id = _string(_find(payload, {"time_activity_id", "timeactivityid"}))
    occurred_at = _string(_find(payload, {"event_timestamp", "eventtimestamp", "occurred_at", "timestamp"}))
    if event_type in {"clock_in", "clock_out", "auto_clock_out"} and not user_id:
        raise ValidationError("user_id is required for supported time activity events")
    received_at = datetime.now(timezone.utc).isoformat()
    return ConnecteamTimeActivityEvent(
        event_key=build_event_key(
            request_id=request_id, company_id=company_id, event_type=event_type,
            activity_type=activity_type, connecteam_user_id=user_id,
            time_clock_id=time_clock_id, time_activity_id=time_activity_id,
            event_timestamp=occurred_at, raw_body=raw_body,
        ),
        provider="connecteam", event_type=event_type, activity_type=activity_type,
        request_id=request_id, company_id=company_id,
        connecteam_user_id=user_id, time_clock_id=time_clock_id,
        time_activity_id=time_activity_id, occurred_at=occurred_at,
        received_at=received_at, payload=payload,
    )
