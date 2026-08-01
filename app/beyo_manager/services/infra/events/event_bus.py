from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from .domain_event import BatchWorkspaceEvent, Event

logger = logging.getLogger(__name__)

DomainEvent = Event | BatchWorkspaceEvent


_handlers: list[Callable[[DomainEvent], Awaitable[None]]] = []


def register(handler: Callable[[DomainEvent], Awaitable[None]]) -> None:
    """Register an async handler. Call during application startup only."""
    _handlers.append(handler)


async def dispatch(events: list[DomainEvent]) -> None:
    """Call every registered handler for each event after a transaction commits.
    A failing handler is logged and skipped so one bad handler cannot block others.
    """
    if events and not _handlers:
        # Dropping events used to be completely silent — an empty handler list is a valid
        # loop, so nothing raised, nothing logged, and no test noticed for two and a half
        # months. `bootstrap.register_default_handlers` should make this unreachable in a
        # real process; if it fires, something imported `dispatch` past that guarantee.
        logger.warning(
            "event_bus: %d event(s) dropped — no handlers registered in this process | events=%s",
            len(events),
            [event.event_name for event in events],
        )
        return
    for event in events:
        for handler in _handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "event handler failed | event=%s handler=%s",
                    event.event_name,
                    handler.__name__,
                )
