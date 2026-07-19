from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.execution.payloads.step_transition import StepTransitionPayload
from beyo_manager.domain.task_steps.enums import StepEventReasonEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.tasks.analytics.process_step_transition import (
    handle_process_step_transition,
)


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _seed_environment(db_session) -> tuple[Workspace, User, Task, WorkingSection]:
    suffix = uuid4().hex
    workspace = Workspace(name=f"shift-hook-{suffix}")
    worker = User(
        username=f"shift-hook-{suffix}",
        email=f"shift-hook-{suffix}@example.com",
        password="test-password-hash",
    )
    db_session.add_all([workspace, worker])
    await db_session.flush()
    task = Task(
        workspace_id=workspace.client_id,
        task_scalar_id=int(suffix[:7], 16),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.WORKING,
        created_by_id=worker.client_id,
    )
    section = WorkingSection(
        workspace_id=workspace.client_id,
        name=f"shift-hook-section-{suffix}",
        created_by_id=worker.client_id,
    )
    db_session.add_all([task, section])
    await db_session.flush()
    return workspace, worker, task, section


async def _seed_post_transition_step(
    db_session,
    *,
    workspace: Workspace,
    worker: User,
    task: Task,
    section: WorkingSection,
    closing_state: TaskStepStateEnum,
    new_state: TaskStepStateEnum,
    transitioned_at: datetime,
    reason: StepEventReasonEnum | None = None,
) -> dict:
    step = TaskStep(
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        state=new_state,
        working_section_id=section.client_id,
        working_section_name_snapshot=section.name,
        assigned_worker_id=worker.client_id,
        created_by_id=worker.client_id,
        allows_batch_working=True,
    )
    db_session.add(step)
    await db_session.flush()
    closing_record = StepStateRecord(
        workspace_id=workspace.client_id,
        step_id=step.client_id,
        state=closing_state,
        entered_at=transitioned_at - timedelta(minutes=30),
        exited_at=transitioned_at,
        created_by_id=worker.client_id,
        credited_user_id=worker.client_id,
    )
    new_record = StepStateRecord(
        workspace_id=workspace.client_id,
        step_id=step.client_id,
        state=new_state,
        reason=reason,
        entered_at=transitioned_at,
        exited_at=None,
        created_by_id=worker.client_id,
        credited_user_id=worker.client_id,
    )
    db_session.add_all([closing_record, new_record])
    await db_session.flush()
    step.latest_state_record_id = new_record.client_id
    return asdict(
        StepTransitionPayload(
            step_id=step.client_id,
            task_id=task.client_id,
            workspace_id=workspace.client_id,
            closing_record_id=closing_record.client_id,
            closing_state=closing_state.value,
            new_state=new_state.value,
            performed_by_user_id=worker.client_id,
            credited_user_id=worker.client_id,
            assigned_worker_id=worker.client_id,
            working_section_id=section.client_id,
            working_section_name_snapshot=section.name,
            entered_at=closing_record.entered_at.isoformat(),
            exited_at=transitioned_at.isoformat(),
            step_task_id=task.client_id,
        )
    )


def _seed_open_shift(
    db_session,
    *,
    workspace_id: str,
    user_id: str,
    state: UserShiftStateEnum,
    started_at: datetime,
) -> None:
    db_session.add_all(
        [
            UserShiftStateRecord(
                workspace_id=workspace_id,
                user_id=user_id,
                state=UserShiftStateEnum.STARTED_SHIFT,
                entered_at=started_at,
                exited_at=started_at,
            ),
            UserShiftStateRecord(
                workspace_id=workspace_id,
                user_id=user_id,
                state=state,
                entered_at=started_at,
                exited_at=None,
            ),
        ]
    )


async def _load_shift_records(db_session, workspace_id: str, user_id: str):
    db_session.expire_all()
    return list(
        (
            await db_session.execute(
                select(UserShiftStateRecord)
                .where(
                    UserShiftStateRecord.workspace_id == workspace_id,
                    UserShiftStateRecord.user_id == user_id,
                )
                .order_by(
                    UserShiftStateRecord.entered_at,
                    UserShiftStateRecord.client_id,
                )
                .execution_options(populate_existing=True)
            )
        ).scalars()
    )


