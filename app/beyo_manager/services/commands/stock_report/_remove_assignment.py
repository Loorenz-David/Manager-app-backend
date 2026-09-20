from beyo_manager.services.commands.stock_report._move_assignment import (
    ASSIGNMENT_DELETE,
    move_assignment,
)
from beyo_manager.services.commands.stock_report._task_flag import (
    recompute_task_stock_flag,
)


async def remove_assignment(session, assignment, *, workspace_id, actor_user_id, now, trigger):
    """`move_assignment(..., DELETE)` then the MC-15 task-flag recompute."""
    events = await move_assignment(
        session,
        assignment,
        ASSIGNMENT_DELETE,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        now=now,
        trigger=trigger,
    )
    await recompute_task_stock_flag(session, workspace_id, assignment.task_id)
    return events
