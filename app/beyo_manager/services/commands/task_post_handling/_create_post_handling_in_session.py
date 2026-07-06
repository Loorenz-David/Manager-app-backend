from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks._post_handling_state_evaluator import evaluate_post_handling_state
from beyo_manager.domain.tasks.enums import TaskPostHandlingStateEnum
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_post_handling import TaskPostHandling
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)


async def _create_post_handling_in_session(
    session: AsyncSession,
    task: Task,
    *,
    workspace_id: str,
    now: datetime,
    user_id: str,
    username_snapshot: str | None = None,
) -> TaskPostHandling | None:
    initial_state = evaluate_post_handling_state(task)
    if initial_state is None:
        return None

    existing = (
        await session.execute(
            select(TaskPostHandling).where(
                TaskPostHandling.workspace_id == workspace_id,
                TaskPostHandling.task_id == task.client_id,
                TaskPostHandling.state != TaskPostHandlingStateEnum.COMPLETED,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return None

    instance = TaskPostHandling(
        workspace_id=workspace_id,
        task_id=task.client_id,
        state=initial_state,
        created_at=now,
    )
    session.add(instance)
    await session.flush()

    await _create_history_record_in_session(
        session=session,
        entity_type=HistoryRecordEntityTypeEnum.TASK_POST_HANDLING,
        entity_client_id=instance.client_id,
        change_type=HistoryRecordChangeTypeEnum.CREATED,
        description=f"Post-handling record created with state {initial_state.value}",
        field_name="state",
        from_value=None,
        to_value={"state": initial_state.value},
        created_by_id=user_id,
        username_snapshot=username_snapshot,
    )

    return instance