async def test_handler_last_working_to_pause_sets_shift_in_pause(db_session) -> None:
    workspace, worker, task, section = await _seed_environment(db_session)
    transitioned_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    _seed_open_shift(
        db_session,
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        state=UserShiftStateEnum.WORKING,
        started_at=transitioned_at - timedelta(hours=1),
    )
    payload = await _seed_post_transition_step(
        db_session,
        workspace=workspace,
        worker=worker,
        task=task,
        section=section,
        closing_state=TaskStepStateEnum.WORKING,
        new_state=TaskStepStateEnum.PAUSED,
        transitioned_at=transitioned_at,
        reason=StepEventReasonEnum.PAUSE_COFFEE_BREAK,
    )
    workspace_id = workspace.client_id
    worker_id = worker.client_id
    await db_session.commit()

    await handle_process_step_transition(payload, "task_shift_pause")

    records = await _load_shift_records(db_session, workspace_id, worker_id)
    assert records[-1].state is UserShiftStateEnum.IN_PAUSE
    assert records[-1].reason == StepEventReasonEnum.PAUSE_COFFEE_BREAK.value
    assert records[-1].exited_at is None


async def test_handler_last_working_to_complete_sets_shift_idle(db_session) -> None:
    workspace, worker, task, section = await _seed_environment(db_session)
    transitioned_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    _seed_open_shift(
        db_session,
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        state=UserShiftStateEnum.WORKING,
        started_at=transitioned_at - timedelta(hours=1),
    )
    payload = await _seed_post_transition_step(
        db_session,
        workspace=workspace,
        worker=worker,
        task=task,
        section=section,
        closing_state=TaskStepStateEnum.WORKING,
        new_state=TaskStepStateEnum.COMPLETED,
        transitioned_at=transitioned_at,
    )
    workspace_id = workspace.client_id
    worker_id = worker.client_id
    await db_session.commit()

    await handle_process_step_transition(payload, "task_shift_complete")

    records = await _load_shift_records(db_session, workspace_id, worker_id)
    assert records[-1].state is UserShiftStateEnum.IDLE
    assert records[-1].exited_at is None


async def test_handler_start_auto_clocks_in_and_sets_shift_working(db_session) -> None:
    workspace, worker, task, section = await _seed_environment(db_session)
    transitioned_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    payload = await _seed_post_transition_step(
        db_session,
        workspace=workspace,
        worker=worker,
        task=task,
        section=section,
        closing_state=TaskStepStateEnum.PENDING,
        new_state=TaskStepStateEnum.WORKING,
        transitioned_at=transitioned_at,
    )
    workspace_id = workspace.client_id
    worker_id = worker.client_id
    await db_session.commit()

    await handle_process_step_transition(payload, "task_shift_auto_clock_in")

    records = await _load_shift_records(db_session, workspace_id, worker_id)
    assert records[0].state is UserShiftStateEnum.STARTED_SHIFT
    assert records[0].entered_at == transitioned_at
    assert records[0].exited_at == transitioned_at
    assert records[1].state is UserShiftStateEnum.WORKING
    assert records[1].exited_at is None


async def test_batch_event_fanout_creates_one_shift_transition(db_session) -> None:
    workspace, worker, task, section = await _seed_environment(db_session)
    transitioned_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    _seed_open_shift(
        db_session,
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        state=UserShiftStateEnum.WORKING,
        started_at=transitioned_at - timedelta(hours=1),
    )
    payloads = [
        await _seed_post_transition_step(
            db_session,
            workspace=workspace,
            worker=worker,
            task=task,
            section=section,
            closing_state=TaskStepStateEnum.WORKING,
            new_state=TaskStepStateEnum.PAUSED,
            transitioned_at=transitioned_at,
            reason=StepEventReasonEnum.PAUSE_COFFEE_BREAK,
        )
        for _ in range(3)
    ]
    workspace_id = workspace.client_id
    worker_id = worker.client_id
    await db_session.commit()

    for index, payload in enumerate(payloads):
        await handle_process_step_transition(payload, f"task_shift_batch_{index}")

    records = await _load_shift_records(db_session, workspace_id, worker_id)
    assert [record.state for record in records].count(UserShiftStateEnum.IN_PAUSE) == 1
    assert sum(record.exited_at is None for record in records) == 1
    assert records[-1].state is UserShiftStateEnum.IN_PAUSE
