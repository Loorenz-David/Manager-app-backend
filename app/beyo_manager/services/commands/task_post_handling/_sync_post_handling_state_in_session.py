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


async def _sync_post_handling_state_in_session(
    session: AsyncSession,
    task_id: str,
    *,
    workspace_id: str,
    now: datetime,
    user_id: str,
    username_snapshot: str | None = None,
) -> bool:
    task = (
        await session.execute(
            select(Task).where(
                Task.workspace_id == workspace_id,
                Task.client_id == task_id,
                Task.is_deleted.is_(False),
            )
        )
    ).scalar_one_or_none()
    if task is None:
        return False

    new_state = evaluate_post_handling_state(task)
    if new_state is None:
        return False

    instance = (
        await session.execute(
            select(TaskPostHandling).where(
                TaskPostHandling.workspace_id == workspace_id,
                TaskPostHandling.task_id == task_id,
                TaskPostHandling.state != TaskPostHandlingStateEnum.COMPLETED,
            )
        )
    ).scalar_one_or_none()
    if instance is None or instance.state == new_state:
        return False

    old_state = instance.state
    instance.state = new_state
    instance.updated_at = now
    await session.flush()

    await _create_history_record_in_session(
        session=session,
        entity_type=HistoryRecordEntityTypeEnum.TASK_POST_HANDLING,
        entity_client_id=instance.client_id,
        change_type=HistoryRecordChangeTypeEnum.UPDATED,
        description=f"Post-handling state changed from {old_state.value} to {new_state.value}",
        field_name="state",
        from_value={"state": old_state.value},
        to_value={"state": new_state.value},
        created_by_id=user_id,
        username_snapshot=username_snapshot,
    )
    return True
