from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError as PydanticValidationError

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.users._clock_worker_shift import clock_out_shift_for_user
from beyo_manager.services.commands.users._worker_shift_access import resolve_worker_shift_target
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


class ClockOutWorkerShiftRequest(BaseModel):
    user_id: str | None = None
    clock_out_at: datetime | None = None


def parse_clock_out_worker_shift_request(data: dict) -> ClockOutWorkerShiftRequest:
    try:
        return ClockOutWorkerShiftRequest.model_validate(data)
    except PydanticValidationError as exc:
        raise ValidationError(str(exc)) from exc


async def clock_out_worker_shift(ctx: ServiceContext) -> dict:
    request = parse_clock_out_worker_shift_request(ctx.incoming_data)
    clock_out_at = request.clock_out_at or datetime.now(timezone.utc)
    async with maybe_begin(ctx.session):
        user_id = await resolve_worker_shift_target(ctx, request.user_id)
        transitioned_steps = await clock_out_shift_for_user(
            ctx.session,
            ctx.workspace_id,
            user_id,
            clock_out_at,
            ctx.user_id,
        )
    return {
        "action": "clock_out",
        "user_id": user_id,
        "transitioned_steps": transitioned_steps,
    }
