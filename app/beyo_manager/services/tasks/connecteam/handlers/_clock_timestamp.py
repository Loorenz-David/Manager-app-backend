from __future__ import annotations

import math
from datetime import datetime, timezone

from beyo_manager.domain.connecteam.time_activity_event import ConnecteamTimeActivityEvent


def clock_event_timestamp(event: ConnecteamTimeActivityEvent) -> datetime:
    """Return the provider event time, falling back to webhook receipt time."""
    raw_value = (event.occurred_at or event.received_at).strip()

    try:
        epoch_seconds = float(raw_value)
    except ValueError:
        epoch_seconds = None

    if epoch_seconds is not None:
        if not math.isfinite(epoch_seconds):
            raise ValueError("Connecteam event timestamp must be finite.")
        return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)

    parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
