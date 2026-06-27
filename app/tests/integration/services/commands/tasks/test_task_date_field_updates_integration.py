from __future__ import annotations

import itertools
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.history.history_record import HistoryRecord
from beyo_manager.models.tables.history.history_record_link import HistoryRecordLink
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.tasks.update_task_ready_by_at import update_task_ready_by_at
from beyo_manager.services.commands.tasks.update_task_schedule import update_task_schedule
from beyo_manager.services.context import ServiceContext


def _ctx(db_session, *, workspace_id: str, user_id: str, incoming_data: dict) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "manager",
            "username": "tester",
        },
        incoming_data=incoming_data,
        session=db_session,
    )


async def _seed_workspace_user(db_session) -> tuple[Workspace, User]:
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    return workspace, user


_scalar_id_counter = itertools.count(1)


async def _seed_task(
    db_session,
    *,
    workspace_id: str,
    user_id: str,
    state: TaskStateEnum = TaskStateEnum.ASSIGNED,
) -> Task:
    suffix = uuid4().hex[:8]
    task = Task(
        client_id=f"tsk_{suffix}",
        workspace_id=workspace_id,
        task_scalar_id=next(_scalar_id_counter),
        task_type=TaskTypeEnum.INTERNAL,
        state=state,
        created_by_id=user_id,
    )
    db_session.add(task)
    await db_session.flush()
    return task


@pytest.mark.integration
async def test_update_task_ready_by_at_updates_history_and_event(db_session, monkeypatch):
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    dispatched_events = []
    ready_by_at = datetime(2026, 6, 25, 12, 30, tzinfo=timezone.utc)

    async def _fake_dispatch(events):
        dispatched_events.extend(events)
        return None

    monkeypatch.setattr(
        "beyo_manager.services.commands.tasks.update_task_ready_by_at.event_bus.dispatch",
        _fake_dispatch,
    )

    result = await update_task_ready_by_at(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"client_id": task.client_id, "ready_by_at": ready_by_at.isoformat()},
        )
    )

    await db_session.refresh(task)
    history_rows = (
        await db_session.execute(
            select(HistoryRecord, HistoryRecordLink)
            .join(HistoryRecordLink, HistoryRecordLink.history_record_id == HistoryRecord.client_id)
            .where(
                HistoryRecordLink.entity_type == HistoryRecordEntityTypeEnum.TASK,
                HistoryRecordLink.entity_client_id == task.client_id,
                HistoryRecord.change_type == HistoryRecordChangeTypeEnum.UPDATED,
            )
        )
    ).all()

    assert result == {"client_id": task.client_id}
    assert task.ready_by_at == ready_by_at
    assert len(history_rows) == 1
    assert dispatched_events[0].event_name == "task:updated"
    assert dispatched_events[0].client_id == task.client_id


@pytest.mark.integration
async def test_update_task_schedule_rejects_invalid_order_and_leaves_row_unchanged(db_session, monkeypatch):
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace_id=workspace.client_id, user_id=user.client_id)
    initial_start = datetime(2026, 6, 25, 9, 0, tzinfo=timezone.utc)
    initial_end = datetime(2026, 6, 25, 10, 0, tzinfo=timezone.utc)
    task.scheduled_start_at = initial_start
    task.scheduled_end_at = initial_end
    await db_session.flush()
    dispatched_events = []

    async def _fake_dispatch(events):
        dispatched_events.extend(events)
        return None

    monkeypatch.setattr(
        "beyo_manager.services.commands.tasks.update_task_schedule.event_bus.dispatch",
        _fake_dispatch,
    )

    with pytest.raises(ValidationError):
        await update_task_schedule(
            _ctx(
                db_session,
                workspace_id=workspace.client_id,
                user_id=user.client_id,
                incoming_data={
                    "client_id": task.client_id,
                    "scheduled_start_at": "2026-06-25T11:00:00Z",
                    "scheduled_end_at": "2026-06-25T10:00:00Z",
                },
            )
        )

    await db_session.refresh(task)
    history_count = await db_session.scalar(select(func.count()).select_from(HistoryRecord))

    assert task.scheduled_start_at == initial_start
    assert task.scheduled_end_at == initial_end
    assert history_count == 0
    assert dispatched_events == []


@pytest.mark.integration
async def test_update_task_ready_by_at_rejects_terminal_tasks(db_session, monkeypatch):
    workspace, user = await _seed_workspace_user(db_session)
    task = await _seed_task(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        state=TaskStateEnum.RESOLVED,
    )

    async def _fake_dispatch(_events):
        return None

    monkeypatch.setattr(
        "beyo_manager.services.commands.tasks.update_task_ready_by_at.event_bus.dispatch",
        _fake_dispatch,
    )

    with pytest.raises(ValidationError, match="Terminal tasks cannot be updated."):
        await update_task_ready_by_at(
            _ctx(
                db_session,
                workspace_id=workspace.client_id,
                user_id=user.client_id,
                incoming_data={"client_id": task.client_id, "ready_by_at": None},
            )
        )
