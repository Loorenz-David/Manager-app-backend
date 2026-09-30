import logging
from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError as PydanticValidationError
from sqlalchemy import select

from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.users.user_declared_state_record import (
    UserDeclaredStateRecord,
)
from beyo_manager.services.commands.users._clock_worker_shift import (
    close_stale_open_shift,
    load_open_worker_shift_for_update,
)
from beyo_manager.services.commands.users._worker_shift_access import (
    resolve_worker_shift_target,
)
from beyo_manager.services.commands.users.reconcile_worker_shift_state import (
    reconcile_worker_shift_state,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events.worker_shift_realtime import (
    emit_steps_paused,
    emit_worker_shift_state,
)


logger = logging.getLogger(__name__)

_NO_DECLARED_STATE = "No declared state is open."


class CloseDeclaredWorkerStateRequest(BaseModel):
    user_id: str | None = None


def parse_close_declared_worker_state_request(
    data: dict,
) -> CloseDeclaredWorkerStateRequest:
    try:
        return CloseDeclaredWorkerStateRequest.model_validate(data)
    except PydanticValidationError as exc:
        raise ValidationError(str(exc)) from exc


async def close_declared_worker_state(ctx: ServiceContext) -> dict:
    request = parse_close_declared_worker_state_request(ctx.incoming_data)
    now = datetime.now(timezone.utc)

    async with maybe_begin(ctx.session):
        user_id = await resolve_worker_shift_target(ctx, request.user_id)
        # Preserve the shared lock order even though the open-shift invariant means
        # every open declaration necessarily has an open shift.
        current_shift = await load_open_worker_shift_for_update(
            ctx.session,
            ctx.workspace_id,
            user_id,
        )
        # A shift past its work-day end is closed at that boundary, which also closes its
        # open declaration there — so after it there is nothing left to close.
        stale = await close_stale_open_shift(
            ctx.session,
            ctx.workspace_id,
            user_id,
            current_shift,
            now,
        )
        if stale is None:
            open_declared, reconcile_outcome = await _close_open_declaration(
                ctx, user_id, now
            )

    if stale is not None:
        # The closure is committed (deterministic whoever triggers it); the worker has no
        # open shift and so no open declaration — the same answer `GET /current` gives.
        await emit_worker_shift_state(ctx.session, ctx.workspace_id, user_id)
        await emit_steps_paused(ctx.workspace_id, stale.paused_step_ids)
        raise ConflictError(_NO_DECLARED_STATE)

    await emit_worker_shift_state(ctx.session, ctx.workspace_id, user_id)

    return {
        "shift_state": reconcile_outcome.state.value,
        "closed_declared_state_id": open_declared.client_id,
    }


async def _close_open_declaration(ctx: ServiceContext, user_id: str, now: datetime):
    """Close the open declaration on the worker's current, in-day shift (lock held)."""
    open_declared = (
        await ctx.session.execute(
            select(UserDeclaredStateRecord)
            .where(
                UserDeclaredStateRecord.workspace_id == ctx.workspace_id,
                UserDeclaredStateRecord.user_id == user_id,
                UserDeclaredStateRecord.exited_at.is_(None),
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if open_declared is None:
        raise ConflictError(_NO_DECLARED_STATE)

    open_declared.exited_at = now
    open_declared.closed_by_id = ctx.user_id
    reconcile_outcome = await reconcile_worker_shift_state(
        ctx.session,
        ctx.workspace_id,
        user_id,
        now,
    )
    if reconcile_outcome.state is None:
        raise RuntimeError("Declared state reconciliation requires an open shift.")

    logger.info(
        "worker_shift.declared_state_closed | "
        "workspace_id=%s user_id=%s actor_id=%s declared_record_id=%s",
        ctx.workspace_id,
        user_id,
        ctx.user_id,
        open_declared.client_id,
    )
    return open_declared, reconcile_outcome
