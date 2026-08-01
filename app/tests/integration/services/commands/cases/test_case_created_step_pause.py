"""Creating a case on a task pauses that task's working steps.

The capability existed once, was removed, and its absence went unnoticed — a worker who
raised a case stayed "working" on the timeline while the problem was discussed.

Every test that exercises the write path runs in a workspace holding **zero**
`pause_reasons` rows, asserted rather than assumed by `_assert_zero_catalog`. That is the
property the whole `system_transition_reasons` set exists to guarantee: a mandatory system
transition must not depend on a workspace-editable catalog row. Reviving the retired
`pause_case_created` row would undo it.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum
from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.cases.case_type import CaseType
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
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
from beyo_manager.services.commands.cases.create_case import create_case
from beyo_manager.services.infra.events import worker_shift_realtime
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.worker_stats.list_workers_linear_timeline import (
    list_workers_linear_timeline,
)


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

CASE_CREATED = TransitionReasonEnum.CASE_CREATED.value
PAUSE_MODULE = "beyo_manager.services.commands.cases._case_created_step_pause"


# --------------------------------------------------------------------------- seeding


async def _seed_workspace_user(db_session) -> tuple[Workspace, User]:
    suffix = uuid4().hex[:12]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Case pause {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"worker_{suffix}",
        email=f"{suffix}@example.com",
        password="test-password-hash",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    return workspace, user


async def _assert_zero_catalog(db_session, workspace_id: str) -> None:
    """The premise of the write-path tests, asserted rather than assumed."""
    count = await db_session.scalar(
        select(func.count())
        .select_from(PauseReason)
        .where(PauseReason.workspace_id == workspace_id)
    )
    assert count == 0, "fixture seeded pause reasons; these tests would pass vacuously"


async def _seed_task(db_session, workspace: Workspace, user: User) -> Task:
    suffix = uuid4().hex[:12]
    task = Task(
        workspace_id=workspace.client_id,
        task_scalar_id=int(suffix[:7], 16),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
        created_by_id=user.client_id,
    )
    db_session.add(task)
    await db_session.flush()
    return task


async def _seed_step(
    db_session,
    workspace: Workspace,
    user: User,
    task: Task,
    *,
    state: TaskStepStateEnum = TaskStepStateEnum.WORKING,
    entered_at: datetime | None = None,
    allows_batch_working: bool = False,
    credited_user_id: str | None = None,
) -> tuple[TaskStep, StepStateRecord]:
    suffix = uuid4().hex[:12]
    section = WorkingSection(
        workspace_id=workspace.client_id,
        name=f"section-{suffix}",
        created_by_id=user.client_id,
    )
    db_session.add(section)
    await db_session.flush()
    step = TaskStep(
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        state=state,
        working_section_id=section.client_id,
        working_section_name_snapshot=section.name,
        allows_batch_working=allows_batch_working,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        assigned_worker_id=user.client_id,
        created_by_id=user.client_id,
    )
    db_session.add(step)
    await db_session.flush()
    record = StepStateRecord(
        workspace_id=workspace.client_id,
        step_id=step.client_id,
        state=state,
        entered_at=entered_at or datetime(2026, 8, 1, 9, tzinfo=timezone.utc),
        exited_at=None,
        created_by_id=user.client_id,
        credited_user_id=credited_user_id or user.client_id,
    )
    db_session.add(record)
    await db_session.flush()
    step.latest_state_record_id = record.client_id
    await db_session.flush()
    return step, record


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


def _patch_case_side_effects(monkeypatch) -> None:
    """Silence the case command's own outbox and realtime dispatch.

    Deliberately patches nothing in the pause path — that is what is under test, and it
    resolves no pause reason to patch anyway.
    """

    async def _noop(*_args, **_kwargs):
        return None

    module = "beyo_manager.services.commands.cases.create_case"
    monkeypatch.setattr(f"{module}.dispatch", _noop)
    monkeypatch.setattr(f"{module}.create_instant_task", _noop)


async def _step_records(db_session, step_id: str) -> list[StepStateRecord]:
    return list(
        (
            await db_session.execute(
                select(StepStateRecord)
                .where(StepStateRecord.step_id == step_id)
                .order_by(StepStateRecord.entered_at, StepStateRecord.client_id)
            )
        )
        .scalars()
        .all()
    )


async def _pause_record(db_session, step_id: str) -> StepStateRecord:
    records = await _step_records(db_session, step_id)
    return next(record for record in records if record.state is TaskStepStateEnum.PAUSED)


# ------------------------------------------------------- criteria 3, 4, 8: the happy path


async def test_zero_catalog_case_on_task_pauses_the_working_step(
    db_session, monkeypatch
) -> None:
    """Criteria 3, 4 and 8 together.

    Criterion 4 is the load-bearing one: this workspace holds no `pause_reasons` rows at
    all, so a pause that resolved a catalog row could not be written here.
    """
    _patch_case_side_effects(monkeypatch)
    workspace, worker = await _seed_workspace_user(db_session)
    case_type = CaseType(
        name="Damaged item",
        entity_type=CaseLinkEntityTypeEnum.TASK,
    )
    db_session.add(case_type)
    task = await _seed_task(db_session, workspace, worker)
    step, working_record = await _seed_step(db_session, workspace, worker, task)
    await _assert_zero_catalog(db_session, workspace.client_id)
    await db_session.commit()

    await create_case(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=worker.client_id,
            incoming_data={
                "entity_type": "task",
                "entity_client_id": task.client_id,
                "case_type_id": case_type.client_id,
            },
        )
    )

    await db_session.refresh(step)
    assert step.state is TaskStepStateEnum.PAUSED

    pause = await _pause_record(db_session, step.client_id)
    assert pause.transition_reason == CASE_CREATED
    # The system decided this, so there is no catalog row to point at — and none exists.
    assert pause.pause_reason_id is None
    # Criterion 8: the type name comes off the case's `case_type`, resolved by
    # `create_case` into `type_label` before the pause ever sees it.
    assert pause.description == "case created: Damaged item"
    assert pause.credited_user_id == worker.client_id
    assert step.latest_state_record_id == pause.client_id

    # The previously open WORKING record was closed rather than left open beside the new
    # one — the partial unique index on (workspace_id, step_id) WHERE exited_at IS NULL
    # would otherwise have rejected the insert inside the user's case-creation request.
    await db_session.refresh(working_record)
    assert working_record.exited_at == pause.entered_at
    open_records = [r for r in await _step_records(db_session, step.client_id) if r.exited_at is None]
    assert len(open_records) == 1
    assert open_records[0].client_id == pause.client_id


async def test_description_falls_back_when_the_case_carries_no_type(
    db_session, monkeypatch
) -> None:
    """Criterion 8, the other arm. `case_type_id` and `type_label` are both nullable, so
    the bare description is a real case and not a defensive branch."""
    _patch_case_side_effects(monkeypatch)
    workspace, worker = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace, worker)
    step, _ = await _seed_step(db_session, workspace, worker, task)
    await _assert_zero_catalog(db_session, workspace.client_id)
    await db_session.commit()

    await create_case(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=worker.client_id,
            incoming_data={
                "entity_type": "task",
                "entity_client_id": task.client_id,
            },
        )
    )

    pause = await _pause_record(db_session, step.client_id)
    assert pause.transition_reason == CASE_CREATED
    assert pause.description == "case created"


async def test_free_text_type_label_is_used_when_there_is_no_case_type(
    db_session, monkeypatch
) -> None:
    """Criterion 8's third shape: a caller-supplied `type_label` with no `case_type_id`.
    `create_case` only overwrites `type_label` when it resolves a case type, so the free
    text has to survive into the description."""
    _patch_case_side_effects(monkeypatch)
    workspace, worker = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace, worker)
    step, _ = await _seed_step(db_session, workspace, worker, task)
    await db_session.commit()

    await create_case(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=worker.client_id,
            incoming_data={
                "entity_type": "task",
                "entity_client_id": task.client_id,
                "type_label": "Missing part",
            },
        )
    )

    pause = await _pause_record(db_session, step.client_id)
    assert pause.description == "case created: Missing part"


# ------------------------------------------------------------------ criterion 5: every step


async def test_every_working_step_on_the_task_pauses(db_session, monkeypatch) -> None:
    """Criterion 5, asserted with **two** working steps.

    A case links to the task, never to a step, and a task may have several steps WORKING
    at once under `allows_batch_working`. Leaving a sibling running would contradict the
    reason for pausing at all. A one-step assertion cannot tell "all of them" from
    "the first one".
    """
    _patch_case_side_effects(monkeypatch)
    workspace, worker = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace, worker)
    first, _ = await _seed_step(
        db_session, workspace, worker, task, allows_batch_working=True
    )
    second, _ = await _seed_step(
        db_session, workspace, worker, task, allows_batch_working=True
    )
    # A step of the SAME task that is not being worked, and a working step on a DIFFERENT
    # task: neither may be touched.
    pending, _ = await _seed_step(
        db_session, workspace, worker, task, state=TaskStepStateEnum.PENDING
    )
    other_task = await _seed_task(db_session, workspace, worker)
    unrelated, _ = await _seed_step(db_session, workspace, worker, other_task)
    await _assert_zero_catalog(db_session, workspace.client_id)
    await db_session.commit()

    await create_case(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=worker.client_id,
            incoming_data={
                "entity_type": "task",
                "entity_client_id": task.client_id,
            },
        )
    )

    for step in (first, second):
        await db_session.refresh(step)
        assert step.state is TaskStepStateEnum.PAUSED, step.client_id
        assert (await _pause_record(db_session, step.client_id)).transition_reason == CASE_CREATED

    await db_session.refresh(pending)
    await db_session.refresh(unrelated)
    assert pending.state is TaskStepStateEnum.PENDING
    assert unrelated.state is TaskStepStateEnum.WORKING
    assert not [
        r for r in await _step_records(db_session, unrelated.client_id)
        if r.state is TaskStepStateEnum.PAUSED
    ]


# ------------------------------------------------------------- criterion 6: pausing nothing


async def test_customer_case_creates_the_case_and_pauses_nothing(
    db_session, monkeypatch
) -> None:
    """Criterion 6, first arm. A customer has no task and therefore no step. The skip is
    explicit in the pause module rather than a consequence of a null check."""
    _patch_case_side_effects(monkeypatch)
    workspace, worker = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace, worker)
    step, _ = await _seed_step(db_session, workspace, worker, task)
    await db_session.commit()

    result = await create_case(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=worker.client_id,
            incoming_data={
                "entity_type": "customer",
                "entity_client_id": f"cus_{uuid4().hex[:12]}",
            },
        )
    )

    assert await db_session.scalar(
        select(Case).where(Case.client_id == result["case_client_id"])
    ) is not None
    await db_session.refresh(step)
    assert step.state is TaskStepStateEnum.WORKING
    # No error, and no empty record either.
    assert len(await _step_records(db_session, step.client_id)) == 1


async def test_task_with_no_working_step_creates_the_case_and_pauses_nothing(
    db_session, monkeypatch
) -> None:
    """Criterion 6, second arm."""
    _patch_case_side_effects(monkeypatch)
    workspace, worker = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace, worker)
    step, _ = await _seed_step(
        db_session, workspace, worker, task, state=TaskStepStateEnum.PENDING
    )
    await db_session.commit()

    result = await create_case(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=worker.client_id,
            incoming_data={
                "entity_type": "task",
                "entity_client_id": task.client_id,
            },
        )
    )

    assert await db_session.scalar(
        select(Case).where(Case.client_id == result["case_client_id"])
    ) is not None
    await db_session.refresh(step)
    assert step.state is TaskStepStateEnum.PENDING
    assert len(await _step_records(db_session, step.client_id)) == 1


async def test_case_on_an_unlinked_entity_pauses_nothing(db_session, monkeypatch) -> None:
    """A case with no entity link at all — the default shape of `POST /cases`."""
    _patch_case_side_effects(monkeypatch)
    workspace, worker = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace, worker)
    step, _ = await _seed_step(db_session, workspace, worker, task)
    await db_session.commit()

    result = await create_case(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=worker.client_id,
            incoming_data={},
        )
    )

    assert result["case_client_id"]
    await db_session.refresh(step)
    assert step.state is TaskStepStateEnum.WORKING


# ---------------------------------------------------- criterion 7: the case outlives a failure


async def test_case_survives_a_failed_pause(db_session, monkeypatch, caplog) -> None:
    """Criterion 7. The case is the user's intent; the pause is a side effect.

    Failure is injected at the **second** of two steps, so this also proves the pause is
    all-or-nothing: the first step's already-written transition is rolled back with it,
    rather than leaving the task half paused.
    """
    _patch_case_side_effects(monkeypatch)
    workspace, worker = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace, worker)
    first, _ = await _seed_step(
        db_session, workspace, worker, task, allows_batch_working=True
    )
    second, _ = await _seed_step(
        db_session, workspace, worker, task, allows_batch_working=True
    )
    await db_session.commit()

    from beyo_manager.services.commands.cases import _case_created_step_pause

    real_apply = _case_created_step_pause._apply_step_transition
    calls = {"n": 0}

    async def _fail_on_the_second_step(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return await real_apply(*args, **kwargs)
        raise RuntimeError("injected step-state failure")

    monkeypatch.setattr(
        f"{PAUSE_MODULE}._apply_step_transition", _fail_on_the_second_step
    )

    with caplog.at_level(logging.ERROR, logger=PAUSE_MODULE):
        result = await create_case(
            _ctx(
                db_session,
                workspace_id=workspace.client_id,
                user_id=worker.client_id,
                incoming_data={
                    "entity_type": "task",
                    "entity_client_id": task.client_id,
                },
            )
        )

    assert calls["n"] == 2
    # The user's action stands.
    case = await db_session.scalar(
        select(Case).where(Case.client_id == result["case_client_id"])
    )
    assert case is not None

    # ...and nothing was left half-applied.
    for step in (first, second):
        await db_session.refresh(step)
        assert step.state is TaskStepStateEnum.WORKING, step.client_id
        assert not [
            r for r in await _step_records(db_session, step.client_id)
            if r.state is TaskStepStateEnum.PAUSED
        ]

    # The failure is logged, not swallowed silently.
    assert any(
        record.levelno >= logging.ERROR
        and "case_created_step_pause_failed" in record.getMessage()
        for record in caplog.records
    )


# --------------------------------------------------------- criterion 9: a read surface


async def _seed_roster_worker(db_session, workspace_id: str) -> User:
    suffix = uuid4().hex[:8]
    user = User(
        client_id=f"usr_{suffix}",
        username=f"cc_{suffix}",
        email=f"cc_{suffix}@example.com",
        password="secret",
    )
    db_session.add(user)
    role = (
        await db_session.execute(select(Role).where(Role.name == RoleNameEnum.WORKER))
    ).scalar_one()
    workspace_role = WorkspaceRole(
        client_id=f"wsr_{suffix}",
        workspace_id=workspace_id,
        role_id=role.client_id,
    )
    db_session.add(workspace_role)
    await db_session.flush()
    db_session.add(
        WorkspaceMembership(
            client_id=f"wsm_{suffix}",
            user_id=user.client_id,
            workspace_id=workspace_id,
            workspace_role_id=workspace_role.client_id,
            is_active=True,
        )
    )
    await db_session.flush()
    return user


async def test_roster_timeline_buckets_and_labels_the_new_transition(db_session) -> None:
    """Criterion 9. Read paths resolve `transition_reason` through the shared label map,
    so a new member flows through without a code change — asserted on one timeline
    surface rather than trusted."""
    workspace = Workspace(name=f"cc-roster-{uuid4().hex[:12]}")
    db_session.add(workspace)
    await db_session.flush()
    worker = await _seed_roster_worker(db_session, workspace.client_id)

    base = datetime(2026, 8, 1, 9, tzinfo=timezone.utc)
    db_session.add_all(
        [
            UserShiftStateRecord(
                workspace_id=workspace.client_id,
                user_id=worker.client_id,
                state=UserShiftStateEnum.STARTED_SHIFT,
                entered_at=base,
                exited_at=base,
            ),
            UserShiftStateRecord(
                workspace_id=workspace.client_id,
                user_id=worker.client_id,
                state=UserShiftStateEnum.IN_PAUSE,
                entered_at=base,
                exited_at=base + timedelta(hours=1),
                transition_reason=CASE_CREATED,
            ),
        ]
    )
    await db_session.flush()

    result = await list_workers_linear_timeline(
        ServiceContext(
            identity={
                "workspace_id": workspace.client_id,
                "user_id": "usr_manager",
                "role_name": "manager",
                "username": "mgr",
            },
            incoming_data={},
            query_params={"date_from": "2026-08-01", "date_to": "2026-08-01"},
            session=db_session,
        )
    )

    entry = next(w for w in result["workers"] if w["user"]["client_id"] == worker.client_id)
    assert entry["timeline"]["pause_by_reason"][CASE_CREATED] == 3600
    assert result["pause_reasons"][CASE_CREATED] == {
        "name": "Case created",
        # The retired `pause_case_created` anchor row was inserted with a literal NULL
        # image and never appeared in either seed list, so there is no icon to reproduce.
        "image_url": None,
        "pause_type": PauseTypeEnum.BLOCKER.value,
    }
    missing = set(entry["timeline"]["pause_by_reason"]) - set(result["pause_reasons"])
    assert missing == set(), f"unresolved pause_by_reason keys: {missing}"


async def test_the_pause_is_announced_to_the_workspace(db_session, monkeypatch) -> None:
    """Closes the gap this domain's README carried: the step was paused server-side and no
    client was told.

    It matters more here than for clock-out. A manager raised the case; the worker whose
    step just stopped is elsewhere in the building with a cache that still reads `working`,
    and the workers app guards its own transitions on that cache — so without the event
    their next action fails against a step the server already paused.
    """
    _patch_case_side_effects(monkeypatch)
    emitted: list[tuple[str, str, object]] = []

    async def record_workspace(workspace_id, event, payload):
        emitted.append((workspace_id, event, payload))

    monkeypatch.setattr(
        worker_shift_realtime, "push_workspace_event_items", record_workspace
    )

    workspace, worker = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace, worker)
    step, _ = await _seed_step(db_session, workspace, worker, task)
    await db_session.commit()

    await create_case(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=worker.client_id,
            incoming_data={"entity_type": "task", "entity_client_id": task.client_id},
        )
    )

    assert emitted == [
        (
            workspace.client_id,
            worker_shift_realtime.TASK_STEP_STATE_CHANGED,
            [{"client_id": step.client_id, "new_state": "paused"}],
        )
    ]


async def test_a_case_that_pauses_nothing_emits_nothing(db_session, monkeypatch) -> None:
    _patch_case_side_effects(monkeypatch)
    emitted: list = []

    async def record_workspace(workspace_id, event, payload):
        emitted.append((workspace_id, event, payload))

    monkeypatch.setattr(
        worker_shift_realtime, "push_workspace_event_items", record_workspace
    )

    workspace, worker = await _seed_workspace_user(db_session)
    task = await _seed_task(db_session, workspace, worker)
    await db_session.commit()

    await create_case(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=worker.client_id,
            incoming_data={"entity_type": "task", "entity_client_id": task.client_id},
        )
    )

    assert emitted == []
