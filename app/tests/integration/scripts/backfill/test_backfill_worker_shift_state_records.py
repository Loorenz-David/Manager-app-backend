from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import (
    StepEventReasonEnum,
    TaskStepStateEnum,
)
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.worker_stats.get_worker_linear_timeline_breakdown import (
    get_worker_linear_timeline_breakdown,
)
from scripts.backfill.backfill_worker_shift_state_records import (
    backfill_worker_shift_day,
)


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _seed_worker_day(db_session):
    suffix = uuid4().hex[:8]
    workspace = Workspace(name=f"backfill-shift-{suffix}")
    worker = User(
        username=f"backfill-shift-{suffix}",
        email=f"backfill-shift-{suffix}@example.com",
        password="secret",
    )
    db_session.add_all([workspace, worker])
    await db_session.flush()
    role = (
        await db_session.execute(
            select(Role).where(Role.name == RoleNameEnum.WORKER)
        )
    ).scalar_one()
    workspace_role = WorkspaceRole(
        workspace_id=workspace.client_id,
        role_id=role.client_id,
    )
    db_session.add(workspace_role)
    await db_session.flush()
    db_session.add(
        WorkspaceMembership(
            workspace_id=workspace.client_id,
            user_id=worker.client_id,
            workspace_role_id=workspace_role.client_id,
            is_active=True,
        )
    )
    section = WorkingSection(
        workspace_id=workspace.client_id,
        name=f"backfill-section-{suffix}",
    )
    task = Task(
        workspace_id=workspace.client_id,
        task_scalar_id=int(suffix[:6], 16),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.WORKING,
        created_by_id=worker.client_id,
    )
    db_session.add_all([section, task])
    await db_session.flush()
    step = TaskStep(
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        working_section_name_snapshot=section.name,
        state=TaskStepStateEnum.WORKING,
        created_by_id=worker.client_id,
    )
    db_session.add(step)
    await db_session.flush()
    return workspace, worker, step


def _add_step_record(
    db_session,
    *,
    workspace_id: str,
    user_id: str,
    step_id: str,
    state: TaskStepStateEnum,
    entered_at: datetime,
    exited_at: datetime,
    reason: StepEventReasonEnum | None = None,
) -> None:
    db_session.add(
        StepStateRecord(
            workspace_id=workspace_id,
            step_id=step_id,
            state=state,
            reason=reason,
            entered_at=entered_at,
            exited_at=exited_at,
            created_by_id=user_id,
            credited_user_id=user_id,
        )
    )


async def _shift_records(db_session, workspace_id: str, user_id: str):
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
            )
        ).scalars()
    )


async def test_backfill_matches_sweep_read_and_is_idempotent(db_session) -> None:
    workspace, worker, step = await _seed_worker_day(db_session)
    work_date = date(2026, 7, 15)
    base = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)
    _add_step_record(
        db_session,
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        step_id=step.client_id,
        state=TaskStepStateEnum.WORKING,
        entered_at=base,
        exited_at=base + timedelta(minutes=20),
    )
    _add_step_record(
        db_session,
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        step_id=step.client_id,
        state=TaskStepStateEnum.PAUSED,
        entered_at=base + timedelta(minutes=20),
        exited_at=base + timedelta(minutes=30),
        reason=StepEventReasonEnum.PAUSE_COFFEE_BREAK,
    )
    _add_step_record(
        db_session,
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        step_id=step.client_id,
        state=TaskStepStateEnum.WORKING,
        entered_at=base + timedelta(minutes=30),
        exited_at=base + timedelta(minutes=50),
    )
    await db_session.flush()
    now = datetime(2026, 7, 20, tzinfo=timezone.utc)

    dry_run = await backfill_worker_shift_day(
        db_session,
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        work_date=work_date,
        now=now,
        execute=False,
    )
    assert dry_run.records_written == 5
    assert await db_session.scalar(
        select(func.count(UserShiftStateRecord.client_id)).where(
            UserShiftStateRecord.workspace_id == workspace.client_id,
            UserShiftStateRecord.user_id == worker.client_id,
        )
    ) == 0

    first = await backfill_worker_shift_day(
        db_session,
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        work_date=work_date,
        now=now,
        execute=True,
    )
    second = await backfill_worker_shift_day(
        db_session,
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        work_date=work_date,
        now=now,
        execute=True,
    )

    count = await db_session.scalar(
        select(func.count(UserShiftStateRecord.client_id)).where(
            UserShiftStateRecord.workspace_id == workspace.client_id,
            UserShiftStateRecord.user_id == worker.client_id,
        )
    )
    records = await _shift_records(
        db_session,
        workspace.client_id,
        worker.client_id,
    )
    assert first == second
    assert count == first.records_written == 5
    assert all(record.exited_at is not None for record in records)
    assert all(record.changed_by_id is None for record in records)
    assert all(record.manually_recorded is False for record in records)

    out = await get_worker_linear_timeline_breakdown(
        ServiceContext(
            identity={
                "workspace_id": workspace.client_id,
                "user_id": "usr_manager",
                "role_name": "manager",
            },
            incoming_data={"user_id": worker.client_id},
            query_params={
                "date_from": work_date.isoformat(),
                "date_to": work_date.isoformat(),
            },
            session=db_session,
        )
    )
    assert out["timeline"]["working_seconds"] == 40 * 60
    assert out["timeline"]["pause_seconds"] == 10 * 60
    assert out["timeline"]["idle_seconds"] == 0
    assert out["timeline"]["pause_by_reason"] == {
        "pause_coffee_break": 10 * 60
    }
    assert [segment["state"] for segment in out["segments"]] == [
        "started_shift",
        "working",
        "paused",
        "working",
        "ended_shift",
    ]


async def test_backfill_ended_shift_segment_terminates_day(db_session) -> None:
    workspace, worker, step = await _seed_worker_day(db_session)
    base = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)
    _add_step_record(
        db_session,
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        step_id=step.client_id,
        state=TaskStepStateEnum.WORKING,
        entered_at=base,
        exited_at=base + timedelta(hours=1),
    )
    _add_step_record(
        db_session,
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        step_id=step.client_id,
        state=TaskStepStateEnum.ENDED_SHIFT,
        entered_at=base + timedelta(hours=1),
        exited_at=base + timedelta(hours=2),
    )
    await db_session.flush()

    await backfill_worker_shift_day(
        db_session,
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        work_date=base.date(),
        now=datetime(2026, 7, 20, tzinfo=timezone.utc),
        execute=True,
    )

    records = await _shift_records(
        db_session,
        workspace.client_id,
        worker.client_id,
    )
    assert {record.state for record in records} == {
        UserShiftStateEnum.STARTED_SHIFT,
        UserShiftStateEnum.WORKING,
        UserShiftStateEnum.ENDED_SHIFT,
    }
    ended = next(
        record
        for record in records
        if record.state is UserShiftStateEnum.ENDED_SHIFT
    )
    assert ended.entered_at == base + timedelta(hours=1)
    assert ended.exited_at == ended.entered_at
