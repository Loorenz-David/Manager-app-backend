from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .enums import ConnecteamActivityTypeEnum, ConnecteamEventTypeEnum


@dataclass(frozen=True)
class ConnecteamTimeActivityEvent:
    event_key: str
    provider: str
    event_type: str
    activity_type: str
    request_id: str | None
    company_id: str | None
    connecteam_user_id: str | None
    time_clock_id: str | None
    time_activity_id: str | None
    occurred_at: str | None
    received_at: str
    payload: dict

    @property
    def supported_event_type(self) -> ConnecteamEventTypeEnum | None:
        try:
            return ConnecteamEventTypeEnum(self.event_type)
        except ValueError:
            return None

    @property
    def activity(self) -> ConnecteamActivityTypeEnum:
        try:
            return ConnecteamActivityTypeEnum(self.activity_type)
        except ValueError:
            return ConnecteamActivityTypeEnum.UNKNOWN

    def as_payload(self) -> dict:
        return {
            "event_key": self.event_key,
            "provider": self.provider,
            "event_type": self.event_type,
            "activity_type": self.activity_type,
            "request_id": self.request_id,
            "company_id": self.company_id,
            "connecteam_user_id": self.connecteam_user_id,
            "time_clock_id": self.time_clock_id,
            "time_activity_id": self.time_activity_id,
            "occurred_at": self.occurred_at,
            "received_at": self.received_at,
            "payload": self.payload,
        }


def build_event_key(
    *, request_id: str | None, company_id: str | None, event_type: str,
    activity_type: str, connecteam_user_id: str | None, time_clock_id: str | None,
    time_activity_id: str | None, event_timestamp: str | None, raw_body: bytes,
) -> str:
    if request_id:
        return f"connecteam:{request_id}"
    raw_hash = hashlib.sha256(raw_body).hexdigest()
    material = "|".join(
        [company_id or "", event_type, activity_type, connecteam_user_id or "",
         time_clock_id or "", time_activity_id or "", event_timestamp or "", raw_hash]
    )
    return f"connecteam:{hashlib.sha256(material.encode()).hexdigest()}"

