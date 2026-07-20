from __future__ import annotations

from dataclasses import dataclass

from beyo_manager.core.logging.config import log_event
from beyo_manager.domain.connecteam.enums import ConnecteamProcessingOutcomeEnum
from beyo_manager.domain.connecteam.time_activity_event import ConnecteamTimeActivityEvent
from beyo_manager.errors.validation import ConflictError
from beyo_manager.services.commands.users._clock_worker_shift import clock_in_shift_for_user
from beyo_manager.services.queries.users.resolve_connecteam_worker import ResolvedConnecteamWorker
from beyo_manager.services.tasks.connecteam.handlers._clock_timestamp import clock_event_timestamp


@dataclass(frozen=True)
class ConnecteamHandlerResult:
    outcome: str = ConnecteamProcessingOutcomeEnum.PROCESSED.value
    transitioned_steps: int = 0


async def execute(
    *,
    session,
    worker: ResolvedConnecteamWorker,
    event: ConnecteamTimeActivityEvent,
) -> ConnecteamHandlerResult:
    occurred_at = clock_event_timestamp(event)
    try:
        await clock_in_shift_for_user(
            session,
            worker.workspace_id,
            worker.user_id,
            occurred_at,
            changed_by_id=worker.user_id,
        )
    except ConflictError:
        log_event(
            "connecteam_clock_event_noop",
            provider="connecteam",
            event_key=event.event_key,
            request_id=event.request_id,
            connecteam_event_type=event.event_type,
            activity_type=event.activity_type,
            connecteam_user_id=event.connecteam_user_id,
            time_clock_id=event.time_clock_id,
            time_activity_id=event.time_activity_id,
            workspace_id=worker.workspace_id,
            internal_user_id=worker.user_id,
            occurred_at=occurred_at.isoformat(),
            noop_reason=ConnecteamProcessingOutcomeEnum.ALREADY_CLOCKED_IN.value,
            processing_status=ConnecteamProcessingOutcomeEnum.ALREADY_CLOCKED_IN.value,
        )
        return ConnecteamHandlerResult(
            outcome=ConnecteamProcessingOutcomeEnum.ALREADY_CLOCKED_IN.value
        )

    log_event(
        "connecteam_clock_in_applied",
        provider="connecteam",
        event_key=event.event_key,
        request_id=event.request_id,
        connecteam_event_type=event.event_type,
        activity_type=event.activity_type,
        connecteam_user_id=event.connecteam_user_id,
        time_clock_id=event.time_clock_id,
        time_activity_id=event.time_activity_id,
        workspace_id=worker.workspace_id,
        internal_user_id=worker.user_id,
        occurred_at=occurred_at.isoformat(),
        processing_status=ConnecteamProcessingOutcomeEnum.CLOCK_IN_APPLIED.value,
    )
    return ConnecteamHandlerResult(
        outcome=ConnecteamProcessingOutcomeEnum.CLOCK_IN_APPLIED.value
    )
