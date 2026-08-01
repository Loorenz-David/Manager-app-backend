"""Fill the event bus's handler list, in every process that can dispatch.

**Why this is called on import rather than at startup.** The handler list is module-level
state, so each process needs its own copy filled. It used to be filled from the FastAPI
lifespan and nowhere else, which meant `dispatch()` in a worker walked an empty list and
discarded the events without raising, logging, or failing a test. Notification socket events
were dropped that way from the first commit until 2026-08.

Startup hooks did not hold because there is no single startup path: five workers go through
`run_worker()`, four more (`task_router`, both schedulers, `email_idle_watcher`) have their
own `main()`. Any hook would have covered some entry points and silently missed the rest —
the same trap one level up. Importing is the one thing every dispatcher must do: you cannot
call `dispatch` without importing the package that defines it.

Safe to do at import because it registers three functions and touches nothing else — the DB
imports inside `audit_handler` and `webhook_handler` are deferred into their function bodies,
and `sockets/__init__.py` builds no server or Redis connection until `get_sio()` is called.
"""

from __future__ import annotations

import logging

from beyo_manager.services.infra.events.event_bus import register


logger = logging.getLogger(__name__)

_registered = False


def register_default_handlers() -> None:
    """Register the socket, audit and webhook handlers once per process."""
    global _registered
    if _registered:
        return

    from beyo_manager.services.infra.events.handlers.audit_handler import handle as audit_handle
    from beyo_manager.services.infra.events.handlers.socket_handler import handle as socket_handle
    from beyo_manager.services.infra.events.handlers.webhook_handler import handle as webhook_handle

    register(socket_handle)
    register(audit_handle)
    register(webhook_handle)
    _registered = True
    logger.debug("event_bus: default handlers registered")
