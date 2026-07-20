from __future__ import annotations

from beyo_manager.domain.connecteam.time_activity_event import ConnecteamTimeActivityEvent
from beyo_manager.services.queries.users.resolve_connecteam_worker import ResolvedConnecteamWorker
from beyo_manager.services.tasks.connecteam.handlers.handle_clock_out import (
    _execute_clock_out,
)
from beyo_manager.services.tasks.connecteam.handlers.handle_clock_in import ConnecteamHandlerResult


async def execute(
    *,
    session,
    worker: ResolvedConnecteamWorker,
    event: ConnecteamTimeActivityEvent,
) -> ConnecteamHandlerResult:
    return await _execute_clock_out(
        session=session,
        worker=worker,
        event=event,
        auto_clock_out=True,
    )
