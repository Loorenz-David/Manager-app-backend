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


async def _teardown_post_handling_in_session(
    session: AsyncSession,
    task: Task,
    *,
    workspace_id: str,
    now: datetime,
    user_id: str,
    username_snapshot: str | None = None,
) -> bool:
    """Hard-delete a non-completed post-handling instance when the task's current
    type no longer supports post-handling (e.g. changed away from RETURN/PRE_ORDER).

    ``evaluate_post_handling_state`` returns ``None`` only for unsupported task
    types (supported types yield PENDING/FILLED regardless of state), so a ``None``
    result is the reliable "no longer applies" signal. Idempotent: returns False
    when post-handling still applies or no non-completed instance exists.
    """
    if evaluate_post_handling_state(task) is not None:
        return False

    instance = (
        await session.execute(
            select(TaskPostHandling).where(
                TaskPostHandling.workspace_id == workspace_id,
                TaskPostHandling.task_id == task.client_id,
                TaskPostHandling.state != TaskPostHandlingStateEnum.COMPLETED,
            )
        )
    ).scalar_one_or_none()
    if instance is None:
        return False

    removed_state = instance.state
    removed_client_id = instance.client_id

    await _create_history_record_in_session(
        session=session,
        entity_type=HistoryRecordEntityTypeEnum.TASK_POST_HANDLING,
        entity_client_id=removed_client_id,
        change_type=HistoryRecordChangeTypeEnum.DELETED,
        description=(
            f"Post-handling record removed (task no longer supports post-handling); "
            f"was {removed_state.value}"
        ),
        field_name="state",
        from_value={"state": removed_state.value},
        to_value=None,
        created_by_id=user_id,
        username_snapshot=username_snapshot,
    )

    await session.delete(instance)
    await session.flush()
    return True
