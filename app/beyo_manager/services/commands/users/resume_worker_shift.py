from datetime import datetime, timezone

from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.services.commands.users._clock_worker_shift import (
    load_open_worker_shift_for_update,
)
from beyo_manager.services.commands.users._worker_shift_access import resolve_worker_shift_target
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def resume_worker_shift(ctx: ServiceContext) -> dict:
    now = datetime.now(timezone.utc)
    async with maybe_begin(ctx.session):
        user_id = await resolve_worker_shift_target(ctx, None)
        current = await load_open_worker_shift_for_update(
            ctx.session,
            ctx.workspace_id,
            user_id,
        )
        if (
            current is None
            or current.state is not UserShiftStateEnum.IN_PAUSE
            or not current.manually_recorded
        ):
            raise ConflictError("A shift can only be resumed from a manual pause.")
        current.exited_at = now
        ctx.session.add(
            UserShiftStateRecord(
                workspace_id=ctx.workspace_id,
                user_id=user_id,
                state=UserShiftStateEnum.IDLE,
                entered_at=now,
                exited_at=None,
                changed_by_id=ctx.user_id,
                reason=None,
                manually_recorded=False,
            )
        )
        await ctx.session.flush()
    return {"state": UserShiftStateEnum.IDLE.value, "user_id": user_id}
