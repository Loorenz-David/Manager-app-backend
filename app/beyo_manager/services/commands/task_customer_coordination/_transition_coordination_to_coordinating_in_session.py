from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.enums import TaskCustomerCoordinationStateEnum
from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)


async def _transition_coordination_to_coordinating_in_session(
    session: AsyncSession,
    coordinations: list[TaskCustomerCoordination],
    *,
    now: datetime,
    user_id: str | None,
    username_snapshot: str | None = None,
) -> list[TaskCustomerCoordination]:
    transitioned: list[TaskCustomerCoordination] = []

    for coordination in coordinations:
        if coordination.state != TaskCustomerCoordinationStateEnum.PENDING:
            continue

        old_state = coordination.state
        coordination.state = TaskCustomerCoordinationStateEnum.COORDINATING
        coordination.updated_at = now

        await _create_history_record_in_session(
            session=session,
            entity_type=HistoryRecordEntityTypeEnum.TASK_CUSTOMER_COORDINATION,
            entity_client_id=coordination.client_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=f"Customer coordination transitioned to coordinating (from {old_state.value})",
            field_name="state",
            from_value={"state": old_state.value},
            to_value={"state": TaskCustomerCoordinationStateEnum.COORDINATING.value},
            created_by_id=user_id,
            username_snapshot=username_snapshot,
        )
        transitioned.append(coordination)

    return transitioned
