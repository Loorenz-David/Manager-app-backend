from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError as PydanticValidationError

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.users._clock_worker_shift import clock_out_shift_for_user
from beyo_manager.services.commands.users._worker_shift_access import resolve_worker_shift_target
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events.worker_shift_realtime import (
    emit_steps_paused,
    emit_worker_shift_state,
)


class ClockOutWorkerShiftRequest(BaseModel):
    user_id: str | None = None


def parse_clock_out_worker_shift_request(data: dict) -> ClockOutWorkerShiftRequest:
    try:
        return ClockOutWorkerShiftRequest.model_validate(data)
    except PydanticValidationError as exc:
        raise ValidationError(str(exc)) from exc


async def clock_out_worker_shift(ctx: ServiceContext) -> dict:
    """Close the target shift and return its internal clock-out timestamp.

    ``_clock_out_at`` is part of this command's direct-caller contract. HTTP routes
    must consume and remove it before serializing the response; the underscore marks
    it as route-internal rather than client-visible.
    """
    request = parse_clock_out_worker_shift_request(ctx.incoming_data)
    clock_out_at = datetime.now(timezone.utc)
    async with maybe_begin(ctx.session):
        user_id = await resolve_worker_shift_target(ctx, request.user_id)
        paused_step_ids = await clock_out_shift_for_user(
            ctx.session,
            ctx.workspace_id,
            user_id,
            clock_out_at,
            ctx.user_id,
        )
    await emit_worker_shift_state(ctx.session, ctx.workspace_id, user_id)
    await emit_steps_paused(ctx.workspace_id, paused_step_ids)
    return {
        "action": "clock_out",
        "user_id": user_id,
        "transitioned_steps": len(paused_step_ids),
        "analytics": None,
        "_clock_out_at": clock_out_at,
    }
