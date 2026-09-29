"""With OUTBOUND_INTEGRATIONS_ENABLED=false, outbound tasks end cancelled, never queued.

Staging runs the full worker set; this is what keeps it from sending email or Web
Push, or calling Shopify or Scanner. A task that is merely left unconsumed would be
re-queued every few minutes forever, so the router must close it, and a worker must
close any that were queued before the switch was turned off.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from beyo_manager.config import settings
from beyo_manager.domain.execution.enums import ExecutionTaskStateEnum, TaskType
from beyo_manager.models.tables.execution.execution_task import ExecutionTask
from beyo_manager.services.infra.execution import worker_base
from beyo_manager.services.infra.execution.outbound import OUTBOUND_DISABLED_REASON
from beyo_manager.services.infra.execution.task_factory import create_instant_task
from beyo_manager.services.infra.execution.task_router import _route_open_tasks

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


class _RecordingRedis:
    """The router's Redis seam: records `rpush`, answers `llen` for its log line."""

    def __init__(self):
        self.pushed = []

    def rpush(self, name, value):
        self.pushed.append((name, value))

    def llen(self, name):
        return sum(1 for queue, _ in self.pushed if queue == name)


async def _create(session, task_type, state=ExecutionTaskStateEnum.OPEN) -> str:
    task = await create_instant_task(session=session, task_type=task_type, payload={})
    task.state = state
    await session.commit()
    return task.client_id


async def _task(session, task_id) -> ExecutionTask:
    return await session.scalar(
        select(ExecutionTask)
        .where(ExecutionTask.client_id == task_id)
        .execution_options(populate_existing=True)
    )


async def _route_until_settled(session, task_ids) -> _RecordingRedis:
    """The router is global and batched; drive it until none of ours is OPEN."""
    redis = _RecordingRedis()
    for _ in range(20):
        await _route_open_tasks(redis)
        states = [(await _task(session, t)).state for t in task_ids]
        await session.commit()
        if ExecutionTaskStateEnum.OPEN not in states:
            break
    return redis


async def test_router_cancels_outbound_tasks_and_queues_internal_ones(db_session, monkeypatch):
    monkeypatch.setattr(settings, "outbound_integrations_enabled", False)
    push = await _create(db_session, TaskType.SEND_PUSH_NOTIFICATION)
    email = await _create(db_session, TaskType.SEND_EMAIL_MESSAGES)
    shopify = await _create(db_session, TaskType.SHOPIFY_PROCESS_PRODUCTS)
    internal = await _create(db_session, TaskType.CREATE_NOTIFICATIONS)

    redis = await _route_until_settled(db_session, [push, email, shopify, internal])

    pushed_ids = [task_id for _, task_id in redis.pushed]
    for task_id in (push, email, shopify):
        task = await _task(db_session, task_id)
        assert task.state is ExecutionTaskStateEnum.CANCEL
        assert task.last_error == OUTBOUND_DISABLED_REASON
        assert task.completed_at is not None
        assert task_id not in pushed_ids
    assert ("queue:notifications", internal) in redis.pushed
    assert (await _task(db_session, internal)).state is ExecutionTaskStateEnum.PENDING


async def test_router_queues_outbound_tasks_when_the_switch_is_on(db_session, monkeypatch):
    monkeypatch.setattr(settings, "outbound_integrations_enabled", True)
    push = await _create(db_session, TaskType.SEND_PUSH_NOTIFICATION)
    shopify = await _create(db_session, TaskType.SHOPIFY_PROCESS_PRODUCTS)

    redis = await _route_until_settled(db_session, [push, shopify])

    assert ("queue:notifications", push) in redis.pushed
    assert ("queue:shopify", shopify) in redis.pushed
    assert (await _task(db_session, push)).state is ExecutionTaskStateEnum.PENDING


async def test_worker_cancels_an_outbound_task_queued_before_the_switch_went_off(
    db_session, monkeypatch
):
    monkeypatch.setattr(settings, "outbound_integrations_enabled", False)
    task_id = await _create(
        db_session, TaskType.SEND_PUSH_NOTIFICATION, state=ExecutionTaskStateEnum.PENDING
    )

    async def _must_not_run(payload, task_id):
        raise AssertionError("an outbound handler ran while outbound integrations were off")

    await worker_base._process_task(
        task_id, "test-worker", {TaskType.SEND_PUSH_NOTIFICATION: _must_not_run}
    )

    task = await _task(db_session, task_id)
    assert task.state is ExecutionTaskStateEnum.CANCEL
    assert task.last_error == OUTBOUND_DISABLED_REASON
    assert task.worker_id is None


async def test_worker_runs_outbound_handlers_when_the_switch_is_on(db_session, monkeypatch):
    monkeypatch.setattr(settings, "outbound_integrations_enabled", True)
    task_id = await _create(
        db_session, TaskType.SEND_PUSH_NOTIFICATION, state=ExecutionTaskStateEnum.PENDING
    )
    ran = []

    async def _handler(payload, task_id):
        ran.append(task_id)

    await worker_base._process_task(
        task_id, "test-worker", {TaskType.SEND_PUSH_NOTIFICATION: _handler}
    )

    assert ran == [task_id]
    assert (await _task(db_session, task_id)).state is ExecutionTaskStateEnum.COMPLETED
