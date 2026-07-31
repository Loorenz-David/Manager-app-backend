from sqlalchemy import func, select

from beyo_manager.models.tables.tasks.task_step_acknowledgment import TaskStepAcknowledgment
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.task_step_acknowledgments._reassigned_steps_filters import (
    reassigned_steps_select_from,
    reassigned_steps_where_clauses,
)


async def count_reassigned_steps(ctx: ServiceContext) -> dict:
    stmt = reassigned_steps_select_from(
        select(
            func.count().label("total"),
            func.count()
            .filter(TaskStepAcknowledgment.acknowledged_at.is_(None))
            .label("unacknowledged"),
        ),
        ctx,
    ).where(*reassigned_steps_where_clauses(ctx))
    row = (await ctx.session.execute(stmt)).one()
    return {
        "reassigned_steps_count": {
            "total": row.total or 0,
            "unacknowledged": row.unacknowledged or 0,
        }
    }
