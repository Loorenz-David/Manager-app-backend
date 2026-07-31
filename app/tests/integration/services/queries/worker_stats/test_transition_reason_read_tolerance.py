"""Phase 1 step D — read tolerance for `transition_reason` through the real queries.

Nothing writes `transition_reason` in this phase, so every row here is seeded with the
column set directly (criterion 14). Mutating `resolve_transition_reason_label` to return
`None` must make these fail — otherwise they are passing vacuously.
"""

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import event as sa_event, select

from beyo_manager.domain.analytics.linear_timeline import UNSPECIFIED_REASON
from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
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
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.worker_stats.get_worker_clock_out_analytics import (
    get_worker_clock_out_analytics,
)
from beyo_manager.services.queries.worker_stats.get_worker_linear_timeline_breakdown import (
    get_worker_linear_timeline_breakdown,
)
from beyo_manager.services.queries.worker_stats.list_workers_linear_timeline import (
    list_workers_linear_timeline,
)


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

SHIFT_ENDED = TransitionReasonEnum.SHIFT_ENDED.value
OTHER_TASK_PRIORITY = TransitionReasonEnum.OTHER_TASK_PRIORITY.value


@pytest.fixture
def executed_statements():
    """Local SQLAlchemy listener — the shared `count_queries` fixture is broken
    (declared_worker_states baseline)."""
    from beyo_manager.models import database

    engine = database._engine
    assert engine is not None, "init_db() must have run before this fixture"
    statements: list[str] = []

    @sa_event.listens_for(engine.sync_engine, "before_cursor_execute")
    def _record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    yield statements

    sa_event.remove(engine.sync_engine, "before_cursor_execute", _record)


def _ctx(
    db_session,
    workspace_id: str,
    query_params: dict | None = None,
    incoming_data: dict | None = None,
) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": "usr_manager",
            "role_name": "manager",
            "username": "mgr",
        },
        incoming_data=incoming_data or {},
        query_params=query_params or {},
        session=db_session,
    )


async def _seed_worker(db_session, workspace_id: str) -> User:
    suffix = uuid4().hex[:8]
    user = User(
        client_id=f"usr_{suffix}",
        username=f"tr_{suffix}",
        email=f"tr_{suffix}@example.com",
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


def _shift_record(
    db_session,
    workspace_id: str,
    user_id: str,
    state: UserShiftStateEnum,
    entered_at: datetime,
    exited_at: datetime | None,
    *,
    reason: str | None = None,
    transition_reason: str | None = None,
) -> None:
    db_session.add(
        UserShiftStateRecord(
            workspace_id=workspace_id,
            user_id=user_id,
            state=state,
            entered_at=entered_at,
            exited_at=exited_at,
            reason=reason,
            transition_reason=transition_reason,
        )
    )


async def _step_record(
    db_session,
    workspace_id: str,
    user_id: str,
    state: TaskStepStateEnum,
    entered_at: datetime,
    exited_at: datetime | None,
    *,
    pause_reason_id: str | None = None,
    transition_reason: str | None = None,
) -> TaskStep:
    suffix = uuid4().hex[:8]
    section = WorkingSection(workspace_id=workspace_id, name=f"sec-{suffix}")
    task = Task(
        workspace_id=workspace_id,
        task_scalar_id=int(suffix[:6], 16),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
        created_by_id=user_id,
    )
    db_session.add_all([section, task])
    await db_session.flush()
    step = TaskStep(
        workspace_id=workspace_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        working_section_name_snapshot=section.name,
        state=state,
        created_by_id=user_id,
    )
    db_session.add(step)
    await db_session.flush()
    db_session.add(
        StepStateRecord(
            workspace_id=workspace_id,
            step_id=step.client_id,
            state=state,
            pause_reason_id=pause_reason_id,
            transition_reason=transition_reason,
            entered_at=entered_at,
            exited_at=exited_at,
            created_by_id=user_id,
            credited_user_id=user_id,
        )
    )
    await db_session.flush()
    return step


# --- roster timeline (audit R11 + R12) -----------------------------------------------


async def test_roster_buckets_and_labels_a_transition_reason_pause(db_session) -> None:
    workspace = Workspace(name=f"tr-roster-{uuid4().hex}")
    db_session.add(workspace)
    await db_session.flush()
    worker = await _seed_worker(db_session, workspace.client_id)
    base = datetime(2026, 7, 15, 9, tzinfo=timezone.utc)
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.STARTED_SHIFT, base, base)
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.IN_PAUSE, base, base + timedelta(hours=1),
                  transition_reason=OTHER_TASK_PRIORITY)
    await db_session.flush()

    result = await list_workers_linear_timeline(
        _ctx(db_session, workspace.client_id, {"date_from": "2026-07-15", "date_to": "2026-07-15"})
    )

    entry = next(w for w in result["workers"] if w["user"]["client_id"] == worker.client_id)
    assert entry["timeline"]["pause_by_reason"][OTHER_TASK_PRIORITY] == 3600
    assert result["pause_reasons"][OTHER_TASK_PRIORITY] == {
        "name": "Other task priority",
        # Criterion 14: a system transition resolves to the same name AND icon its
        # replaced catalog row carried, so no kiosk surface loses its image.
        "image_url": (
            "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com"
            "/images/ws_workspace_test/pause_reasons/other_task_priority.webp"
        ),
        "pause_type": PauseTypeEnum.BLOCKER.value,
    }
    missing = set(entry["timeline"]["pause_by_reason"]) - set(result["pause_reasons"])
    assert missing == set(), f"unresolved pause_by_reason keys: {missing}"


