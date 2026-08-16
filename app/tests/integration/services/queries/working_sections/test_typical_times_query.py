from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete

from beyo_manager.domain.item_economics.budget_division import TYPICAL_MIN_SAMPLE_SIZE
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.working_sections.get_working_section_typical_times import get_working_section_typical_times


async def _seed_section_rows(db_session, *, values, old=False):
    token = uuid4().hex[:10]
    workspace = Workspace(client_id=f"ws_{token}", name=f"Budget {token}")
    user = User(client_id=f"usr_{token}", username=f"budget_{token}", email=f"budget_{token}@example.com", password="secret")
    section = WorkingSection(client_id=f"wsec_{token}", workspace_id=workspace.client_id, name=f"Typical {token}")
    empty = WorkingSection(client_id=f"wsec_empty_{token}", workspace_id=workspace.client_id, name=f"Empty {token}")
    db_session.add(workspace)
    await db_session.flush()
    db_session.add(user)
    await db_session.flush()
    db_session.add_all([section, empty])
    await db_session.flush()
    close_at = datetime.now(timezone.utc) - timedelta(days=100 if old else 1)
    tasks = []
    steps = []
    for index, seconds in enumerate(values):
        task = Task(
            client_id=f"tsk_{token}_{index}", workspace_id=workspace.client_id, task_scalar_id=index + 1,
            task_type=TaskTypeEnum.INTERNAL, state=TaskStateEnum.ASSIGNED, created_by_id=user.client_id,
        )
        step = TaskStep(
            client_id=f"tsp_{token}_{index}", workspace_id=workspace.client_id, task_id=task.client_id,
            working_section_id=section.client_id, working_section_name_snapshot=section.name,
            state=TaskStepStateEnum.COMPLETED, readiness_status=TaskStepReadinessStatusEnum.READY,
            total_dependencies=0, completed_dependencies=0, total_working_seconds=seconds,
            closed_at=close_at, created_by_id=user.client_id,
        )
        tasks.append(task)
        steps.append(step)
    db_session.add_all([*tasks, *steps])
    await db_session.flush()
    return workspace, user, section, empty, tasks, steps


def _ctx(db_session, workspace_id, **query):
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": "usr_test", "role_name": "worker"},
        incoming_data={}, query_params=query, session=db_session,
    )


@pytest.mark.integration
async def test_typical_query_uses_group_median_and_returns_empty_sections(db_session):
    workspace, user, section, empty, tasks, _ = await _seed_section_rows(
        db_session, values=[600, 1000, 1200, 6000, 7000]
    )
    try:
        result = await get_working_section_typical_times(_ctx(db_session, workspace.client_id))
        rows = {row["working_section_id"]: row for row in result["typical_times"]}
        assert rows[section.client_id]["typical_worker_seconds"] == 1200
        assert rows[section.client_id]["sample_count"] == TYPICAL_MIN_SAMPLE_SIZE
        assert rows[empty.client_id]["typical_worker_seconds"] is None
        assert rows[empty.client_id]["sample_count"] == 0
    finally:
        await db_session.execute(delete(TaskStep).where(TaskStep.task_id.in_([task.client_id for task in tasks])))
        await db_session.execute(delete(Task).where(Task.client_id.in_([task.client_id for task in tasks])))
        await db_session.execute(delete(WorkingSection).where(WorkingSection.client_id.in_([section.client_id, empty.client_id])))
        await db_session.execute(delete(User).where(User.client_id == user.client_id))
        await db_session.execute(delete(Workspace).where(Workspace.client_id == workspace.client_id))


@pytest.mark.integration
async def test_typical_query_applies_group_window_and_repeatable_filter(db_session):
    workspace, user, section, empty, tasks, _ = await _seed_section_rows(
        db_session, values=[600, 1000, 1200, 6000, 7000], old=True
    )
    try:
        result = await get_working_section_typical_times(
            _ctx(db_session, workspace.client_id, working_section_ids=[section.client_id])
        )
        row = result["typical_times"][0]
        assert row["working_section_id"] == section.client_id
        assert row["sample_count"] == 0
        assert row["typical_worker_seconds"] is None
        unknown = await get_working_section_typical_times(
            _ctx(db_session, workspace.client_id, working_section_ids=["wsec_unknown"])
        )
        assert unknown["typical_times"] == []
    finally:
        await db_session.execute(delete(TaskStep).where(TaskStep.task_id.in_([task.client_id for task in tasks])))
        await db_session.execute(delete(Task).where(Task.client_id.in_([task.client_id for task in tasks])))
        await db_session.execute(delete(WorkingSection).where(WorkingSection.client_id.in_([section.client_id, empty.client_id])))
        await db_session.execute(delete(User).where(User.client_id == user.client_id))
        await db_session.execute(delete(Workspace).where(Workspace.client_id == workspace.client_id))
