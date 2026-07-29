import logging
from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError as PydanticValidationError
from sqlalchemy import select

from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.users.user_declared_state_record import (
    UserDeclaredStateRecord,
)
from beyo_manager.services.commands.users._clock_worker_shift import (
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


logger = logging.getLogger(__name__)


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
        await load_open_worker_shift_for_update(
            ctx.session,
            ctx.workspace_id,
            user_id,
        )
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
            raise ConflictError("No declared state is open.")

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

    return {
        "shift_state": reconcile_outcome.state.value,
        "closed_declared_state_id": open_declared.client_id,
    }