async def test_transition_reason_labels_cost_no_extra_query(
    db_session, executed_statements
) -> None:
    """Criterion 16 — resolution is from an in-memory map, so a transition-only roster
    issues strictly fewer statements than one that also has a catalog reason to fetch."""
    workspace = Workspace(name=f"tr-roster-q-{uuid4().hex}")
    db_session.add(workspace)
    await db_session.flush()
    worker = await _seed_worker(db_session, workspace.client_id)
    base = datetime(2026, 7, 16, 9, tzinfo=timezone.utc)
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.STARTED_SHIFT, base, base)
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.IN_PAUSE, base, base + timedelta(hours=1),
                  transition_reason=SHIFT_ENDED)
    await db_session.flush()
    params = {"date_from": "2026-07-16", "date_to": "2026-07-16"}

    executed_statements.clear()
    result = await list_workers_linear_timeline(_ctx(db_session, workspace.client_id, params))
    transition_only = [s for s in executed_statements if "FROM pause_reasons" in s]

    assert result["pause_reasons"][SHIFT_ENDED]["name"] == "Ended shift"
    assert transition_only == [], (
        "resolving a code-owned transition reason must not query pause_reasons, "
        f"but issued: {transition_only}"
    )


async def test_catalog_reason_still_queries_pause_reasons(
    db_session, executed_statements
) -> None:
    """Control for the test above: the catalog path is untouched and still round-trips."""
    workspace = Workspace(name=f"tr-roster-catalog-{uuid4().hex}")
    db_session.add(workspace)
    await db_session.flush()
    worker = await _seed_worker(db_session, workspace.client_id)
    reason = PauseReason(
        workspace_id=workspace.client_id,
        name=f"Cleaning-{uuid4().hex[:6]}",
        pause_type=PauseTypeEnum.PERSONAL,
    )
    db_session.add(reason)
    await db_session.flush()
    base = datetime(2026, 7, 17, 9, tzinfo=timezone.utc)
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.STARTED_SHIFT, base, base)
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.IN_PAUSE, base, base + timedelta(hours=1),
                  reason=reason.client_id)
    await db_session.flush()

    executed_statements.clear()
    result = await list_workers_linear_timeline(
        _ctx(db_session, workspace.client_id,
             {"date_from": "2026-07-17", "date_to": "2026-07-17"})
    )

    assert result["pause_reasons"][reason.client_id]["name"] == reason.name
    assert any("FROM pause_reasons" in s for s in executed_statements)


# --- kiosk clock-out analytics (audit R13, criterion 15) ------------------------------


