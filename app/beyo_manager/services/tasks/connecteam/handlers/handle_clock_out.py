from __future__ import annotations

from beyo_manager.core.logging.config import log_event
from beyo_manager.domain.connecteam.enums import ConnecteamProcessingOutcomeEnum
from beyo_manager.domain.connecteam.time_activity_event import ConnecteamTimeActivityEvent
from beyo_manager.errors.validation import ConflictError
from beyo_manager.services.commands.users._clock_worker_shift import clock_out_shift_for_user
from beyo_manager.services.queries.users.resolve_connecteam_worker import ResolvedConnecteamWorker
from beyo_manager.services.tasks.connecteam.handlers._clock_timestamp import clock_event_timestamp
from beyo_manager.services.tasks.connecteam.handlers.handle_clock_in import ConnecteamHandlerResult


async def _execute_clock_out(
    *,
    session,
    worker: ResolvedConnecteamWorker,
    event: ConnecteamTimeActivityEvent,
    auto_clock_out: bool,
) -> ConnecteamHandlerResult:
    occurred_at = clock_event_timestamp(event)
    try:
        transitioned_steps = await clock_out_shift_for_user(
            session,
            worker.workspace_id,
            worker.user_id,
            occurred_at,
            changed_by_id=worker.user_id,
        )
    except ConflictError:
        # The midnight safeguard can close a shift before Connecteam's own
        # auto_clock_out arrives. That later delivery is an expected no-op.
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
            noop_reason=ConnecteamProcessingOutcomeEnum.NO_OPEN_SHIFT.value,
            processing_status=ConnecteamProcessingOutcomeEnum.NO_OPEN_SHIFT.value,
            auto_clock_out=auto_clock_out,
        )
        return ConnecteamHandlerResult(
            outcome=ConnecteamProcessingOutcomeEnum.NO_OPEN_SHIFT.value
        )

    log_event(
        "connecteam_clock_out_applied",
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
        transitioned_steps=transitioned_steps,
        processing_status=ConnecteamProcessingOutcomeEnum.CLOCK_OUT_APPLIED.value,
        auto_clock_out=auto_clock_out,
    )
    return ConnecteamHandlerResult(
        outcome=ConnecteamProcessingOutcomeEnum.CLOCK_OUT_APPLIED.value,
        transitioned_steps=transitioned_steps,
    )


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
        auto_clock_out=False,
    )
