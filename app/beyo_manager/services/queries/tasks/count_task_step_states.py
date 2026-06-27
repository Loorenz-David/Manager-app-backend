from sqlalchemy import func, select

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.context import ServiceContext


async def count_task_step_states(ctx: ServiceContext) -> dict:
    task_id = ctx.incoming_data.get("task_id")

    task_result = await ctx.session.execute(
        select(Task).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id == task_id,
            Task.is_deleted.is_(False),
        )
    )
    if task_result.scalar_one_or_none() is None:
        raise NotFound("Task not found.")

    rows = (
        await ctx.session.execute(
            select(TaskStep.state, func.count(TaskStep.client_id))
            .where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.task_id == task_id,
                TaskStep.is_deleted.is_(False),
            )
            .group_by(TaskStep.state)
        )
    ).all()

    raw = {state.value: count for state, count in rows}
    counts_by_state = {state.value: raw.get(state.value, 0) for state in TaskStepStateEnum}
    return {"counts_by_state": counts_by_state}
