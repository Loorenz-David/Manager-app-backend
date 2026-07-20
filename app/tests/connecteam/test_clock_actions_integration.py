from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from freezegun import freeze_time
from sqlalchemy import select

from beyo_manager.domain.connecteam.time_activity_event import ConnecteamTimeActivityEvent
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import StepEventReasonEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.users.toggle_worker_shift import toggle_worker_shift
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.tasks.connecteam.handlers.handle_clock_in import execute as clock_in
from beyo_manager.services.tasks.connecteam.handlers.handle_clock_out import execute as clock_out
from beyo_manager.services.queries.users.resolve_connecteam_worker import ResolvedConnecteamWorker


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _seed_worker(db_session, workspace: Workspace, label: str, connecteam_id: str):
    suffix = uuid4().hex
    worker = User(
        username=f"connecteam-{label}-{suffix}",
        email=f"connecteam-{label}-{suffix}@example.com",
        password="test-password-hash",
    )
    db_session.add(worker)
    await db_session.flush()
    db_session.add(
        UserWorkProfile(
            user_id=worker.client_id,
            workspace_id=workspace.client_id,
            created_by_id=worker.client_id,
            connecteam_user_id=connecteam_id,
        )
    )
    await db_session.flush()
    return worker


async def _records(db_session, workspace_id: str, user_id: str):
    return list(
        (
            await db_session.execute(
                select(UserShiftStateRecord)
                .where(
                    UserShiftStateRecord.workspace_id == workspace_id,
                    UserShiftStateRecord.user_id == user_id,
                )
                .order_by(UserShiftStateRecord.entered_at, UserShiftStateRecord.client_id)
            )
        ).scalars()
    )


def _event(event_type: str, occurred_at: str) -> ConnecteamTimeActivityEvent:
    return ConnecteamTimeActivityEvent(
        event_key=f"connecteam:{event_type}:{occurred_at}",
        provider="connecteam",
        event_type=event_type,
        activity_type="shift",
        request_id="request-integration",
        company_id="company-integration",
        connecteam_user_id="connecteam-webhook-worker",
        time_clock_id="clock",
        time_activity_id="activity",
        occurred_at=occurred_at,
        received_at="2026-07-20T08:00:02+00:00",
        payload={},
    )


def _record_shape(records, actor_id: str):
    return sorted(
        [
            (
                record.state.value,
                record.entered_at,
                record.exited_at,
                record.changed_by_id == actor_id,
                record.reason,
                record.manually_recorded,
            )
            for record in records
        ],
        key=lambda shape: (shape[0], shape[1], shape[2] or shape[1]),
    )


async def _seed_open_working_step(db_session, workspace_id: str, user_id: str, entered_at):
    suffix = uuid4().hex
    section = WorkingSection(
        workspace_id=workspace_id,
        name=f"connecteam-parity-section-{suffix}",
        created_by_id=user_id,
    )
    task = Task(
        workspace_id=workspace_id,
        task_scalar_id=int(suffix[:7], 16),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=user_id,
    )
    db_session.add_all([section, task])
    await db_session.flush()
    step = TaskStep(
        workspace_id=workspace_id,
        task_id=task.client_id,
        state=TaskStepStateEnum.WORKING,
        working_section_id=section.client_id,
        assigned_worker_id=user_id,
        created_by_id=user_id,
    )
    db_session.add(step)
    await db_session.flush()
    record = StepStateRecord(
        workspace_id=workspace_id,
        step_id=step.client_id,
        state=TaskStepStateEnum.WORKING,
        reason=None,
        entered_at=entered_at,
        exited_at=None,
        created_by_id=user_id,
        credited_user_id=user_id,
    )
    db_session.add(record)
    await db_session.flush()
    step.latest_state_record_id = record.client_id
    return step


