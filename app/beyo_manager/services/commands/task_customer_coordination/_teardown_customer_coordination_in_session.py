from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.enums import TaskCustomerCoordinationStateEnum
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.task_customer_coordination._create_customer_coordination_in_session import (
    task_requires_customer_coordination,
)


async def _teardown_customer_coordination_in_session(
    session: AsyncSession,
    task: Task,
    *,
    workspace_id: str,
    now: datetime,
    user_id: str,
    username_snapshot: str | None = None,
) -> bool:
    """Hard-delete a non-completed customer-coordination instance when the task's
    current type/source no longer calls for one (e.g. changed away from PRE_ORDER).

    Idempotent: returns False (no-op) when the task still requires coordination or
    when no non-completed instance exists. A history record snapshots the removal.
    """
    if task_requires_customer_coordination(task):
        return False

    instance = (
        await session.execute(
            select(TaskCustomerCoordination).where(
                TaskCustomerCoordination.workspace_id == workspace_id,
                TaskCustomerCoordination.task_id == task.client_id,
                TaskCustomerCoordination.state != TaskCustomerCoordinationStateEnum.COMPLETED,
            )
        )
    ).scalar_one_or_none()
    if instance is None:
        return False

    removed_state = instance.state
    removed_client_id = instance.client_id

    await _create_history_record_in_session(
        session=session,
        entity_type=HistoryRecordEntityTypeEnum.TASK_CUSTOMER_COORDINATION,
        entity_client_id=removed_client_id,
        change_type=HistoryRecordChangeTypeEnum.DELETED,
        description=(
            f"Customer coordination record removed (task no longer requires it); "
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
