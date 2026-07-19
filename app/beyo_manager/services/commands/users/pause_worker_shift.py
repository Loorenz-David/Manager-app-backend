from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.services.commands.users._clock_worker_shift import (
    load_open_worker_shift_for_update,
)
from beyo_manager.services.commands.users._worker_shift_access import resolve_worker_shift_target
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


class PauseWorkerShiftRequest(BaseModel):
    reason: str

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reason must not be blank.")
        if len(value) > 512:
            raise ValueError("reason must not exceed 512 characters.")
        return value


def parse_pause_worker_shift_request(data: dict) -> PauseWorkerShiftRequest:
    try:
        return PauseWorkerShiftRequest.model_validate(data)
    except PydanticValidationError as exc:
        raise ValidationError(str(exc)) from exc


async def pause_worker_shift(ctx: ServiceContext) -> dict:
    request = parse_pause_worker_shift_request(ctx.incoming_data)
    now = datetime.now(timezone.utc)
    async with maybe_begin(ctx.session):
        user_id = await resolve_worker_shift_target(ctx, None)
        current = await load_open_worker_shift_for_update(
            ctx.session,
            ctx.workspace_id,
            user_id,
        )
        if current is None or current.state is not UserShiftStateEnum.IDLE:
            raise ConflictError("A shift can only be manually paused from IDLE.")
        current.exited_at = now
        ctx.session.add(
            UserShiftStateRecord(
                workspace_id=ctx.workspace_id,
                user_id=user_id,
                state=UserShiftStateEnum.IN_PAUSE,
                entered_at=now,
                exited_at=None,
                changed_by_id=ctx.user_id,
                reason=request.reason,
                manually_recorded=True,
            )
        )
        await ctx.session.flush()
    return {"state": UserShiftStateEnum.IN_PAUSE.value, "user_id": user_id}