async def test_clock_out_analytics_resolves_transition_and_unspecified_keys(db_session) -> None:
    """The published `pause_by_reason` / `pause_reasons` contract must keep resolving
    EVERY key — the literal `"unspecified"`, a catalog id, and a transition reason."""
    workspace = Workspace(name=f"tr-clockout-{uuid4().hex}")
    worker = User(
        username=f"tr-co-{uuid4().hex[:8]}",
        email=f"tr-co-{uuid4().hex[:8]}@example.com",
        password="hash",
    )
    db_session.add_all([workspace, worker])
    await db_session.flush()
    named = PauseReason(
        workspace_id=workspace.client_id,
        name="Cleaning",
        # Carries an icon so the criterion-14 check below compares like with like: both
        # explanation channels must resolve to a name *and* an image.
        image_url="https://example.test/cleaning.webp",
        pause_type=PauseTypeEnum.PERSONAL,
        created_by_id=worker.client_id,
    )
    db_session.add(named)
    await db_session.flush()

    clock_out_at = datetime(2026, 7, 31, 12, tzinfo=timezone.utc)
    t0 = clock_out_at - timedelta(hours=4)
    t1, t2, t3 = t0 + timedelta(hours=1), t0 + timedelta(hours=2), t0 + timedelta(hours=3)
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.IN_PAUSE, t0, t1, reason=named.client_id)
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.IN_PAUSE, t1, t2, reason=None)
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.IN_PAUSE, t2, t3, transition_reason=OTHER_TASK_PRIORITY)
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.WORKING, t3, clock_out_at)
    await db_session.flush()

    analytics = await get_worker_clock_out_analytics(
        _ctx(db_session, workspace.client_id), worker.client_id, clock_out_at
    )

    buckets = analytics["timeline"]["pause_by_reason"]
    assert buckets[named.client_id] == 3600
    assert buckets[UNSPECIFIED_REASON] == 3600
    assert buckets[OTHER_TASK_PRIORITY] == 3600
    missing = set(buckets) - set(analytics["pause_reasons"])
    assert missing == set(), f"pause_by_reason keys without a pause_reasons entry: {missing}"
    assert analytics["pause_reasons"][OTHER_TASK_PRIORITY]["name"] == "Other task priority"
    # Criterion 14, verified rather than asserted: the kiosk renders name AND icon for
    # every bucket. A system transition must not be the one slice that comes back
    # imageless.
    assert analytics["pause_reasons"][OTHER_TASK_PRIORITY]["image_url"] is not None
    assert analytics["pause_reasons"][named.client_id]["image_url"] is not None
    # The published `unspecified` entry is untouched by this phase.
    assert analytics["pause_reasons"][UNSPECIFIED_REASON] == {
        "name": "Reason unavailable",
        "image_url": None,
        "pause_type": None,
    }


# --- worker breakdown (audit R8 / R9 / R10) ------------------------------------------


async def test_breakdown_resolves_a_transition_reason_step_record(db_session) -> None:
    workspace = Workspace(name=f"tr-breakdown-{uuid4().hex}")
    db_session.add(workspace)
    await db_session.flush()
    worker = await _seed_worker(db_session, workspace.client_id)
    base = datetime(2026, 7, 18, 9, tzinfo=timezone.utc)
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.STARTED_SHIFT, base, base)
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.IN_PAUSE, base, base + timedelta(hours=1),
                  transition_reason=OTHER_TASK_PRIORITY)
    await _step_record(
        db_session, workspace.client_id, worker.client_id,
        TaskStepStateEnum.PAUSED, base, base + timedelta(hours=1),
        transition_reason=OTHER_TASK_PRIORITY,
    )
    await db_session.flush()

    result = await get_worker_linear_timeline_breakdown(
        _ctx(db_session, workspace.client_id,
             {"date_from": "2026-07-18", "date_to": "2026-07-18"},
             {"user_id": worker.client_id})
    )

    assert result["pause_reasons"][OTHER_TASK_PRIORITY]["name"] == "Other task priority"
    paused = [s for s in result["segments"] if s["state"] == "paused"]
    assert paused, "expected a paused segment"
    assert paused[0]["reason"] == OTHER_TASK_PRIORITY
    # The nested object must be POPULATED for a transition-typed record. The timeline
    # calendar renders `record.pause_reason?.name`, so a null here shows a paused block
    # with no explanation. A system transition has no catalog row, so the object is
    # synthesized from the code-owned vocabulary in the same shape a catalog row
    # serializes — the client cannot tell, and must not have to.
    step_details = paused[0]["steps"]
    assert step_details, "expected a step detail"
    assert step_details[0]["pause_reason"] is not None
    assert step_details[0]["pause_reason"]["name"] == "Other task priority"
    assert step_details[0]["pause_reason"]["client_id"] == OTHER_TASK_PRIORITY
    assert step_details[0]["pause_reason"]["image_url"] is not None
    # Still no new top-level key on the detail — the shape is unchanged, only populated.
    assert "transition_reason" not in step_details[0]


