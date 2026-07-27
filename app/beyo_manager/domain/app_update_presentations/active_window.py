"""Active-time-window evaluation for a presentation. Pure, no I/O."""

from datetime import datetime


def is_within_active_window(
    starts_at: datetime | None,
    expires_at: datetime | None,
    now: datetime,
) -> bool:
    """A presentation is active when ``now`` is inside ``[starts_at, expires_at)``.

    A null bound means "unbounded" on that side. ``starts_at`` is inclusive,
    ``expires_at`` is exclusive.
    """
    if starts_at is not None and starts_at > now:
        return False
    if expires_at is not None and expires_at <= now:
        return False
    return True
