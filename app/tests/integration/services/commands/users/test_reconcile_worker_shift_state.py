import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_declared_state_record import (
    UserDeclaredStateRecord,
)
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.users.reconcile_worker_shift_state import (
    reconcile_worker_shift_state,
)


pytestmark = pytest.mark.asyncio


async def _seed_worker(db_session) -> tuple[Workspace, User]:
    suffix = uuid4().hex
    workspace = Workspace(name=f"shift-reconcile-{suffix}")
    user = User(
        username=f"shift-worker-{suffix}",
        email=f"shift-worker-{suffix}@example.com",
        password="test-password-hash",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    return workspace, user


async def _seed_open_step(
    db_session,
    workspace: Workspace,
    user: User,
    *,
    state: TaskStepStateEnum,
    entered_at: datetime,
    reason: str | None = None,
) -> StepStateRecord:
    suffix = uuid4().hex
    section = WorkingSection(
        workspace_id=workspace.client_id,
        name=f"shift-section-{suffix}",
        created_by_id=user.client_id,
    )
    task = Task(
        workspace_id=workspace.client_id,
        task_scalar_id=int(suffix[:7], 16),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=user.client_id,
    )
    db_session.add_all([section, task])
    await db_session.flush()
    step = TaskStep(
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        state=state,
        working_section_id=section.client_id,
        assigned_worker_id=user.client_id,
        created_by_id=user.client_id,
    )
    db_session.add(step)
    await db_session.flush()
    record = StepStateRecord(
        workspace_id=workspace.client_id,
        step_id=step.client_id,
        state=state,
        pause_reason_id=(
            await db_session.scalar(
                select(PauseReason.client_id).where(
                    PauseReason.slug == reason,
                )
            )
            if reason is not None
            else None
        ),
        entered_at=entered_at,
        exited_at=None,
        created_by_id=user.client_id,
        credited_user_id=user.client_id,
    )
    db_session.add(record)
    await db_session.flush()
    step.latest_state_record_id = record.client_id
    return record


async def _seed_declared_state(
    db_session,
    workspace: Workspace,
    user: User,
    *,
    entered_at: datetime,
    reason: str,
    exited_at: datetime | None = None,
) -> UserDeclaredStateRecord:
    suffix = uuid4().hex
    pause_reason = PauseReason(
        workspace_id=workspace.client_id,
        name=f"{reason.replace('_', ' ').title()} {suffix}",
        pause_type=PauseTypeEnum.PERSONAL,
        slug=f"{reason}-{suffix}",
        created_by_id=user.client_id,
    )
    db_session.add(pause_reason)
    await db_session.flush()
    declared = UserDeclaredStateRecord(
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        pause_reason_id=pause_reason.client_id,
        entered_at=entered_at,
        exited_at=exited_at,
        created_by_id=user.client_id,
        closed_by_id=None,
    )
    db_session.add(declared)
    await db_session.flush()
    return declared


def _shift_record(
    workspace: Workspace,
    user: User,
    state: UserShiftStateEnum,
    entered_at: datetime,
    exited_at: datetime | None,
    *,
    manually_recorded: bool = False,
) -> UserShiftStateRecord:
    return UserShiftStateRecord(
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        state=state,
        entered_at=entered_at,
        exited_at=exited_at,
        manually_recorded=manually_recorded,
    )


async def _load_shift_records(db_session, workspace_id: str, user_id: str):
    result = await db_session.execute(
        select(UserShiftStateRecord)
        .where(
            UserShiftStateRecord.workspace_id == workspace_id,
            UserShiftStateRecord.user_id == user_id,
        )
        .order_by(UserShiftStateRecord.entered_at, UserShiftStateRecord.client_id)
    )
    return list(result.scalars().all())


async def test_reconcile_is_idempotent(db_session) -> None:
    workspace, user = await _seed_worker(db_session)
    shift_start = datetime(2026, 7, 20, 8, tzinfo=timezone.utc)
    now = shift_start + timedelta(hours=1)
    db_session.add_all(
        [
            _shift_record(workspace, user, UserShiftStateEnum.STARTED_SHIFT, shift_start, shift_start),
            _shift_record(workspace, user, UserShiftStateEnum.IDLE, shift_start, None),
        ]
    )
    await _seed_open_step(
        db_session,
        workspace,
        user,
        state=TaskStepStateEnum.WORKING,
        entered_at=now - timedelta(minutes=10),
    )

    first = await reconcile_worker_shift_state(
        db_session, workspace.client_id, user.client_id, now
    )
    second = await reconcile_worker_shift_state(
        db_session, workspace.client_id, user.client_id, now
    )

    records = await _load_shift_records(db_session, workspace.client_id, user.client_id)
    assert first.changed is True
    assert second.changed is False
    assert {record.state for record in records} == {
        UserShiftStateEnum.STARTED_SHIFT,
        UserShiftStateEnum.IDLE,
        UserShiftStateEnum.WORKING,
    }
    assert sum(record.exited_at is None for record in records) == 1


async def test_reconcile_auto_clock_in_uses_working_start(db_session) -> None:
    workspace, user = await _seed_worker(db_session)
    working_start = datetime(2026, 7, 20, 8, 15, tzinfo=timezone.utc)
    now = working_start + timedelta(minutes=20)
    await _seed_open_step(
        db_session,
        workspace,
        user,
        state=TaskStepStateEnum.WORKING,
        entered_at=working_start,
    )

    outcome = await reconcile_worker_shift_state(
        db_session, workspace.client_id, user.client_id, now
    )

    records = await _load_shift_records(db_session, workspace.client_id, user.client_id)
    assert outcome.auto_clocked_in is True
    assert [(record.state, record.entered_at, record.exited_at) for record in records] == [
        (UserShiftStateEnum.STARTED_SHIFT, working_start, working_start),
        (UserShiftStateEnum.WORKING, now, None),
    ]


async def test_reconcile_auto_clock_in_clamps_to_latest_ended_marker(db_session) -> None:
    workspace, user = await _seed_worker(db_session)
    working_start = datetime(2026, 7, 20, 8, tzinfo=timezone.utc)
    prior_end = working_start + timedelta(minutes=30)
    now = working_start + timedelta(hours=1)
    db_session.add(
        _shift_record(workspace, user, UserShiftStateEnum.ENDED_SHIFT, prior_end, prior_end)
    )
    await _seed_open_step(
        db_session,
        workspace,
        user,
        state=TaskStepStateEnum.WORKING,
        entered_at=working_start,
    )

    await reconcile_worker_shift_state(db_session, workspace.client_id, user.client_id, now)

    records = await _load_shift_records(db_session, workspace.client_id, user.client_id)
    started = [record for record in records if record.state is UserShiftStateEnum.STARTED_SHIFT]
    assert len(started) == 1
    assert started[0].entered_at == prior_end
    assert started[0].exited_at == prior_end


async def test_reconcile_without_shift_or_working_step_is_noop(db_session) -> None:
    workspace, user = await _seed_worker(db_session)

    outcome = await reconcile_worker_shift_state(
        db_session,
        workspace.client_id,
        user.client_id,
        datetime(2026, 7, 20, 9, tzinfo=timezone.utc),
    )

    assert outcome.changed is False
    assert outcome.state is None
    assert await _load_shift_records(db_session, workspace.client_id, user.client_id) == []


async def test_reconcile_ignores_open_pause_from_previous_shift(db_session) -> None:
    workspace, user = await _seed_worker(db_session)
    previous_day = datetime(2026, 7, 19, 12, tzinfo=timezone.utc)
    shift_start = datetime(2026, 7, 20, 8, tzinfo=timezone.utc)
    await _seed_open_step(
        db_session,
        workspace,
        user,
        state=TaskStepStateEnum.PAUSED,
        entered_at=previous_day,
        reason="pause_lunch_break",
    )
    db_session.add_all(
        [
            _shift_record(workspace, user, UserShiftStateEnum.STARTED_SHIFT, shift_start, shift_start),
            _shift_record(workspace, user, UserShiftStateEnum.IDLE, shift_start, None),
        ]
    )

    outcome = await reconcile_worker_shift_state(
        db_session,
        workspace.client_id,
        user.client_id,
        shift_start + timedelta(minutes=5),
    )

    assert outcome.changed is False
    assert outcome.state is UserShiftStateEnum.IDLE


async def test_reconcile_pause_uses_earliest_open_pause_reason(db_session) -> None:
    workspace, user = await _seed_worker(db_session)
    shift_start = datetime(2026, 7, 20, 8, tzinfo=timezone.utc)
    now = shift_start + timedelta(hours=1)
    db_session.add_all(
        [
            _shift_record(workspace, user, UserShiftStateEnum.STARTED_SHIFT, shift_start, shift_start),
            _shift_record(workspace, user, UserShiftStateEnum.IDLE, shift_start, None),
        ]
    )
    await _seed_open_step(
        db_session,
        workspace,
        user,
        state=TaskStepStateEnum.PAUSED,
        entered_at=shift_start + timedelta(minutes=10),
        reason="pause_coffee_break",
    )
    await _seed_open_step(
        db_session,
        workspace,
        user,
        state=TaskStepStateEnum.PAUSED,
        entered_at=shift_start + timedelta(minutes=20),
        reason="pause_lunch_break",
    )

    outcome = await reconcile_worker_shift_state(
        db_session, workspace.client_id, user.client_id, now
    )

    open_record = (
        await db_session.execute(
            select(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace.client_id,
                UserShiftStateRecord.user_id == user.client_id,
                UserShiftStateRecord.exited_at.is_(None),
            )
        )
    ).scalar_one()
    assert outcome.state is UserShiftStateEnum.IN_PAUSE
    pause_reason_id = await db_session.scalar(
        select(PauseReason.client_id).where(PauseReason.slug == "pause_coffee_break")
    )
    assert open_record.reason == pause_reason_id


async def test_reconcile_declared_state_is_derived_and_idempotent(db_session) -> None:
    workspace, user = await _seed_worker(db_session)
    shift_start = datetime(2026, 7, 20, 8, tzinfo=timezone.utc)
    now = shift_start + timedelta(minutes=20)
    db_session.add_all(
        [
            _shift_record(workspace, user, UserShiftStateEnum.STARTED_SHIFT, shift_start, shift_start),
            _shift_record(workspace, user, UserShiftStateEnum.IDLE, shift_start, None),
        ]
    )
    declared = await _seed_declared_state(
        db_session,
        workspace,
        user,
        entered_at=shift_start + timedelta(minutes=10),
        reason="pause_coffee_break",
    )

    first = await reconcile_worker_shift_state(
        db_session, workspace.client_id, user.client_id, now
    )
    second = await reconcile_worker_shift_state(
        db_session, workspace.client_id, user.client_id, now + timedelta(minutes=1)
    )

    records = await _load_shift_records(db_session, workspace.client_id, user.client_id)
    current = next(record for record in records if record.exited_at is None)
    assert first.changed is True
    assert second.changed is False
    assert current.state is UserShiftStateEnum.IN_PAUSE
    assert current.reason == declared.pause_reason_id
    assert current.manually_recorded is True
    assert sum(
        record.state is UserShiftStateEnum.IN_PAUSE for record in records
    ) == 1


async def test_reconcile_ignores_open_declaration_from_before_current_shift(
    db_session,
) -> None:
    workspace, user = await _seed_worker(db_session)
    shift_start = datetime(2026, 7, 20, 8, tzinfo=timezone.utc)
    db_session.add_all(
        [
            _shift_record(
                workspace,
                user,
                UserShiftStateEnum.STARTED_SHIFT,
                shift_start,
                shift_start,
            ),
            _shift_record(
                workspace,
                user,
                UserShiftStateEnum.IDLE,
                shift_start,
                None,
            ),
        ]
    )
    stale_declared = await _seed_declared_state(
        db_session,
        workspace,
        user,
        entered_at=shift_start - timedelta(minutes=10),
        reason="pause_coffee_break",
    )

    outcome = await reconcile_worker_shift_state(
        db_session,
        workspace.client_id,
        user.client_id,
        shift_start + timedelta(minutes=20),
    )

    current = (
        await db_session.execute(
            select(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace.client_id,
                UserShiftStateRecord.user_id == user.client_id,
                UserShiftStateRecord.exited_at.is_(None),
            )
        )
    ).scalar_one()
    assert outcome.changed is False
    assert current.state is UserShiftStateEnum.IDLE
    assert stale_declared.exited_at is None


async def test_reconcile_working_closes_declaration_without_resurrection(
    db_session,
) -> None:
    workspace, user = await _seed_worker(db_session)
    shift_start = datetime(2026, 7, 20, 8, tzinfo=timezone.utc)
    db_session.add_all(
        [
            _shift_record(workspace, user, UserShiftStateEnum.STARTED_SHIFT, shift_start, shift_start),
            _shift_record(workspace, user, UserShiftStateEnum.IDLE, shift_start, None),
        ]
    )
    declared = await _seed_declared_state(
        db_session,
        workspace,
        user,
        entered_at=shift_start + timedelta(minutes=5),
        reason="pause_coffee_break",
    )
    await reconcile_worker_shift_state(
        db_session,
        workspace.client_id,
        user.client_id,
        shift_start + timedelta(minutes=10),
    )
    working_record = await _seed_open_step(
        db_session,
        workspace,
        user,
        state=TaskStepStateEnum.WORKING,
        entered_at=shift_start + timedelta(minutes=20),
    )
    working_at = shift_start + timedelta(minutes=21)

    working_outcome = await reconcile_worker_shift_state(
        db_session,
        workspace.client_id,
        user.client_id,
        working_at,
    )
    await db_session.refresh(declared)
    working_record.exited_at = shift_start + timedelta(minutes=30)
    idle_outcome = await reconcile_worker_shift_state(
        db_session,
        workspace.client_id,
        user.client_id,
        shift_start + timedelta(minutes=31),
    )

    current = (
        await db_session.execute(
            select(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace.client_id,
                UserShiftStateRecord.user_id == user.client_id,
                UserShiftStateRecord.exited_at.is_(None),
            )
        )
    ).scalar_one()
    assert working_outcome.state is UserShiftStateEnum.WORKING
    assert declared.exited_at == working_at
    assert declared.closed_by_id is None
    assert idle_outcome.state is UserShiftStateEnum.IDLE
    assert current.state is UserShiftStateEnum.IDLE


async def test_reconcile_declared_state_outranks_open_paused_step(db_session) -> None:
    workspace, user = await _seed_worker(db_session)
    shift_start = datetime(2026, 7, 20, 8, tzinfo=timezone.utc)
    now = shift_start + timedelta(minutes=30)
    db_session.add_all(
        [
            _shift_record(workspace, user, UserShiftStateEnum.STARTED_SHIFT, shift_start, shift_start),
            _shift_record(workspace, user, UserShiftStateEnum.IDLE, shift_start, None),
        ]
    )
    await _seed_open_step(
        db_session,
        workspace,
        user,
        state=TaskStepStateEnum.PAUSED,
        entered_at=shift_start + timedelta(minutes=5),
        reason="pause_lunch_break",
    )
    declared = await _seed_declared_state(
        db_session,
        workspace,
        user,
        entered_at=shift_start + timedelta(minutes=10),
        reason="pause_coffee_break",
    )

    await reconcile_worker_shift_state(
        db_session, workspace.client_id, user.client_id, now
    )

    current = (
        await db_session.execute(
            select(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace.client_id,
                UserShiftStateRecord.user_id == user.client_id,
                UserShiftStateRecord.exited_at.is_(None),
            )
        )
    ).scalar_one()
    assert current.state is UserShiftStateEnum.IN_PAUSE
    assert current.reason == declared.pause_reason_id
    assert current.manually_recorded is True


async def test_reconcile_updates_pause_projection_when_source_changes(db_session) -> None:
    workspace, user = await _seed_worker(db_session)
    shift_start = datetime(2026, 7, 20, 8, tzinfo=timezone.utc)
    db_session.add_all(
        [
            _shift_record(
                workspace,
                user,
                UserShiftStateEnum.STARTED_SHIFT,
                shift_start,
                shift_start,
            ),
            _shift_record(
                workspace,
                user,
                UserShiftStateEnum.IDLE,
                shift_start,
                None,
            ),
        ]
    )
    declared = await _seed_declared_state(
        db_session,
        workspace,
        user,
        entered_at=shift_start + timedelta(minutes=5),
        reason="pause_coffee_break",
    )
    await reconcile_worker_shift_state(
        db_session,
        workspace.client_id,
        user.client_id,
        shift_start + timedelta(minutes=6),
    )

    declared.exited_at = shift_start + timedelta(minutes=10)
    step_reason = PauseReason(
        workspace_id=workspace.client_id,
        name=f"Step pause {uuid4().hex}",
        pause_type=PauseTypeEnum.PERSONAL,
        slug=f"step-pause-{uuid4().hex}",
        created_by_id=user.client_id,
    )
    db_session.add(step_reason)
    await db_session.flush()
    await _seed_open_step(
        db_session,
        workspace,
        user,
        state=TaskStepStateEnum.PAUSED,
        entered_at=declared.exited_at,
        reason=step_reason.slug,
    )

    outcome = await reconcile_worker_shift_state(
        db_session,
        workspace.client_id,
        user.client_id,
        shift_start + timedelta(minutes=11),
    )

    current = (
        await db_session.execute(
            select(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace.client_id,
                UserShiftStateRecord.user_id == user.client_id,
                UserShiftStateRecord.exited_at.is_(None),
            )
        )
    ).scalar_one()
    assert outcome.changed is True
    assert current.state is UserShiftStateEnum.IN_PAUSE
    assert current.reason == step_reason.client_id
    assert current.manually_recorded is False


async def test_reconcile_keeps_step_pause_reason_when_earliest_step_closes(
    db_session,
) -> None:
    workspace, user = await _seed_worker(db_session)
    shift_start = datetime(2026, 7, 20, 8, tzinfo=timezone.utc)
    db_session.add_all(
        [
            _shift_record(
                workspace,
                user,
                UserShiftStateEnum.STARTED_SHIFT,
                shift_start,
                shift_start,
            ),
            _shift_record(
                workspace,
                user,
                UserShiftStateEnum.IDLE,
                shift_start,
                None,
            ),
        ]
    )
    first_reason = PauseReason(
        workspace_id=workspace.client_id,
        name=f"First step pause {uuid4().hex}",
        pause_type=PauseTypeEnum.PERSONAL,
        slug=f"first-step-pause-{uuid4().hex}",
        created_by_id=user.client_id,
    )
    second_reason = PauseReason(
        workspace_id=workspace.client_id,
        name=f"Second step pause {uuid4().hex}",
        pause_type=PauseTypeEnum.PERSONAL,
        slug=f"second-step-pause-{uuid4().hex}",
        created_by_id=user.client_id,
    )
    db_session.add_all([first_reason, second_reason])
    await db_session.flush()
    first_step_pause = await _seed_open_step(
        db_session,
        workspace,
        user,
        state=TaskStepStateEnum.PAUSED,
        entered_at=shift_start + timedelta(minutes=5),
        reason=first_reason.slug,
    )
    await _seed_open_step(
        db_session,
        workspace,
        user,
        state=TaskStepStateEnum.PAUSED,
        entered_at=shift_start + timedelta(minutes=10),
        reason=second_reason.slug,
    )
    await reconcile_worker_shift_state(
        db_session,
        workspace.client_id,
        user.client_id,
        shift_start + timedelta(minutes=11),
    )
    current_before = (
        await db_session.execute(
            select(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace.client_id,
                UserShiftStateRecord.user_id == user.client_id,
                UserShiftStateRecord.exited_at.is_(None),
            )
        )
    ).scalar_one()

    first_step_pause.exited_at = shift_start + timedelta(minutes=12)
    outcome = await reconcile_worker_shift_state(
        db_session,
        workspace.client_id,
        user.client_id,
        shift_start + timedelta(minutes=13),
    )

    current_after = (
        await db_session.execute(
            select(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace.client_id,
                UserShiftStateRecord.user_id == user.client_id,
                UserShiftStateRecord.exited_at.is_(None),
            )
        )
    ).scalar_one()
    assert outcome.changed is False
    assert current_after.client_id == current_before.client_id
    assert current_after.reason == first_reason.client_id
    assert current_after.manually_recorded is False


async def test_concurrent_reconciles_create_one_open_shift_record(db_session) -> None:
    workspace, user = await _seed_worker(db_session)
    now = datetime(2026, 7, 20, 9, tzinfo=timezone.utc)
    await _seed_open_step(
        db_session,
        workspace,
        user,
        state=TaskStepStateEnum.WORKING,
        entered_at=now - timedelta(minutes=15),
    )
    await db_session.commit()

    async def _run_reconcile():
        async for session in get_db_session():
            async with session.begin():
                return await reconcile_worker_shift_state(
                    session, workspace.client_id, user.client_id, now
                )
        raise AssertionError("database session was not yielded")

    outcomes = await asyncio.gather(_run_reconcile(), _run_reconcile())

    async for session in get_db_session():
        open_count = await session.scalar(
            select(func.count(UserShiftStateRecord.client_id)).where(
                UserShiftStateRecord.workspace_id == workspace.client_id,
                UserShiftStateRecord.user_id == user.client_id,
                UserShiftStateRecord.exited_at.is_(None),
            )
        )
        started_count = await session.scalar(
            select(func.count(UserShiftStateRecord.client_id)).where(
                UserShiftStateRecord.workspace_id == workspace.client_id,
                UserShiftStateRecord.user_id == user.client_id,
                UserShiftStateRecord.state == UserShiftStateEnum.STARTED_SHIFT,
            )
        )

    assert sum(outcome.changed for outcome in outcomes) == 1
    assert open_count == 1
    assert started_count == 1


async def test_reconcile_pause_without_any_reason_leaves_both_fields_null(
    db_session,
) -> None:
    """The live derivation copies both explanation channels off the owning step record.

    This is the control for that copy: a step pause carrying neither a catalog reason nor
    a transition reason must still project a row with both fields null, exactly as it did
    when the copy was guarded on `pause_reason_id is not None`.
    """
    workspace, user = await _seed_worker(db_session)
    shift_start = datetime(2026, 7, 20, 8, tzinfo=timezone.utc)
    now = shift_start + timedelta(hours=1)
    db_session.add_all(
        [
            _shift_record(workspace, user, UserShiftStateEnum.STARTED_SHIFT, shift_start, shift_start),
            _shift_record(workspace, user, UserShiftStateEnum.IDLE, shift_start, None),
        ]
    )
    await _seed_open_step(
        db_session,
        workspace,
        user,
        state=TaskStepStateEnum.PAUSED,
        entered_at=shift_start + timedelta(minutes=10),
        reason=None,
    )

    outcome = await reconcile_worker_shift_state(
        db_session, workspace.client_id, user.client_id, now
    )

    open_record = (
        await db_session.execute(
            select(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace.client_id,
                UserShiftStateRecord.user_id == user.client_id,
                UserShiftStateRecord.exited_at.is_(None),
            )
        )
    ).scalar_one()
    assert outcome.state is UserShiftStateEnum.IN_PAUSE
    assert open_record.reason is None
    assert open_record.transition_reason is None


async def test_reconcile_projects_a_system_auto_pause_by_its_transition_reason(
    db_session,
) -> None:
    """A system auto-pause carries no catalog id, so the live row would show an
    unexplained pause if the derivation only copied `pause_reason_id`.
    """
    workspace, user = await _seed_worker(db_session)
    shift_start = datetime(2026, 7, 20, 8, tzinfo=timezone.utc)
    now = shift_start + timedelta(hours=1)
    db_session.add_all(
        [
            _shift_record(workspace, user, UserShiftStateEnum.STARTED_SHIFT, shift_start, shift_start),
            _shift_record(workspace, user, UserShiftStateEnum.IDLE, shift_start, None),
        ]
    )
    record = await _seed_open_step(
        db_session,
        workspace,
        user,
        state=TaskStepStateEnum.PAUSED,
        entered_at=shift_start + timedelta(minutes=10),
        reason=None,
    )
    record.transition_reason = TransitionReasonEnum.OTHER_TASK_PRIORITY.value
    await db_session.flush()

    outcome = await reconcile_worker_shift_state(
        db_session, workspace.client_id, user.client_id, now
    )

    open_record = (
        await db_session.execute(
            select(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace.client_id,
                UserShiftStateRecord.user_id == user.client_id,
                UserShiftStateRecord.exited_at.is_(None),
            )
        )
    ).scalar_one()
    assert outcome.state is UserShiftStateEnum.IN_PAUSE
    assert open_record.reason is None
    assert open_record.transition_reason == TransitionReasonEnum.OTHER_TASK_PRIORITY.value
