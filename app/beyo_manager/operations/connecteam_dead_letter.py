from __future__ import annotations

import asyncio

from sqlalchemy import select

from beyo_manager.domain.execution.enums import ExecutionTaskStateEnum, TaskType
from beyo_manager.models.database import get_db_session, init_db
from beyo_manager.models.tables.execution.execution_task import ExecutionTask


async def _list(raw: bool = False) -> list[dict]:
    await init_db()
    async for session in get_db_session():
        rows = (
            await session.execute(
                select(ExecutionTask)
                .where(
                    ExecutionTask.task_type == TaskType.CONNECTEAM_PROCESS_TIME_ACTIVITY,
                    ExecutionTask.state == ExecutionTaskStateEnum.FAIL,
                )
                .order_by(ExecutionTask.created_at.asc())
            )
        ).scalars().all()
        result = []
        for task in rows:
            payload = task.payload.payload if task.payload else {}
            item = {
                "task_id": task.client_id,
                "event_key": payload.get("event_key"),
                "last_error": (task.last_error or "")[:200],
                "created_at": task.created_at.isoformat(),
            }
            if raw:
                item["payload"] = payload
            result.append(item)
        return result
    return []


def list_dead_letters(raw: bool = False) -> None:
    for item in asyncio.run(_list(raw=raw)):
        print(item)


async def _requeue(task_id: str) -> bool:
    await init_db()
    async for session in get_db_session():
        task = await session.scalar(
            select(ExecutionTask).where(
                ExecutionTask.client_id == task_id,
                ExecutionTask.task_type == TaskType.CONNECTEAM_PROCESS_TIME_ACTIVITY,
                ExecutionTask.state == ExecutionTaskStateEnum.FAIL,
            )
        )
        if task is None:
            return False
        task.state = ExecutionTaskStateEnum.OPEN
        task.try_count = 0
        task.next_retry_at = None
        await session.commit()
        return True
    return False


def requeue_dead_letter(task_id: str) -> None:
    if not asyncio.run(_requeue(task_id)):
        raise RuntimeError("Connecteam dead-letter task not found.")


async def _purge(task_id: str) -> bool:
    await init_db()
    async for session in get_db_session():
        task = await session.scalar(
            select(ExecutionTask).where(
                ExecutionTask.client_id == task_id,
                ExecutionTask.task_type == TaskType.CONNECTEAM_PROCESS_TIME_ACTIVITY,
                ExecutionTask.state == ExecutionTaskStateEnum.FAIL,
            )
        )
        if task is None:
            return False
        task.state = ExecutionTaskStateEnum.CANCEL
        await session.commit()
        return True
    return False


def purge_dead_letter(task_id: str, confirm: bool = False) -> None:
    if not confirm:
        raise RuntimeError("Pass --confirm to mark a Connecteam dead-letter task cancelled.")
    if not asyncio.run(_purge(task_id)):
        raise RuntimeError("Connecteam dead-letter task not found.")

