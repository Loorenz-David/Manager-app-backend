"""Seed helpers for the phase-4 task-economics contract tests."""

from datetime import datetime, timedelta, timezone

from tests.integration.services.queries.item_economics.test_budget_allocations_query import _seed
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep


async def seed_narrowing_history(db_session):
    """Reuse the approved economics seed and expose its objects to narrowing cases."""

    values = await _seed(db_session)
    workspace, user, section, _task, *_ = values
    now = datetime.now(timezone.utc)
    for index, seconds in enumerate((600, 900, 1200, 1500, 1800)):
        history_task = Task(
            client_id=f"tsk_narrowing_history_{workspace.client_id}_{index}",
            workspace_id=workspace.client_id,
            task_scalar_id=1000 + index,
            task_type=TaskTypeEnum.INTERNAL,
            state=TaskStateEnum.ASSIGNED,
            created_by_id=user.client_id,
        )
        history_step = TaskStep(
            client_id=f"tsp_narrowing_history_{workspace.client_id}_{index}",
            workspace_id=workspace.client_id,
            task_id=history_task.client_id,
            working_section_id=section.client_id,
            state=TaskStepStateEnum.COMPLETED,
            readiness_status=TaskStepReadinessStatusEnum.READY,
            total_dependencies=0,
            completed_dependencies=0,
            total_working_seconds=seconds,
            closed_at=now - timedelta(days=1),
            created_by_id=user.client_id,
        )
        db_session.add_all([history_task, history_step])
    await db_session.flush()
    return values
