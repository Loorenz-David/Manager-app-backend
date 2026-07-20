from __future__ import annotations


from beyo_manager.core.logging.config import log_event
from beyo_manager.domain.connecteam.enums import ConnecteamActivityTypeEnum, ConnecteamEventTypeEnum
from beyo_manager.domain.connecteam.time_activity_event import ConnecteamTimeActivityEvent
from beyo_manager.models.database import get_db_session
from beyo_manager.services.queries.users.resolve_connecteam_worker import (
    AmbiguousConnecteamMappingError,
    resolve_connecteam_worker,
)
from beyo_manager.services.tasks.connecteam.handlers.handle_auto_clock_out import execute as handle_auto_clock_out
from beyo_manager.services.tasks.connecteam.handlers.handle_clock_in import execute as handle_clock_in
from beyo_manager.services.tasks.connecteam.handlers.handle_clock_out import execute as handle_clock_out

HANDLER_MAP = {
    ConnecteamEventTypeEnum.CLOCK_IN: handle_clock_in,
    ConnecteamEventTypeEnum.CLOCK_OUT: handle_clock_out,
    ConnecteamEventTypeEnum.AUTO_CLOCK_OUT: handle_auto_clock_out,
}


def _event(raw: dict) -> ConnecteamTimeActivityEvent:
    values = dict(raw)
    values.setdefault("provider", "connecteam")
    values.setdefault("payload", {})
    return ConnecteamTimeActivityEvent(**values)


async def handle_connecteam_process_time_activity(raw_payload: dict, task_client_id: str) -> None:
    event = _event(raw_payload)
    if event.activity == ConnecteamActivityTypeEnum.MANUAL_BREAK:
        log_event("connecteam_webhook_completed", provider="connecteam", event_key=event.event_key,
                  processing_status="ignored_activity_type", execution_id=task_client_id)
        return
    try:
        event_type = ConnecteamEventTypeEnum(event.event_type)
    except ValueError:
        log_event("connecteam_webhook_rejected", provider="connecteam", event_key=event.event_key,
                  processing_status="unsupported_event_type", execution_id=task_client_id)
        return
    async for session in get_db_session():
        async with session.begin():
            try:
                worker = await resolve_connecteam_worker(
                    session,
                    connecteam_user_id=event.connecteam_user_id or "",
                    company_id=event.company_id,
                )
            except AmbiguousConnecteamMappingError:
                log_event(
                    "connecteam_webhook_completed",
                    provider="connecteam",
                    event_key=event.event_key,
                    processing_status="ambiguous_mapping",
                    execution_id=task_client_id,
                )
                return
            if worker is None:
                log_event(
                    "connecteam_worker_not_mapped",
                    provider="connecteam",
                    event_key=event.event_key,
                    connecteam_user_id=event.connecteam_user_id,
                    processing_status="worker_not_mapped",
                    execution_id=task_client_id,
                )
                return
            log_event(
                "connecteam_worker_resolved",
                provider="connecteam",
                event_key=event.event_key,
                connecteam_user_id=event.connecteam_user_id,
                workspace_id=worker.workspace_id,
                internal_user_id=worker.user_id,
                processing_status="resolved",
                execution_id=task_client_id,
            )
            result = await HANDLER_MAP[event_type](
                session=session,
                worker=worker,
                event=event,
            )
        log_event(
            "connecteam_webhook_completed",
            provider="connecteam",
            event_key=event.event_key,
            connecteam_event_type=event.event_type,
            activity_type=event.activity_type,
            processing_status=result.outcome,
            execution_id=task_client_id,
        )
        return
