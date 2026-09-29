"""A queued task id must point to a committed, claimable task row."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import asyncpg
import pytest
from redis.exceptions import ConnectionError
from sqlalchemy import select

from beyo_manager.config import settings
from beyo_manager.domain.execution.enums import ExecutionTaskStateEnum, TaskType
from beyo_manager.models.tables.execution.execution_task import ExecutionTask
from beyo_manager.services.infra.execution.task_factory import create_instant_task
from beyo_manager.services.infra.execution.task_router import (
    STUCK_PENDING_MINUTES,
    _recover_stuck_pending_tasks,
    _route_open_tasks,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


def _committed_state(task_id: str) -> str | None:
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    async def read():
        conn = await asyncpg.connect(dsn)
        try:
            return await conn.fetchval(
                "SELECT state::text FROM execution_tasks WHERE client_id = $1", task_id
            )
        finally:
            await conn.close()

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(read())).result(timeout=10)


class _CommittedStateRedis:
    """Record what a worker's independent database connection sees at each push."""

    def __init__(self):
        self.pushed = []
        self.state_at_push = {}

    def rpush(self, name, value):
        self.pushed.append((name, value))
        self.state_at_push[value] = _committed_state(value)

    def llen(self, name):
        return sum(1 for queue, _ in self.pushed if queue == name)


class _FailingRedis:
    def rpush(self, name, value):
        raise ConnectionError("down")

    def llen(self, name):
        return 0


async def _task(session, task_id: str) -> ExecutionTask:
    return await session.scalar(
        select(ExecutionTask)
        .where(ExecutionTask.client_id == task_id)
        .execution_options(populate_existing=True)
    )


async def _open_task(session) -> str:
    task = await create_instant_task(
        session=session, task_type=TaskType.CREATE_NOTIFICATIONS, payload={}
    )
    task.state = ExecutionTaskStateEnum.OPEN
    await session.commit()
    return task.client_id


async def test_a_task_is_committed_pending_before_its_id_reaches_redis(db_session, monkeypatch):
    monkeypatch.setattr(settings, "outbound_integrations_enabled", True)
    task_id = await _open_task(db_session)
    redis = _CommittedStateRedis()

    for _ in range(20):
        await _route_open_tasks(redis)
        if ("queue:notifications", task_id) in redis.pushed:
            break

    assert ("queue:notifications", task_id) in redis.pushed
    assert redis.state_at_push[task_id] == ExecutionTaskStateEnum.PENDING.value


async def test_a_push_that_fails_after_the_commit_is_recovered_by_stuck_pending(
    db_session, monkeypatch
):
    monkeypatch.setattr(settings, "outbound_integrations_enabled", True)
    task_id = await _open_task(db_session)
    redis = _FailingRedis()

    for _ in range(20):
        try:
            await _route_open_tasks(redis)
        except ConnectionError:
            pass
        task = await _task(db_session, task_id)
        await db_session.commit()
        if task.state is not ExecutionTaskStateEnum.OPEN:
            break

    assert task.state is ExecutionTaskStateEnum.PENDING
    assert task.locked_at is not None

    task.locked_at = datetime.now(timezone.utc) - timedelta(minutes=STUCK_PENDING_MINUTES + 1)
    await db_session.commit()
    for _ in range(20):
        await _recover_stuck_pending_tasks()
        task = await _task(db_session, task_id)
        await db_session.commit()
        if task.state is ExecutionTaskStateEnum.OPEN:
            break

    assert task.state is ExecutionTaskStateEnum.OPEN
