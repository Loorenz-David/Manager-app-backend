import logging
from collections.abc import Awaitable, Callable
from typing import Any

from beyo_manager.errors.base import DomainError
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.outcome import StatusOutcome

logger = logging.getLogger(__name__)

_DEPTH_KEY = "run_service_depth"

# Non-sensitive entity identifiers worth surfacing when a service blows up.
# Deliberately excludes anything credential-bearing: no tokens, presigned URLs,
# passwords, auth headers or free-text user content.
_ENTITY_ID_KEYS = (
    "client_id",
    "presentation_id",
    "slide_id",
    "media_id",
    "pending_upload_client_id",
    "storage_key",
)


def _entity_ids(ctx: ServiceContext) -> dict[str, Any]:
    data = ctx.incoming_data
    if not isinstance(data, dict):
        return {}
    return {key: data[key] for key in _ENTITY_ID_KEYS if data.get(key) is not None}


async def run_service(
    fn: Callable[[ServiceContext], Awaitable[Any]],
    ctx: ServiceContext,
) -> StatusOutcome:
    """Single error boundary for all service calls.

    Catches DomainError and returns a failed StatusOutcome.
    Catches unexpected exceptions, logs the traceback, and returns a generic error.

    The outermost run on a session also owns the inventory-ledger scope: one correlation id
    for everything it writes, and one ``upholstery:inventory-updated`` event per inventory it
    touched, dispatched only after success.
    """
    session = getattr(ctx, "session", None)
    info = getattr(session, "info", None)
    if not isinstance(info, dict):  # mocked sessions in unit tests
        info = None
    outermost = info is not None and info.get(_DEPTH_KEY, 0) == 0
    if info is not None:
        info[_DEPTH_KEY] = info.get(_DEPTH_KEY, 0) + 1
    try:
        data = await fn(ctx)
        if outermost:
            await _dispatch_inventory_events(session)
        return StatusOutcome(success=True, data=data)
    except DomainError as exc:
        # A refusal is an outcome, not a crash — but it used to leave no trace at
        # all, so a rejected webhook was indistinguishable from one that never
        # arrived. Client-side refusals (4xx) are INFO; a 5xx domain error is a
        # warning because it means the server gave up on work it accepted.
        service_name = getattr(fn, "__name__", repr(fn))
        logger.log(
            logging.WARNING if exc.http_status >= 500 else logging.INFO,
            "Refused %s | exc_type=%s status=%s exc_message=%s "
            "user_id=%s workspace_id=%s entities=%s",
            service_name,
            type(exc).__name__,
            exc.http_status,
            exc,
            ctx.user_id,
            ctx.workspace_id,
            _entity_ids(ctx),
            extra={
                "event_type": "service.domain_error",
                "service": service_name,
                "status_code": exc.http_status,
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        return StatusOutcome(success=False, error=exc)
    except Exception as exc:
        service_name = getattr(fn, "__name__", repr(fn))
        logger.exception(
            "Unexpected error in %s | exc_type=%s exc_message=%s "
            "user_id=%s workspace_id=%s entities=%s",
            service_name,
            type(exc).__name__,
            exc,
            ctx.user_id,
            ctx.workspace_id,
            _entity_ids(ctx),
            extra={
                "event_type": "service.unexpected_error",
                "service": service_name,
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        return StatusOutcome(
            success=False,
            error=DomainError("An unexpected internal error occurred."),
        )
    finally:
        if info is not None:
            info[_DEPTH_KEY] = info.get(_DEPTH_KEY, 1) - 1
            if outermost:
                _reset_inventory_scope(session)


async def _dispatch_inventory_events(session) -> None:
    from beyo_manager.services.infra.events.inventory_realtime import (
        dispatch_touched_inventory_events,
    )

    try:
        await dispatch_touched_inventory_events(session)
    except Exception:
        logger.exception("inventory realtime dispatch failed")


def _reset_inventory_scope(session) -> None:
    from beyo_manager.services.commands.upholstery._inventory_history import reset_movement_scope

    reset_movement_scope(session)
