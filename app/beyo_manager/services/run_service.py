import logging
from collections.abc import Awaitable, Callable
from typing import Any

from beyo_manager.errors.base import DomainError
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.outcome import StatusOutcome

logger = logging.getLogger(__name__)

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
    """
    try:
        data = await fn(ctx)
        return StatusOutcome(success=True, data=data)
    except DomainError as exc:
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
