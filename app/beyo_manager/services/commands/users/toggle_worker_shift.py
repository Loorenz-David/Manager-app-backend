from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError as PydanticValidationError

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.users._clock_worker_shift import (
    clock_in_shift_for_user,
    clock_out_shift_for_user,
    load_open_worker_shift_for_update,
)
from beyo_manager.services.commands.users._worker_shift_access import resolve_worker_shift_target
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events.worker_shift_realtime import (
    emit_steps_paused,
    emit_worker_shift_state,
)


class ToggleWorkerShiftRequest(BaseModel):
    user_id: str | None = None


def parse_toggle_worker_shift_request(data: dict) -> ToggleWorkerShiftRequest:
    try:
        return ToggleWorkerShiftRequest.model_validate(data)
    except PydanticValidationError as exc:
        raise ValidationError(str(exc)) from exc


async def toggle_worker_shift(ctx: ServiceContext) -> dict:
    """Toggle the target shift, returning route-internal ``_clock_out_at`` on clock-out.

    Direct callers receive the timestamp as part of the command contract. HTTP routes
    must pop it before serialization; it is intentionally not a client response field.
    """
    request = parse_toggle_worker_shift_request(ctx.incoming_data)
    now = datetime.now(timezone.utc)
    async with maybe_begin(ctx.session):
        user_id = await resolve_worker_shift_target(ctx, request.user_id)
        current = await load_open_worker_shift_for_update(
            ctx.session,
            ctx.workspace_id,
            user_id,
        )
        if current is None:
            await clock_in_shift_for_user(
                ctx.session,
                ctx.workspace_id,
                user_id,
                now,
                ctx.user_id,
            )
            action = "clock_in"
            paused_step_ids: list[str] = []
        else:
            paused_step_ids = await clock_out_shift_for_user(
                ctx.session,
                ctx.workspace_id,
                user_id,
                now,
                ctx.user_id,
            )
            action = "clock_out"
    await emit_worker_shift_state(ctx.session, ctx.workspace_id, user_id)
    await emit_steps_paused(ctx.workspace_id, paused_step_ids)
    result = {
        "action": action,
        "user_id": user_id,
        "transitioned_steps": len(paused_step_ids),
    }
    if action == "clock_out":
        result["analytics"] = None
        result["_clock_out_at"] = now
    return result
