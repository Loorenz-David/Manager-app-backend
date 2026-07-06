from sqlalchemy import select

from beyo_manager.domain.tasks.serializers import serialize_task_post_handling
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_post_handling import TaskPostHandling
from beyo_manager.services.context import ServiceContext


async def list_task_post_handlings(ctx: ServiceContext) -> dict:
    task_id = ctx.incoming_data.get("task_id")

    task_result = await ctx.session.execute(
        select(Task).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id == task_id,
            Task.is_deleted.is_(False),
        )
    )
    task = task_result.scalar_one_or_none()
    if task is None:
        raise NotFound("Task not found.")

    result = await ctx.session.execute(
        select(TaskPostHandling)
        .where(
            TaskPostHandling.workspace_id == ctx.workspace_id,
            TaskPostHandling.task_id == task_id,
        )
        .order_by(TaskPostHandling.created_at.asc())
    )
    instances = result.scalars().all()
    return {"post_handling": [serialize_task_post_handling(ph) for ph in instances]}