async def test_breakdown_never_emits_a_catalog_id_that_did_not_resolve(db_session) -> None:
    """F1 regression — the resolution guard is load-bearing, not incidental.

    `pause_reason_objects` is scoped to `ctx.workspace_id`, so a step whose
    `pause_reason_id` points into ANOTHER workspace resolves to nothing. The segment key
    must fall through to the worker-level reason, exactly as it did before phase 1. If
    the foreign id is emitted instead it is (a) a behaviour change under criterion 17,
    (b) a `pause_by_reason` key absent from the response's own `pause_reasons` map, which
    the published contract guarantees resolves every key, and (c) another workspace's
    `par_…` id leaking into a workspace-scoped response.
    """
    foreign_workspace = Workspace(name=f"tr-foreign-{uuid4().hex}")
    workspace = Workspace(name=f"tr-guard-{uuid4().hex}")
    db_session.add_all([foreign_workspace, workspace])
    await db_session.flush()
    worker = await _seed_worker(db_session, workspace.client_id)

    foreign_reason = PauseReason(
        workspace_id=foreign_workspace.client_id,
        name=f"Foreign-{uuid4().hex[:6]}",
        pause_type=PauseTypeEnum.BLOCKER,
    )
    own_reason = PauseReason(
        workspace_id=workspace.client_id,
        name=f"Own-{uuid4().hex[:6]}",
        pause_type=PauseTypeEnum.PERSONAL,
    )
    db_session.add_all([foreign_reason, own_reason])
    await db_session.flush()

    base = datetime(2026, 7, 20, 9, tzinfo=timezone.utc)
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.STARTED_SHIFT, base, base)
    # Worker-level reason resolves in THIS workspace — this is what must be emitted.
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.IN_PAUSE, base, base + timedelta(hours=1),
                  reason=own_reason.client_id)
    # Step-level reason points at the other workspace's catalog row.
    await _step_record(
        db_session, workspace.client_id, worker.client_id,
        TaskStepStateEnum.PAUSED, base, base + timedelta(hours=1),
        pause_reason_id=foreign_reason.client_id,
    )
    await db_session.flush()

    result = await get_worker_linear_timeline_breakdown(
        _ctx(db_session, workspace.client_id,
             {"date_from": "2026-07-20", "date_to": "2026-07-20"},
             {"user_id": worker.client_id})
    )

    paused = [s for s in result["segments"] if s["state"] == "paused"]
    assert paused, "expected a paused segment"
    assert paused[0]["reason"] == own_reason.client_id, (
        "an unresolvable catalog id must not become the segment key"
    )
    assert foreign_reason.client_id not in json.dumps(result), (
        "a foreign workspace's pause reason id must not appear anywhere in the response"
    )
    assert foreign_reason.client_id not in result["timeline"]["pause_by_reason"]
    # NOT asserted here: that EVERY `pause_by_reason` key resolves in this endpoint's
    # `pause_reasons` map. That map is built from step records only, so a worker-level
    # reason with no matching step reason is unresolvable — verified **pre-existing** by
    # running this exact scenario against the unmodified tree at 26d290d, where the
    # segment-key assertion above passes and the map assertion fails identically. Phase 1
    # must not repair it (criterion 17); recorded as a finding instead. The kiosk
    # clock-out endpoint, whose contract DOES guarantee full resolution, is covered by
    # `test_clock_out_analytics_resolves_transition_and_unspecified_keys`.


async def test_breakdown_prefers_the_catalog_reason_when_a_row_carries_both(db_session) -> None:
    """Criterion 13 at the query layer — the catalog id wins the bucket key."""
    workspace = Workspace(name=f"tr-breakdown-both-{uuid4().hex}")
    db_session.add(workspace)
    await db_session.flush()
    worker = await _seed_worker(db_session, workspace.client_id)
    reason = PauseReason(
        workspace_id=workspace.client_id,
        name=f"Supplier-{uuid4().hex[:6]}",
        pause_type=PauseTypeEnum.BLOCKER,
    )
    db_session.add(reason)
    await db_session.flush()
    base = datetime(2026, 7, 19, 9, tzinfo=timezone.utc)
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.STARTED_SHIFT, base, base)
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.IN_PAUSE, base, base + timedelta(hours=1),
                  reason=reason.client_id, transition_reason=OTHER_TASK_PRIORITY)
    await _step_record(
        db_session, workspace.client_id, worker.client_id,
        TaskStepStateEnum.PAUSED, base, base + timedelta(hours=1),
        pause_reason_id=reason.client_id, transition_reason=OTHER_TASK_PRIORITY,
    )
    await db_session.flush()

    result = await get_worker_linear_timeline_breakdown(
        _ctx(db_session, workspace.client_id,
             {"date_from": "2026-07-19", "date_to": "2026-07-19"},
             {"user_id": worker.client_id})
    )

    paused = [s for s in result["segments"] if s["state"] == "paused"]
    assert paused and paused[0]["reason"] == reason.client_id
    assert paused[0]["steps"][0]["pause_reason"]["client_id"] == reason.client_id
