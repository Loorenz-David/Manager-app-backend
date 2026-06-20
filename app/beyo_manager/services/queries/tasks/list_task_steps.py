from sqlalchemy import and_, select

from beyo_manager.domain.task_steps.serializers import serialize_task_step_compact
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_task_steps(ctx: ServiceContext) -> dict:
    task_id = ctx.incoming_data.get("task_id")
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

    task_result = await ctx.session.execute(
        select(Task).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id == task_id,
            Task.is_deleted.is_(False),
        )
    )
    if task_result.scalar_one_or_none() is None:
        raise NotFound("Task not found.")

    stmt = (
        select(TaskStep, WorkingSection)
        .join(
            WorkingSection,
            and_(
                WorkingSection.workspace_id == ctx.workspace_id,
                WorkingSection.client_id == TaskStep.working_section_id,
                WorkingSection.is_deleted.is_(False),
            ),
            isouter=True,
        )
        .where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.task_id == task_id,
            TaskStep.is_deleted.is_(False),
        )
        .order_by(
            TaskStep.sequence_order.asc().nullslast(),
            TaskStep.created_at.asc(),
        )
        .offset(offset)
        .limit(limit + 1)
    )

    rows = (await ctx.session.execute(stmt)).all()
    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "steps_pagination": {
            "items": [
                serialize_task_step_compact(step, working_section)
                for step, working_section in page
            ],
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }
