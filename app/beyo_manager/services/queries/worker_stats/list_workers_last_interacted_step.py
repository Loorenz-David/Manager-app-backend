from collections import Counter, defaultdict

from sqlalchemy import func, select

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.users.serializers import serialize_user_worker_stat
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.working_sections.step_record_payload import (
    build_step_record_payload,
    load_step_with_latest_record,
)
from beyo_manager.services.queries.worker_stats._roster import load_worker_page, resolve_work_date


async def list_workers_last_interacted_step(ctx: ServiceContext) -> dict:
    # This endpoint is a point-in-time snapshot (always the latest step) and does NOT
    # scope by date. `work_date` is accepted only to keep the pre-split validation
    # contract (a garbage value still 422s); it has no effect on the response.
    if ctx.query_params.get("work_date"):
        resolve_work_date(ctx.query_params["work_date"])

    workers, workers_pagination = await load_worker_page(
        ctx, roles=(RoleNameEnum.WORKER, RoleNameEnum.MANAGER)
    )
    worker_ids = [user.client_id for user in workers]

    step_rows_by_worker: dict[str, list] = defaultdict(list)
    if worker_ids:
        latest_per_step = (
            select(
                StepStateRecord.created_by_id.label("worker_id"),
                StepStateRecord.step_id.label("step_id"),
                StepStateRecord.entered_at.label("entered_at"),
                StepStateRecord.created_at.label("record_created_at"),
                StepStateRecord.state.label("state"),
                TaskStep.allows_batch_working.label("allows_batch_working"),
                func.row_number()
                .over(
                    partition_by=(StepStateRecord.created_by_id, StepStateRecord.step_id),
                    order_by=(
                        StepStateRecord.entered_at.desc(),
                        StepStateRecord.created_at.desc(),
                        StepStateRecord.client_id.desc(),
                    ),
                )
                .label("step_row_number"),
            )
            .join(TaskStep, TaskStep.client_id == StepStateRecord.step_id)
            .join(Task, Task.client_id == TaskStep.task_id)
            .where(
                StepStateRecord.workspace_id == ctx.workspace_id,
                StepStateRecord.created_by_id.in_(worker_ids),
                StepStateRecord.is_deleted.is_(False),
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.is_deleted.is_(False),
                Task.workspace_id == ctx.workspace_id,
                Task.is_deleted.is_(False),
            )
            .cte("worker_latest_record_per_step")
        )
        latest_records = (
            select(
                latest_per_step.c.worker_id,
                latest_per_step.c.step_id,
                latest_per_step.c.entered_at,
                latest_per_step.c.record_created_at,
                latest_per_step.c.state,
                latest_per_step.c.allows_batch_working,
                func.rank()
                .over(
                    partition_by=latest_per_step.c.worker_id,
                    order_by=latest_per_step.c.entered_at.desc(),
                )
                .label("cohort_rank"),
            )
            .where(latest_per_step.c.step_row_number == 1)
            .subquery("worker_last_step_cohort_ranked")
        )
        step_rows_result = await ctx.session.execute(
            select(latest_records)
            .where(latest_records.c.cohort_rank == 1)
            .order_by(
                latest_records.c.worker_id,
                latest_records.c.record_created_at.desc(),
                latest_records.c.step_id.asc(),
            )
        )
        for row in step_rows_result:
            step_rows_by_worker[row.worker_id].append(row)

    worker_results: list[dict] = []
    for user in workers:
        cohort = sorted(
            step_rows_by_worker.get(user.client_id, []),
            key=lambda row: (-row.record_created_at.timestamp(), row.step_id),
        )
        payload = None
        batch = None
        if cohort:
            state_order = [row.state for row in cohort]
            state_counts = Counter(state_order)
            winning_state = next(
                state for state in state_order if state_counts[state] == max(state_counts.values())
            )
            representative = next(row for row in cohort if row.state == winning_state)
            step = await load_step_with_latest_record(ctx, representative.step_id)
            if step is not None:
                payload = await build_step_record_payload(
                    ctx, step, include_cases_summary=False
                )

            if representative.allows_batch_working and len(cohort) >= 2:
                state_value = getattr(representative.state, "value", representative.state)
                batch = {
                    "count": len(cohort),
                    "step_ids": sorted(row.step_id for row in cohort),
                    "shared_entered_at": representative.entered_at.isoformat(),
                    "state": state_value,
                }

        worker_results.append(
            {
                "user": serialize_user_worker_stat(user),
                "last_interacted_step": payload,
                "batch": batch,
            }
        )

    return {"workers": worker_results, "workers_pagination": workers_pagination}
