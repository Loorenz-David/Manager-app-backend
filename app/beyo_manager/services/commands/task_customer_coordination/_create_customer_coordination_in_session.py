from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.enums import (
    TaskCustomerCoordinationStateEnum,
    TaskReturnSourceEnum,
    TaskTypeEnum,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)


async def _create_customer_coordination_in_session(
    session: AsyncSession,
    task: Task,
    *,
    workspace_id: str,
    now: datetime,
    user_id: str,
    username_snapshot: str | None = None,
) -> TaskCustomerCoordination | None:
    is_pre_order = task.task_type == TaskTypeEnum.PRE_ORDER
    is_non_store_return = (
        task.task_type == TaskTypeEnum.RETURN
        and task.return_source != TaskReturnSourceEnum.STORE_RETURN
    )
    if not is_pre_order and not is_non_store_return:
        return None

    existing = (
        await session.execute(
            select(TaskCustomerCoordination).where(
                TaskCustomerCoordination.workspace_id == workspace_id,
                TaskCustomerCoordination.task_id == task.client_id,
                TaskCustomerCoordination.state != TaskCustomerCoordinationStateEnum.COMPLETED,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return None

    instance = TaskCustomerCoordination(
        workspace_id=workspace_id,
        task_id=task.client_id,
        state=TaskCustomerCoordinationStateEnum.PENDING,
        created_at=now,
    )
    session.add(instance)
    await session.flush()

    await _create_history_record_in_session(
        session=session,
        entity_type=HistoryRecordEntityTypeEnum.TASK_CUSTOMER_COORDINATION,
        entity_client_id=instance.client_id,
        change_type=HistoryRecordChangeTypeEnum.CREATED,
        description="Customer coordination record created with state pending",
        field_name="state",
        from_value=None,
        to_value={"state": TaskCustomerCoordinationStateEnum.PENDING.value},
        created_by_id=user_id,
        username_snapshot=username_snapshot,
    )

    return instance
