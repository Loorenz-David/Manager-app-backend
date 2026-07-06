from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES, TERMINAL_TASK_STATES
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.commands.task_customer_coordination._create_customer_coordination_in_session import (
    _create_customer_coordination_in_session,
)
from beyo_manager.services.commands.task_post_handling._create_post_handling_in_session import (
    _create_post_handling_in_session,
)


def maybe_advance_task_to_working(
    task: Task,
    *,
    now: datetime,
    updated_by_id: str,
) -> bool:
    if task.state != TaskStateEnum.ASSIGNED:
        return False

    task.state = TaskStateEnum.WORKING
    task.updated_at = now
    task.updated_by_id = updated_by_id
    return True


async def maybe_evaluate_task_ready(
    session: AsyncSession,
    task: Task,
    *,
    workspace_id: str,
    now: datetime,
    updated_by_id: str,
) -> bool:
    if task.state in TERMINAL_TASK_STATES:
        return False
    if task.state == TaskStateEnum.READY:
        return False

    all_steps = (
        await session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == workspace_id,
                TaskStep.task_id == task.client_id,
                TaskStep.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    if not all_steps or not all(step.state in TERMINAL_STEP_STATES for step in all_steps):
        return False

    task.state = TaskStateEnum.READY
    task.updated_at = now
    task.updated_by_id = updated_by_id
    await _create_post_handling_in_session(
        session,
        task,
        workspace_id=workspace_id,
        now=now,
        user_id=updated_by_id,
    )
    await _create_customer_coordination_in_session(
        session,
        task,
        workspace_id=workspace_id,
        now=now,
        user_id=updated_by_id,
    )
    return True
