from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ConnecteamWebhookPayload(BaseModel):
    """Tolerant provider DTO; Connecteam may add envelope fields over time."""

    model_config = ConfigDict(extra="allow")
    request_id: str | None = None
    requestId: str | None = None
    company_id: str | None = None
    companyId: str | None = None
    company: Any = None
    event_type: str | None = None
    eventType: str | None = None
    activity_type: str | None = None
    activityType: str | None = None
    event_timestamp: str | int | float | None = None
    eventTimestamp: str | int | float | None = None
    user_id: str | int | None = None
    userId: str | int | None = None
    time_clock_id: str | int | None = None
    timeClockId: str | int | None = None
    time_activity_id: str | int | None = None
    timeActivityId: str | int | None = None
    data: Any = None
    time_activity: Any = None

