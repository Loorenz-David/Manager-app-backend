import logging
from datetime import datetime, timezone

from pydantic import (
    BaseModel,
    ValidationError as PydanticValidationError,
    field_validator,
)
from sqlalchemy import select

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.users.serializers import serialize_declared_state
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.users.user_declared_state_record import (
    UserDeclaredStateRecord,
)
from beyo_manager.services.commands.task_steps._step_transition_core import (
    _apply_step_transition,
)
from beyo_manager.services.commands.users._clock_worker_shift import (
    _load_open_working_step_rows,
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


class DeclareWorkerStateRequest(BaseModel):
    user_id: str | None = None
    pause_reason_id: str
    description: str | None = None

    @field_validator("user_id", "pause_reason_id")
    @classmethod
    def validate_identifier(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("identifier must not be blank.")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if len(value) > 512:
            raise ValueError("description must not exceed 512 characters.")
        return value


def parse_declare_worker_state_request(data: dict) -> DeclareWorkerStateRequest:
    try:
        return DeclareWorkerStateRequest.model_validate(data)
    except PydanticValidationError as exc:
        raise ValidationError(str(exc)) from exc


async def declare_worker_state(ctx: ServiceContext) -> dict:
    request = parse_declare_worker_state_request(ctx.incoming_data)
    now = datetime.now(timezone.utc)

    async with maybe_begin(ctx.session):
        user_id = await resolve_worker_shift_target(ctx, request.user_id)
        current_shift = await load_open_worker_shift_for_update(
            ctx.session,
            ctx.workspace_id,
            user_id,
        )
        if current_shift is None:
            raise ConflictError("Worker must be clocked in to declare a state.")

        pause_reason = (
            await ctx.session.execute(
                select(PauseReason).where(
                    PauseReason.workspace_id == ctx.workspace_id,
                    PauseReason.client_id == request.pause_reason_id,
                    PauseReason.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if pause_reason is None:
            raise NotFound("Pause reason not found.")
        if pause_reason.pause_type is not PauseTypeEnum.PERSONAL:
            raise ValidationError("Only personal pause reasons can be declared.")
        if pause_reason.requires_description and request.description is None:
            raise ValidationError("Description is required for this pause reason.")

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
        switched_from_id = None
        if open_declared is not None:
            open_declared.exited_at = now
            open_declared.closed_by_id = ctx.user_id
            switched_from_id = open_declared.client_id

        open_working_rows = await _load_open_working_step_rows(
            ctx.session,
            ctx.workspace_id,
            user_id,
        )
        for closing_record, step, task in open_working_rows:
            await _apply_step_transition(
                ctx,
                step,
                task,
                closing_record,
                new_state=TaskStepStateEnum.PAUSED,
                pause_reason_id=pause_reason.client_id,
                description=None,
                credited_user_id=user_id,
                now=now,
            )

        declared_state = UserDeclaredStateRecord(
            workspace_id=ctx.workspace_id,
            user_id=user_id,
            pause_reason_id=pause_reason.client_id,
            description=request.description,
            entered_at=now,
            exited_at=None,
            created_by_id=ctx.user_id,
            closed_by_id=None,
        )
        ctx.session.add(declared_state)
        await ctx.session.flush()

        reconcile_outcome = await reconcile_worker_shift_state(
            ctx.session,
            ctx.workspace_id,
            user_id,
            now,
        )
        if reconcile_outcome.state is None:
            raise RuntimeError("Declared state reconciliation requires an open shift.")

        logger.info(
            "worker_shift.declared_state_opened | "
            "workspace_id=%s user_id=%s actor_id=%s declared_record_id=%s "
            "switched_from_id=%s paused_steps=%s",
            ctx.workspace_id,
            user_id,
            ctx.user_id,
            declared_state.client_id,
            switched_from_id,
            len(open_working_rows),
        )

    await emit_worker_shift_state(ctx.session, ctx.workspace_id, user_id)
    # A manager can declare on a worker's behalf, and declaring auto-pauses their steps.
    # Without this the worker's device keeps rendering those steps as working.
    await emit_steps_paused(
        ctx.workspace_id,
        [step.client_id for _, step, _ in open_working_rows],
    )

    return {
        "declared_state": serialize_declared_state(declared_state, pause_reason),
        "shift_state": reconcile_outcome.state.value,
        "paused_steps": len(open_working_rows),
    }
