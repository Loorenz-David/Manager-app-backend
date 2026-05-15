from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.execution.enums import EventTaskOriginSourceEnum, ExecutionTaskStateEnum, TaskType
from beyo_manager.models.tables.execution.execution_payload import ExecutionPayload
from beyo_manager.models.tables.execution.execution_task import ExecutionTask


async def create_execution_task(
    session: AsyncSession,
    task_type: TaskType,
    payload: dict,
    origin_source: EventTaskOriginSourceEnum,
    origin_id: str | None = None,
    scheduled_at: datetime | None = None,
    event_client_id: str | None = None,
    max_try: int = 3,
) -> ExecutionTask:
    """Single entry point for creating an ExecutionTask + ExecutionPayload pair.
    Always call inside an open transaction so task creation is atomic with the
    domain write that triggered it.
    """
    now = datetime.now(timezone.utc)
    task = ExecutionTask(
        task_type=task_type,
        state=ExecutionTaskStateEnum.OPEN,
        max_try=max_try,
        created_at=now,
        scheduled_at=scheduled_at,
    )
    session.add(task)
    await session.flush()  # assign client_id

    session.add(ExecutionPayload(
        origin_source=origin_source,
        origin_id=origin_id,
        event_client_id=event_client_id,
        payload=payload,
        execution_task_id=task.client_id,
        created_at=now,
    ))
    return task


async def create_instant_task(
    session: AsyncSession,
    task_type: TaskType,
    payload: dict,
    event_client_id: str | None = None,
    max_try: int = 3,
) -> ExecutionTask:
    """Convenience wrapper for commands that trigger instant (non-scheduled) tasks."""
    return await create_execution_task(
        session=session,
        task_type=task_type,
        payload=payload,
        origin_source=EventTaskOriginSourceEnum.INSTANT,
        event_client_id=event_client_id,
        max_try=max_try,
    )
