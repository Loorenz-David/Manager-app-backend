from sqlalchemy import and_, case, select

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.working_sections.step_record_payload import (
    build_step_record_payload,
    load_step_with_latest_record,
)

_ACTIVE_STATES = [
    TaskStepStateEnum.WORKING,
    TaskStepStateEnum.PAUSED,
    TaskStepStateEnum.ENDED_SHIFT,
]

# 4-tier priority: open WORKING (0) > open PAUSED/ENDED_SHIFT (1) > closed WORKING (2) > closed PAUSED/ENDED_SHIFT (3)
_ACTIVE_RECORD_PRIORITY = case(
    (and_(StepStateRecord.state == TaskStepStateEnum.WORKING, StepStateRecord.exited_at.is_(None)), 0),
    (StepStateRecord.exited_at.is_(None), 1),
    (StepStateRecord.state == TaskStepStateEnum.WORKING, 2),
    else_=3,
)


async def get_user_last_active_step_record(ctx: ServiceContext) -> dict:
    # 1. Find the step_id of the user's most relevant active record (the resume-card primary)
    step_id_result = await ctx.session.execute(
        select(StepStateRecord.step_id)
        .join(
            TaskStep,
            and_(
                TaskStep.client_id == StepStateRecord.step_id,
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.is_deleted.is_(False),
            ),
        )
        .join(
            Task,
            and_(
                Task.client_id == TaskStep.task_id,
                Task.workspace_id == ctx.workspace_id,
                Task.is_deleted.is_(False),
            ),
        )
        .where(
            StepStateRecord.created_by_id == ctx.user_id,
            StepStateRecord.state.in_(_ACTIVE_STATES),
        )
        .order_by(_ACTIVE_RECORD_PRIORITY.asc(), StepStateRecord.created_at.desc())
        .limit(1)
    )
    step_id = step_id_result.scalar_one_or_none()
    if step_id is None:
        return {"user_last_active_step_record": None, "active_batch_steps": None}

    # 2. Load the primary TaskStep with its latest state record
    primary_step = await load_step_with_latest_record(ctx, step_id)
    if primary_step is None:
        return {"user_last_active_step_record": None, "active_batch_steps": None}

    primary_payload = await build_step_record_payload(ctx, primary_step)

    # 3. If the primary step is batch-capable, surface the user's whole *open* active batch group.
    #    "Active batch group" = the user's batch steps that currently have an open active record
    #    (WORKING/PAUSED/ENDED_SHIFT, exited_at IS NULL). Non-batch primaries keep the single-step
    #    behavior untouched (active_batch_steps stays null).
    #    NOTE: this assembles per step; the active batch set is expected to be small (a worker's
    #    concurrently-open batch steps). If that set can grow large, batch-load the per-step data.
    active_batch_steps: list[dict] | None = None
    if primary_step.allows_batch_working:
        open_batch_rows = await ctx.session.execute(
            select(StepStateRecord.step_id)
            .join(
                TaskStep,
                and_(
                    TaskStep.client_id == StepStateRecord.step_id,
                    TaskStep.workspace_id == ctx.workspace_id,
                    TaskStep.is_deleted.is_(False),
                    TaskStep.allows_batch_working.is_(True),
                ),
            )
            .join(
                Task,
                and_(
                    Task.client_id == TaskStep.task_id,
                    Task.workspace_id == ctx.workspace_id,
                    Task.is_deleted.is_(False),
                ),
            )
            .where(
                StepStateRecord.created_by_id == ctx.user_id,
                StepStateRecord.state.in_(_ACTIVE_STATES),
                StepStateRecord.exited_at.is_(None),
            )
            .order_by(StepStateRecord.entered_at.desc())
        )
        # Distinct, order-preserving (one open active record per step under the one-active invariant).
        ordered_step_ids: list[str] = []
        seen: set[str] = set()
        for (sid,) in open_batch_rows.all():
            if sid not in seen:
                seen.add(sid)
                ordered_step_ids.append(sid)

        if ordered_step_ids:
            payloads: list[dict] = []
            for sid in ordered_step_ids:
                if sid == primary_step.client_id:
                    payloads.append(primary_payload)
                    continue
                batch_step = await load_step_with_latest_record(ctx, sid)
                if batch_step is not None:
                    payloads.append(await build_step_record_payload(ctx, batch_step))
            active_batch_steps = payloads

    return {
        "user_last_active_step_record": primary_payload,
        "active_batch_steps": active_batch_steps,
    }