async def test_webhook_records_match_toggle_shape_and_use_provider_timestamps(db_session) -> None:
    suffix = uuid4().hex
    workspace = Workspace(name=f"connecteam-parity-{suffix}")
    db_session.add(workspace)
    await db_session.flush()

    worker_role = (
        await db_session.execute(select(Role).where(Role.name == RoleNameEnum.WORKER))
    ).scalar_one_or_none()
    if worker_role is None:
        worker_role = Role(name=RoleNameEnum.WORKER)
        db_session.add(worker_role)
        await db_session.flush()
    workspace_role = WorkspaceRole(
        workspace_id=workspace.client_id,
        role_id=worker_role.client_id,
        is_system=True,
    )
    db_session.add(workspace_role)
    await db_session.flush()

    manual_worker = await _seed_worker(db_session, workspace, "manual", "connecteam-manual")
    webhook_worker = await _seed_worker(
        db_session, workspace, "webhook", "connecteam-webhook-worker"
    )
    db_session.add_all(
        [
            WorkspaceMembership(
                user_id=manual_worker.client_id,
                workspace_id=workspace.client_id,
                workspace_role_id=workspace_role.client_id,
                is_active=True,
            ),
            WorkspaceMembership(
                user_id=webhook_worker.client_id,
                workspace_id=workspace.client_id,
                workspace_role_id=workspace_role.client_id,
                is_active=True,
            ),
        ]
    )
    await db_session.flush()
    await db_session.commit()

    clock_in_at = datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc)
    clock_out_at = datetime(2026, 7, 20, 16, 0, tzinfo=timezone.utc)
    manual_ctx = ServiceContext(
        identity={
            "workspace_id": workspace.client_id,
            "user_id": manual_worker.client_id,
            "role_name": RoleNameEnum.WORKER.value,
        },
        incoming_data={},
        session=db_session,
    )
    webhook_resolved = ResolvedConnecteamWorker(
        work_profile_id="uwp_webhook",
        user_id=webhook_worker.client_id,
        workspace_id=workspace.client_id,
    )
    manual_worker_id = manual_worker.client_id
    webhook_worker_id = webhook_worker.client_id
    workspace_id = workspace.client_id

    with freeze_time(clock_in_at):
        async with db_session.begin():
            await toggle_worker_shift(manual_ctx)
            await clock_in(
                session=db_session,
                worker=webhook_resolved,
                event=_event("clock_in", clock_in_at.isoformat()),
            )

        manual_after_in = await _records(db_session, workspace_id, manual_worker_id)
        webhook_after_in = await _records(db_session, workspace_id, webhook_worker_id)
    assert _record_shape(manual_after_in, manual_worker_id) == _record_shape(
        webhook_after_in, webhook_worker_id
    )
    started_record = next(
        record for record in webhook_after_in if record.state is UserShiftStateEnum.STARTED_SHIFT
    )
    idle_record = next(
        record for record in webhook_after_in if record.state is UserShiftStateEnum.IDLE
    )
    assert started_record.entered_at == clock_in_at
    assert started_record.changed_by_id == webhook_worker_id
    assert idle_record.manually_recorded is False
    await db_session.rollback()

    async with db_session.begin():
        working_step = await _seed_open_working_step(
            db_session,
            workspace_id,
            webhook_worker_id,
            clock_in_at,
        )

    with freeze_time(clock_out_at):
        async with db_session.begin():
            await toggle_worker_shift(manual_ctx)
            webhook_clock_out = await clock_out(
                session=db_session,
                worker=webhook_resolved,
                event=_event("clock_out", clock_out_at.isoformat()),
            )

    manual_after_out = await _records(db_session, workspace_id, manual_worker_id)
    webhook_after_out = await _records(db_session, workspace_id, webhook_worker_id)
    assert _record_shape(manual_after_out, manual_worker_id) == _record_shape(
        webhook_after_out, webhook_worker_id
    )
    await db_session.refresh(working_step)
    ended_step_record = (
        await db_session.execute(
            select(StepStateRecord).where(
                StepStateRecord.step_id == working_step.client_id,
                StepStateRecord.state == TaskStepStateEnum.ENDED_SHIFT,
                StepStateRecord.reason == StepEventReasonEnum.PAUSE_ENDED_SHIFT,
            )
        )
    ).scalar_one()
    assert webhook_clock_out.transitioned_steps == 1
    assert working_step.state is TaskStepStateEnum.ENDED_SHIFT
    assert ended_step_record.entered_at == clock_out_at
    assert webhook_after_out[-1].state is UserShiftStateEnum.ENDED_SHIFT
    assert webhook_after_out[-1].entered_at == clock_out_at
    assert webhook_after_out[-1].exited_at == clock_out_at
    assert webhook_after_out[-1].changed_by_id == webhook_worker_id
