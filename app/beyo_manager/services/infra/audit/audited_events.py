from __future__ import annotations

import os

# Default audited events — high-risk auth, membership, and destructive actions.
_BASE_AUDITED_EVENTS: frozenset[str] = frozenset({
    # Auth
    "auth:signed-in",
    "auth:signed-out",
    "auth:token-refreshed",
    "auth:password-changed",
    # Workspace membership
    "workspace:member-invited",
    "workspace:member-removed",
    "workspace:role-changed",
    # Cases
    "case:state-changed",
    "case:deleted",
    "case:participant-removed",
    # Messages
    "message:deleted",
})

# Domain modules extend this by calling register_audited_events() at startup.
_EXTENSIONS: set[str] = set()


def register_audited_events(events: set[str] | list[str]) -> None:
    """Register additional audited events from a domain module.
    Call during application startup before the first request.
    """
    _EXTENSIONS.update(events)


def get_audited_events() -> frozenset[str]:
    """Return the merged set of audited event names.
    Combines base defaults + registered extensions + AUDITED_EVENTS env override.
    """
    combined: set[str] = set(_BASE_AUDITED_EVENTS) | _EXTENSIONS
    env_override = os.environ.get("AUDITED_EVENTS", "")
    if env_override.strip():
        combined |= {e.strip() for e in env_override.split(",") if e.strip()}
    return frozenset(combined)
