import logging
from collections.abc import Awaitable, Callable
from typing import Any

from beyo_manager.errors.base import DomainError
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.outcome import StatusOutcome

logger = logging.getLogger(__name__)


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
    except Exception:
        logger.exception(
            "Unexpected error in %s | user=%s workspace=%s",
            fn.__name__,
            ctx.user_id,
            ctx.workspace_id,
        )
        return StatusOutcome(
            success=False,
            error=DomainError("An unexpected internal error occurred."),
        )
