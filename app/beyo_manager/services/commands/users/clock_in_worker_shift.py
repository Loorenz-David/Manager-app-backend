from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError as PydanticValidationError

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.users._clock_worker_shift import clock_in_shift_for_user
from beyo_manager.services.commands.users._worker_shift_access import resolve_worker_shift_target
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


class ClockInWorkerShiftRequest(BaseModel):
    user_id: str | None = None


def parse_clock_in_worker_shift_request(data: dict) -> ClockInWorkerShiftRequest:
    try:
        return ClockInWorkerShiftRequest.model_validate(data)
    except PydanticValidationError as exc:
        raise ValidationError(str(exc)) from exc


async def clock_in_worker_shift(ctx: ServiceContext) -> dict:
    request = parse_clock_in_worker_shift_request(ctx.incoming_data)
    async with maybe_begin(ctx.session):
        user_id = await resolve_worker_shift_target(ctx, request.user_id)
        await clock_in_shift_for_user(
            ctx.session,
            ctx.workspace_id,
            user_id,
            datetime.now(timezone.utc),
            ctx.user_id,
        )
    return {"action": "clock_in", "user_id": user_id}
