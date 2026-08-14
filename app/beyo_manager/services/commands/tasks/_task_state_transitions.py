from datetime import datetime
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES, TERMINAL_TASK_STATES
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.item_cost_result import ItemCostResultPayload
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.commands.tasks._reconcile_task_side_effects import (
    reconcile_task_side_effects,
)
from beyo_manager.services.infra.execution.task_factory import create_instant_task


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


async def maybe_reopen_task_to_working(
    session: AsyncSession,
    task: Task,
    *,
    workspace_id: str,
    now: datetime,
    updated_by_id: str,
) -> bool:
    """Move a ready task back into active work when new work is added.

    This is intentionally a separate transition from ``ASSIGNED -> WORKING``:
    adding a new task step reopens a task that had already reached ``READY``.
    The result task is created here so every sanctioned reopen inherits the
    boundary emission while retaining the caller's transaction.
    """
    if task.state != TaskStateEnum.READY:
        return False

    task.state = TaskStateEnum.WORKING
    task.updated_at = now
    task.updated_by_id = updated_by_id
    await create_instant_task(
        session=session,
        task_type=TaskType.PROCESS_ITEM_COST_RESULT,
        payload=asdict(ItemCostResultPayload(workspace_id=workspace_id, task_id=task.client_id)),
    )
    return True


async def maybe_evaluate_task_ready(
    session: AsyncSession,
    task: Task,
    *,
    workspace_id: str,
    now: datetime,
    updated_by_id: str,
    allow_stepless: bool = False,
) -> bool:
    """Flip a task to ``READY`` when every step has reached a terminal state.

    This is the ONLY way into ``READY``: it owns the ``reconcile_task_side_effects``
    call that creates the post-handling and customer-coordination instances, so a
    caller that writes ``task.state = READY`` itself silently skips them.

    ``allow_stepless`` lets a task with no steps at all become ready. Organic readiness
    is "all the work finished", which a stepless task can never satisfy — so this stays
    off by default and is opted into only by ``force_task_ready``, where a manager has
    explicitly declared a step-free task done. The side effects still run either way,
    which is the whole reason that command routes through here.
    """
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
    if all_steps:
        if not all(step.state in TERMINAL_STEP_STATES for step in all_steps):
            return False
    elif not allow_stepless:
        return False

    task.state = TaskStateEnum.READY
    task.updated_at = now
    task.updated_by_id = updated_by_id
    await reconcile_task_side_effects(
        session,
        task,
        workspace_id=workspace_id,
        now=now,
        user_id=updated_by_id,
    )
    await create_instant_task(
        session=session,
        task_type=TaskType.PROCESS_ITEM_COST_RESULT,
        payload=asdict(ItemCostResultPayload(workspace_id=workspace_id, task_id=task.client_id)),
    )
    return True
