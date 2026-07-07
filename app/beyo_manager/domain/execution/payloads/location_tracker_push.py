from dataclasses import dataclass


@dataclass(frozen=True)
class LocationTrackerPushPayload:
    changes: list[dict]
    requested_by_user_id: str | None = None
