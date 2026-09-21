"""Plan 10 — `sync_task_stock_assignments` wired at S1-S9 (master plan §6.5;
intention §5B MC-2).

F0 (master plan §6.8) plus a worker **Wk**; `MAP` = `ASSIGNMENT_STATE_BY_TASK_STATE`.
`CR(...)` creates an assignment through the real command (plan 8 §6). This file
builds the sync's behaviour and exercises a representative site per distinct code
path — S1 (`transition_step_state`), S4/S5/S6 (the three terminal task commands,
symmetric fixtures), S8 (`remove_task_step`), plus the terminal-skip and `=`-cell
invariants driven directly through `move_assignment` + `sync_task_stock_assignments`
where building the real S2/S3/S7/S9 command fixture is out of this round's budget
(named plainly in the implementer handoff; the tester owns the rest of plan 10's
criteria table).
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select

from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.domain.stock_report.enums import StockTaskAssignmentStateEnum as S
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.models.tables.history.history_record import HistoryRecord
from beyo_manager.models.tables.history.history_record_link import HistoryRecordLink
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.commands.stock_report._move_assignment import (
    move_assignment,
)
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from beyo_manager.services.commands.stock_report.sync_task_stock_assignments import (
    sync_task_stock_assignments,
)
from beyo_manager.services.commands.task_steps.remove_task_step import remove_task_step
from beyo_manager.services.commands.tasks.cancel_task import cancel_task
from beyo_manager.services.commands.tasks.fail_task import fail_task
from beyo_manager.services.commands.tasks.resolve_task import resolve_task
from tests.helpers.stock_report import (
    assert_stock_report_clean,
    capture_dispatch,
    make_ctx,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
SCANNER_KEY = "test-task-sync-scanner-key"


async def _make_row(db_session, seeded, *, criteria=None, quantity_requested=10):
    criteria = criteria if criteria is not None else {"wood_group": ["teak"]}
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties=criteria,
        properties_signature=compute_stock_criteria_signature(criteria),
        quantity_requested=quantity_requested,
    )
    db_session.add(row)
    await db_session.flush()
    return row


async def _CR(db_session, seeded, row, task, item):
    ctx = make_ctx(
        db_session,
        seeded,
        role_name="worker",
        incoming_data={
            "entries": [
                {
                    "stock_report_item_id": row.client_id,
                    "task_id": task.client_id,
                    "item_id": item.client_id,
                    "override_property_mismatch": False,
                }
            ]
        },
    )
    result = await create_stock_task_assignments(ctx)
    return result["stock_task_assignments"][0]["client_id"]


async def _fresh_assignment(db_session, client_id):
    return (
        await db_session.execute(
            select(StockTaskAssignment)
            .where(StockTaskAssignment.client_id == client_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


async def _fresh_task(db_session, client_id):
    return (
        await db_session.execute(
            select(Task).where(Task.client_id == client_id).execution_options(populate_existing=True)
        )
    ).scalar_one()


async def _counters(db_session, row_id):
    return (
        await db_session.execute(
            select(
                StockReportItem.quantity_in_queue,
                StockReportItem.quantity_in_progress,
                StockReportItem.quantity_awaiting,
            ).where(StockReportItem.client_id == row_id)
        )
    ).one()


async def _cleanup_task_side_effects(db_session, seeded):
    """Beyond `purge_stock_report_workspace`'s own tables: the terminal task
    commands write a generic `HistoryRecord` (created_by_id FK, checked
    immediately despite `deferrable=True`), and this file's S1/S8 fixtures add
    their own `TaskStep`/`StepStateRecord`/`WorkingSection` rows (RESTRICT FK on
    `tasks`). Both must go before `purge_stock_report_workspace` deletes tasks
    and users."""
    return await _cleanup_task_side_effects_by_ids(
        db_session,
        seeded.workspace.client_id,
        [seeded.manager.client_id, seeded.worker.client_id],
    )


async def _cleanup_task_side_effects_by_ids(db_session, workspace_id, user_ids):
    history_record_ids = (
        await db_session.execute(
            select(HistoryRecord.client_id).where(
                HistoryRecord.created_by_id.in_(user_ids)
            )
        )
    ).scalars().all()
    if history_record_ids:
        await db_session.execute(
            delete(HistoryRecordLink).where(
                HistoryRecordLink.history_record_id.in_(history_record_ids)
            )
        )
        await db_session.execute(
            delete(HistoryRecord).where(HistoryRecord.client_id.in_(history_record_ids))
        )
    # Circular RESTRICT: task_steps.latest_state_record_id -> step_state_records,
    # step_state_records.step_id -> task_steps. Null the former before deleting
    # either.
    await db_session.execute(
        TaskStep.__table__.update()
        .where(TaskStep.workspace_id == workspace_id)
        .values(latest_state_record_id=None)
    )
    await db_session.execute(
        delete(StepStateRecord).where(StepStateRecord.workspace_id == workspace_id)
    )
    await db_session.execute(
        delete(TaskStep).where(TaskStep.workspace_id == workspace_id)
    )
    await db_session.execute(
        delete(WorkingSection).where(WorkingSection.workspace_id == workspace_id)
    )


async def _terminal_ctx(db_session, seeded, task):
    return make_ctx(
        db_session,
        seeded,
        role_name="manager",
        incoming_data={"client_id": task.client_id},
    )


# --- fixture kit shared by the S1/S2/S7/S8/S9 rows -------------------------


async def _section(db_session, seeded, name, *, batch=False):
    section = WorkingSection(
        workspace_id=seeded.workspace.client_id,
        name=name,
        allows_batch_working=batch,
        created_by_id=seeded.manager.client_id,
    )
    db_session.add(section)
    await db_session.flush()
    return section


async def _add_step(db_session, seeded, task, section, *, state, sequence_order=1):
    from beyo_manager.domain.task_steps.enums import TaskStepStateEnum  # noqa: F401

    step = TaskStep(
        workspace_id=seeded.workspace.client_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        working_section_name_snapshot=section.name,
        allows_batch_working=section.allows_batch_working,
        state=state,
        readiness_status="ready",
        total_dependencies=0,
        completed_dependencies=0,
        sequence_order=sequence_order,
        created_by_id=seeded.manager.client_id,
    )
    db_session.add(step)
    await db_session.flush()
    record = StepStateRecord(
        workspace_id=seeded.workspace.client_id,
        step_id=step.client_id,
        state=state,
        entered_at=NOW,
        exited_at=None,
        created_by_id=seeded.manager.client_id,
    )
    db_session.add(record)
    await db_session.flush()
    step.latest_state_record_id = record.client_id
    await db_session.flush()
    return step


async def _set_task_state(db_session, task, state):
    """Set T's state in the fixture. The session runs `expire_on_commit=False`, so a
    raw Core UPDATE alone leaves the identity-mapped instance stale and the command
    under test reads the OLD state — the fixture must move both."""
    await db_session.execute(
        Task.__table__.update().where(Task.client_id == task.client_id).values(state=state)
    )
    task.state = state
    await db_session.flush()


async def _second_task_and_item(db_session, seeded, suffix, *, quantity=4):
    from sqlalchemy import func

    from beyo_manager.domain.items.enums import ItemStateEnum
    from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskTypeEnum
    from beyo_manager.models.tables.items.item import Item
    from beyo_manager.models.tables.tasks.task_item import TaskItem

    next_scalar_id = (
        await db_session.scalar(
            select(func.max(Task.task_scalar_id)).where(
                Task.workspace_id == seeded.workspace.client_id
            )
        )
        or 0
    ) + 1
    task = Task(
        client_id=f"tsk_{suffix}_{seeded.workspace.client_id}",
        workspace_id=seeded.workspace.client_id,
        task_scalar_id=next_scalar_id,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=seeded.manager.client_id,
    )
    item = Item(
        client_id=f"itm_{suffix}_{seeded.workspace.client_id}",
        workspace_id=seeded.workspace.client_id,
        article_number=f"{suffix}-{seeded.workspace.client_id}",
        state=ItemStateEnum.PENDING,
        quantity=quantity,
        item_category_id=seeded.categories[0].client_id,
        properties={"wood_type": "Teak", "upholstery": "Down"},
    )
    db_session.add_all([task, item])
    await db_session.flush()
    db_session.add(
        TaskItem(
            client_id=f"tim_{suffix}_{seeded.workspace.client_id}",
            workspace_id=seeded.workspace.client_id,
            task_id=task.client_id,
            item_id=item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=seeded.manager.client_id,
        )
    )
    await db_session.flush()
    return task, item


async def _make_goal(db_session, seeded, row):
    from beyo_manager.domain.stock_report.enums import StockReportHistoryRecordTypeEnum
    from beyo_manager.models.tables.stock_report.stock_report_history_record import (
        StockReportHistoryRecord,
    )

    record = StockReportHistoryRecord(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        type=StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
        quantity_requested=row.quantity_requested,
        quantity_awaiting=0,
        created_at=NOW,
    )
    db_session.add(record)
    await db_session.flush()
    return record


async def _goal_awaiting(db_session, goal_id):
    from beyo_manager.models.tables.stock_report.stock_report_history_record import (
        StockReportHistoryRecord,
    )

    return await db_session.scalar(
        select(StockReportHistoryRecord.quantity_awaiting).where(
            StockReportHistoryRecord.client_id == goal_id
        )
    )


# ---------------------------------------------------------------------------
# S1 — transition_step_state (advance a step; a real step + record needed)
# ---------------------------------------------------------------------------


async def test_s1_transition_step_state_advances_the_assignment(db_session, monkeypatch):
    from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
    from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
    from beyo_manager.models.tables.tasks.task_step import TaskStep
    from beyo_manager.services.commands.task_steps.transition_step_state import (
        transition_step_state,
    )

    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)

    # A working section is not required by the step model directly, but a step
    # needs a working_section_id; reuse an existing one if the seed doesn't carry
    # one — F0 doesn't seed a WorkingSection, so build the step without one is not
    # possible. Build the smallest legal step instead.
    from beyo_manager.models.tables.working_sections.working_section import WorkingSection

    section = WorkingSection(
        workspace_id=seeded.workspace.client_id,
        name="S1 section",
        allows_batch_working=False,
        created_by_id=seeded.manager.client_id,
    )
    db_session.add(section)
    await db_session.flush()
    step = TaskStep(
        workspace_id=seeded.workspace.client_id,
        task_id=seeded.task.client_id,
        working_section_id=section.client_id,
        working_section_name_snapshot=section.name,
        state=TaskStepStateEnum.PENDING,
        readiness_status="ready",
        total_dependencies=0,
        completed_dependencies=0,
        sequence_order=1,
        created_by_id=seeded.manager.client_id,
    )
    db_session.add(step)
    await db_session.flush()
    record = StepStateRecord(
        workspace_id=seeded.workspace.client_id,
        step_id=step.client_id,
        state=TaskStepStateEnum.PENDING,
        entered_at=NOW,
        exited_at=None,
        created_by_id=seeded.manager.client_id,
    )
    db_session.add(record)
    await db_session.flush()
    step.latest_state_record_id = record.client_id
    # maybe_advance_task_to_working only fires from ASSIGNED (a step already
    # exists here, which is what add_task_steps would have produced).
    await db_session.execute(
        Task.__table__.update()
        .where(Task.client_id == seeded.task.client_id)
        .values(state=TaskStateEnum.ASSIGNED)
    )
    await db_session.flush()

    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        ctx = make_ctx(
            db_session,
            seeded,
            role_name="worker",
            incoming_data={"step_id": step.client_id, "task_id": seeded.task.client_id, "new_state": "working"},
        )
        await transition_step_state(ctx)

        task_after = await _fresh_task(db_session, seeded.task.client_id)
        assert task_after.state == TaskStateEnum.WORKING
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.IN_PROGRESS
        assert await _counters(db_session, row.client_id) == (0, 4, 0)

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C1(m) — a task carrying a terminal AND an active assignment: the discovery
# query must select the live one, never whichever row the database returns
# first (review F-1/F-5, owner card 1; intention §14F F1,
# `uix_stock_task_assignments_task_active`).
# ---------------------------------------------------------------------------


async def test_c1m_sync_selects_the_active_assignment_over_a_terminal_one(
    db_session, monkeypatch
):
    """A task may legitimately carry a terminal assignment **and** an active one:
    §14F F1 says a terminal assignment does not block a new assignment, and
    `uix_stock_task_assignments_task_active`'s partial unique index constrains
    only the three *active* states, never "at most one, period". A1 fails
    (terminal); A2 is a fresh assignment created afterwards for the same
    `(task, item, row)` — the exact story review finding F-1 reproduced (a job
    fails, a step removal re-opens it, Scanner re-assigns the same item). Driving
    T through S1 (`in_queue -> working`) must move **A2 only**, with exactly one
    `stock_task_assignment:state-changed` for A2 and one `:updated` for R; A1
    must not appear in either the state read or the dispatched events."""
    from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
    from beyo_manager.services.commands.task_steps.transition_step_state import (
        transition_step_state,
    )

    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    section = await _section(db_session, seeded, "C1m section")
    step = await _add_step(
        db_session, seeded, seeded.task, section, state=TaskStepStateEnum.PENDING
    )
    # maybe_advance_task_to_working only fires from ASSIGNED (same precondition
    # as the S1 test above); both assignments are created while T is ASSIGNED.
    await _set_task_state(db_session, seeded.task, TaskStateEnum.ASSIGNED)

    a1_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    a1 = await _fresh_assignment(db_session, a1_id)
    await move_assignment(
        db_session, a1, S.FAILED,
        workspace_id=seeded.workspace.client_id, actor_user_id=seeded.manager.client_id,
        now=NOW, trigger="test",
    )
    a2_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        a1_before = await _fresh_assignment(db_session, a1_id)
        assert a1_before.state == S.FAILED
        a2_before = await _fresh_assignment(db_session, a2_id)
        assert a2_before.state == S.IN_QUEUE

        captured = capture_dispatch(
            monkeypatch,
            "beyo_manager.services.commands.task_steps.transition_step_state.event_bus.dispatch",
        )
        ctx = make_ctx(
            db_session, seeded, role_name="worker",
            incoming_data={"step_id": step.client_id, "task_id": seeded.task.client_id, "new_state": "working"},
        )
        await transition_step_state(ctx)

        task_after = await _fresh_task(db_session, seeded.task.client_id)
        assert task_after.state == TaskStateEnum.WORKING

        a1_after = await _fresh_assignment(db_session, a1_id)
        assert a1_after.state == S.FAILED  # untouched
        a2_after = await _fresh_assignment(db_session, a2_id)
        assert a2_after.state == S.IN_PROGRESS
        assert await _counters(db_session, row.client_id) == (0, 4, 0)

        state_changed = [
            event
            for event in captured
            if event.event_name == "stock_task_assignment:state-changed"
        ]
        assert [event.client_id for event in state_changed] == [a2_id]
        assert state_changed[0].extra["state"] == "in_progress"
        updated = [
            event
            for event in captured
            if event.event_name == "stock_report_item:updated"
            and event.client_id == row.client_id
        ]
        assert len(updated) == 1

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# S4/S5/S6 — the three terminal task commands (symmetric fixture)
# ---------------------------------------------------------------------------


async def test_s4_resolve_task_moves_in_progress_to_awaiting(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await db_session.commit()

    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id, actor_user_id=seeded.manager.client_id,
        now=NOW, trigger="test",
    )
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        ctx = await _terminal_ctx(db_session, seeded, seeded.task)
        await resolve_task(ctx)

        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.AWAITING
        assert await _counters(db_session, row.client_id) == (0, 0, 4)

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_s5_fail_task_moves_the_assignment_to_failed(db_session, monkeypatch):
    """C1(g): S5 `fail_task` **from working** (A `in_progress`) -> A `failed`,
    counters `(0, 0, 0)`."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id, actor_user_id=seeded.manager.client_id,
        now=NOW, trigger="test",
    )
    await _set_task_state(db_session, seeded.task, TaskStateEnum.WORKING)
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        assert await _counters(db_session, row.client_id) == (0, 4, 0)
        ctx = await _terminal_ctx(db_session, seeded, seeded.task)
        await fail_task(ctx)

        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.FAILED
        assert await _counters(db_session, row.client_id) == (0, 0, 0)

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_s6_cancel_task_moves_the_assignment_to_failed(db_session, monkeypatch):
    """C1(h): S6 `cancel_task` **from assigned** (A `in_queue`, MAP[assigned]) ->
    A `failed`."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await _set_task_state(db_session, seeded.task, TaskStateEnum.ASSIGNED)
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        assert await _counters(db_session, row.client_id) == (4, 0, 0)
        ctx = await _terminal_ctx(db_session, seeded, seeded.task)
        await cancel_task(ctx)

        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.FAILED
        assert await _counters(db_session, row.client_id) == (0, 0, 0)

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c6a_credited_user_is_the_performer_not_a_third_party(db_session, monkeypatch):
    """C6(a) (MC-17): S1, performed by the manager **M** while the step's work is
    credited to the worker **Wk**. The assignment carries the PERFORMER.

    The two identities must be different, and both must be present, or the row
    cannot fail: a fixture with no `credited_user_id` at all is satisfied by a sync
    that reads the credited user (charter rule 2's companion)."""
    from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
    from beyo_manager.services.commands.task_steps.transition_step_state import (
        transition_step_state,
    )

    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    section = await _section(db_session, seeded, "C6a section")
    step = await _add_step(
        db_session, seeded, seeded.task, section, state=TaskStepStateEnum.PENDING
    )
    await _set_task_state(db_session, seeded.task, TaskStateEnum.ASSIGNED)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        assert seeded.manager.client_id != seeded.worker.client_id
        ctx = make_ctx(
            db_session, seeded, role_name="manager", user=seeded.manager,
            incoming_data={
                "step_id": step.client_id,
                "task_id": seeded.task.client_id,
                "new_state": "working",
                "credited_user_id": seeded.worker.client_id,
            },
        )
        await transition_step_state(ctx)

        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.IN_PROGRESS
        assert assignment.updated_by_id == seeded.manager.client_id
        assert assignment.updated_by_id != seeded.worker.client_id

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# S8 — remove_task_step (the row's own state write is inside the shared helper)
# ---------------------------------------------------------------------------


async def test_s8_remove_task_step_moves_in_progress_to_in_queue(db_session, monkeypatch):
    from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
    from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
    from beyo_manager.models.tables.tasks.task_step import TaskStep
    from beyo_manager.models.tables.working_sections.working_section import WorkingSection

    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    section = WorkingSection(
        workspace_id=seeded.workspace.client_id,
        name="S8 section",
        allows_batch_working=False,
        created_by_id=seeded.manager.client_id,
    )
    db_session.add(section)
    await db_session.flush()
    step = TaskStep(
        workspace_id=seeded.workspace.client_id,
        task_id=seeded.task.client_id,
        working_section_id=section.client_id,
        working_section_name_snapshot=section.name,
        state=TaskStepStateEnum.WORKING,
        readiness_status="ready",
        total_dependencies=0,
        completed_dependencies=0,
        sequence_order=1,
        created_by_id=seeded.manager.client_id,
    )
    db_session.add(step)
    await db_session.flush()
    record = StepStateRecord(
        workspace_id=seeded.workspace.client_id,
        step_id=step.client_id,
        state=TaskStepStateEnum.WORKING,
        entered_at=NOW,
        exited_at=None,
        created_by_id=seeded.manager.client_id,
    )
    db_session.add(record)
    await db_session.flush()
    step.latest_state_record_id = record.client_id
    await db_session.execute(
        Task.__table__.update()
        .where(Task.client_id == seeded.task.client_id)
        .values(state=TaskStateEnum.WORKING)
    )
    await db_session.flush()

    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id, actor_user_id=seeded.manager.client_id,
        now=NOW, trigger="test",
    )
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        ctx = make_ctx(
            db_session, seeded, role_name="manager",
            incoming_data={"task_id": seeded.task.client_id, "step_id": step.client_id},
        )
        await remove_task_step(ctx)

        task_after = await _fresh_task(db_session, seeded.task.client_id)
        assert task_after.state == TaskStateEnum.PENDING
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.IN_QUEUE
        assert await _counters(db_session, row.client_id) == (4, 0, 0)

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# Terminal-skip invariant (C3 family) and the `=` no-op — driven directly
# through the sync function, since a fixture through S4/S9's own resolution
# path (Scanner webhook, phase 9) is already covered in test_process_items_processed.
# ---------------------------------------------------------------------------


async def test_sync_never_moves_a_resolved_early_assignment(db_session, monkeypatch):
    """§14F F3: a resolved_early assignment stays put whatever the task does."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.RESOLVED_EARLY,
        workspace_id=seeded.workspace.client_id, actor_user_id=None,
        now=NOW, trigger="test",
    )
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        assignment = await _fresh_assignment(db_session, assignment_id)
        old_state = seeded.task.state  # pending
        events = await sync_task_stock_assignments(
            db_session,
            [(seeded.task, old_state)],
            workspace_id=workspace_id,
            actor_user_id=seeded.manager.client_id,
            now=NOW,
        )
        assert events == []
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.RESOLVED_EARLY

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_sync_no_ops_when_the_assignment_is_already_at_target(db_session, monkeypatch):
    """The `=` cell: no move, no event, when the assignment is already at MAP[task.state]."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await db_session.commit()  # A is in_queue, T is pending -> MAP[pending] == in_queue

    workspace_id = seeded.workspace.client_id
    try:
        events = await sync_task_stock_assignments(
            db_session,
            [(seeded.task, seeded.task.state)],
            workspace_id=workspace_id,
            actor_user_id=seeded.manager.client_id,
            now=NOW,
        )
        assert events == []
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.IN_QUEUE

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C1(b) — S1's other exit: the last step completes, T goes `ready`, and MAP
# sends the assignment to `awaiting` (the HC-4 cell) with the goal credited.
# ---------------------------------------------------------------------------


async def test_c1b_s1_last_step_completed_sends_the_assignment_to_awaiting(
    db_session, monkeypatch
):
    from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
    from beyo_manager.services.commands.task_steps.transition_step_state import (
        transition_step_state,
    )

    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row)
    section = await _section(db_session, seeded, "C1b section")
    step = await _add_step(
        db_session, seeded, seeded.task, section, state=TaskStepStateEnum.WORKING
    )
    await _set_task_state(db_session, seeded.task, TaskStateEnum.WORKING)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id, actor_user_id=seeded.manager.client_id,
        now=NOW, trigger="test",
    )
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        ctx = make_ctx(
            db_session, seeded, role_name="worker",
            incoming_data={
                "step_id": step.client_id,
                "task_id": seeded.task.client_id,
                "new_state": "completed",
            },
        )
        await transition_step_state(ctx)

        task_after = await _fresh_task(db_session, seeded.task.client_id)
        assert task_after.state == TaskStateEnum.READY
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.AWAITING
        assert await _counters(db_session, row.client_id) == (0, 0, 4)
        assert await _goal_awaiting(db_session, goal.client_id) == 4

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C1(c) — S2 `transition_step_state_batch`: two tasks on one row R advance
# together; the row gets exactly ONE `:updated` for the whole batch.
# ---------------------------------------------------------------------------


async def test_c1c_s2_batch_two_tasks_on_one_row_emit_one_updated(db_session, monkeypatch):
    from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
    from beyo_manager.services.commands.task_steps.transition_step_state_batch import (
        transition_step_state_batch,
    )

    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    section = await _section(db_session, seeded, "C1c section", batch=True)
    pairs = []
    for index in range(2):
        task, item = await _second_task_and_item(db_session, seeded, f"c1c{index}")
        step = await _add_step(
            db_session, seeded, task, section, state=TaskStepStateEnum.PENDING
        )
        assignment_id = await _CR(db_session, seeded, row, task, item)
        await _set_task_state(db_session, task, TaskStateEnum.ASSIGNED)
        pairs.append((task, step, assignment_id))
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        captured = capture_dispatch(
            monkeypatch,
            "beyo_manager.services.commands.task_steps.transition_step_state_batch.event_bus.dispatch",
        )
        ctx = make_ctx(
            db_session, seeded, role_name="worker",
            incoming_data={
                "items": [
                    {"task_id": task.client_id, "step_id": step.client_id}
                    for task, step, _ in pairs
                ],
                "new_state": "working",
            },
        )
        await transition_step_state_batch(ctx)
        for task, _step, assignment_id in pairs:
            task_after = await _fresh_task(db_session, task.client_id)
            assert task_after.state == TaskStateEnum.WORKING
            assignment = await _fresh_assignment(db_session, assignment_id)
            assert assignment.state == S.IN_PROGRESS
        assert await _counters(db_session, row.client_id) == (0, 8, 0)

        updated = [
            event
            for event in captured
            if event.event_name == "stock_report_item:updated"
            and event.client_id == row.client_id
        ]
        assert len(updated) == 1, f"{len(updated)} :updated events for R"

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C1(d) — S3 `force_task_ready`: T `pending`, A `in_queue` -> A `awaiting`.
# ---------------------------------------------------------------------------


async def test_c1d_s3_force_task_ready_moves_in_queue_to_awaiting(db_session, monkeypatch):
    from beyo_manager.services.commands.tasks.force_task_ready import force_task_ready

    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        ctx = make_ctx(
            db_session, seeded, role_name="manager",
            incoming_data={"client_id": seeded.task.client_id, "reason": "C1(d)"},
        )
        await force_task_ready(ctx)

        task_after = await _fresh_task(db_session, seeded.task.client_id)
        assert task_after.state == TaskStateEnum.READY
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.AWAITING
        assert await _counters(db_session, row.client_id) == (0, 0, 4)

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C1(f) / C1(i) — the MC-2 step-5 `=` cell at a real command boundary: the task
# moves, `MAP[T.state]` is where the assignment already is, so nothing is
# written and **no stock event** is emitted.
# ---------------------------------------------------------------------------


async def test_c1f_s4_resolve_task_from_ready_leaves_awaiting_untouched(
    db_session, monkeypatch
):
    """C1(f): S4 from `ready` — MAP[resolved] is `awaiting` and A is already
    `awaiting`, so the sync writes nothing and emits no stock event."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.AWAITING,
        workspace_id=seeded.workspace.client_id, actor_user_id=seeded.manager.client_id,
        now=NOW, trigger="test",
    )
    await _set_task_state(db_session, seeded.task, TaskStateEnum.READY)
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        captured = capture_dispatch(
            monkeypatch,
            "beyo_manager.services.commands.tasks.resolve_task.event_bus.dispatch",
        )
        await resolve_task(await _terminal_ctx(db_session, seeded, seeded.task))

        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.AWAITING
        assert await _counters(db_session, row.client_id) == (0, 0, 4)
        stock_events = [
            event for event in captured if event.event_name.startswith("stock_")
        ]
        assert stock_events == []

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c1i_s7_add_task_steps_on_pending_leaves_in_queue_untouched(
    db_session, monkeypatch
):
    """C1(i): S7 on T `pending` -> T `assigned`; MAP[assigned] is `in_queue` and A
    is already `in_queue`, so no write and **no stock event**."""
    from beyo_manager.services.commands.task_steps.add_task_steps import add_task_steps

    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    section = await _section(db_session, seeded, "C1i section")
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        captured = capture_dispatch(
            monkeypatch,
            "beyo_manager.services.commands.task_steps.add_task_steps.event_bus.dispatch",
        )
        ctx = make_ctx(
            db_session, seeded, role_name="manager",
            incoming_data={
                "task_id": seeded.task.client_id,
                "steps": [{"working_section_id": section.client_id}],
            },
        )
        await add_task_steps(ctx)

        task_after = await _fresh_task(db_session, seeded.task.client_id)
        assert task_after.state == TaskStateEnum.ASSIGNED
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.IN_QUEUE
        assert await _counters(db_session, row.client_id) == (4, 0, 0)
        stock_events = [
            event for event in captured if event.event_name.startswith("stock_")
        ]
        assert stock_events == []

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c1j_s7_add_task_steps_reopens_ready_and_uncredits_the_goal(
    db_session, monkeypatch
):
    """C1(j): S7 on T `ready` (A `awaiting`, credited) reopens T to `working`; the
    assignment follows to `in_progress`, the goal credit is returned (`G == 0`) and
    the credit memory is cleared (MC-5 row 4)."""
    from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
    from beyo_manager.services.commands.task_steps.add_task_steps import add_task_steps

    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row)
    section = await _section(db_session, seeded, "C1j section")
    await _add_step(
        db_session, seeded, seeded.task, section, state=TaskStepStateEnum.COMPLETED
    )
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.AWAITING,
        workspace_id=seeded.workspace.client_id, actor_user_id=seeded.manager.client_id,
        now=NOW, trigger="test",
    )
    await _set_task_state(db_session, seeded.task, TaskStateEnum.READY)
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        assert await _goal_awaiting(db_session, goal.client_id) == 4
        ctx = make_ctx(
            db_session, seeded, role_name="manager",
            incoming_data={
                "task_id": seeded.task.client_id,
                "steps": [{"working_section_id": section.client_id}],
            },
        )
        await add_task_steps(ctx)

        task_after = await _fresh_task(db_session, seeded.task.client_id)
        assert task_after.state == TaskStateEnum.WORKING
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.IN_PROGRESS
        assert await _counters(db_session, row.client_id) == (0, 4, 0)
        assert await _goal_awaiting(db_session, goal.client_id) == 0
        assert assignment.credited_history_record_id is None

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C1(l) — S9 `handle_finalize_pending_step_completion`, driven directly. This
# handler has no `ctx`: the actor is the payload's own performer (MC-17), which
# is the clause this row pins.
# ---------------------------------------------------------------------------


class _NestedTxSession:
    """The handler owns its transaction (`async with session.begin()`), which cannot
    be opened on a session the fixture has already written through; mapping it onto a
    SAVEPOINT keeps its commit semantics under the fixture's outer rollback.
    Precedent: `test_finalize_pending_step_completion_integration.py`."""

    def __init__(self, session):
        self._session = session

    def __getattr__(self, name):
        return getattr(self._session, name)

    def begin(self):
        return self._session.begin_nested()


async def test_c1l_s9_finalize_credits_the_payloads_performer(db_session, monkeypatch):
    from collections.abc import AsyncIterator

    from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
    from beyo_manager.services.tasks.task_steps import (
        finalize_pending_step_completion as module,
    )

    async def _fake_get_db_session() -> AsyncIterator[object]:
        yield _NestedTxSession(db_session)

    async def _noop_create_instant_task(**_kwargs):
        return None

    async def _noop_targets(*_args, **_kwargs):
        return []

    async def _dispatch(_events):
        return None

    monkeypatch.setattr(module, "get_db_session", _fake_get_db_session)
    monkeypatch.setattr(module, "create_instant_task", _noop_create_instant_task)
    monkeypatch.setattr(module, "resolve_task_step_notification_targets", _noop_targets)
    monkeypatch.setattr(module.event_bus, "dispatch", _dispatch)

    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    section = await _section(db_session, seeded, "C1l section")
    step = await _add_step(
        db_session, seeded, seeded.task, section, state=TaskStepStateEnum.WORKING
    )
    await _set_task_state(db_session, seeded.task, TaskStateEnum.WORKING)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id, actor_user_id=seeded.manager.client_id,
        now=NOW, trigger="test",
    )
    await db_session.flush()

    # The performer is Wk; the credited user is the manager. MC-17: the assignment
    # carries the PERFORMER.
    payload = {
        "step_id": step.client_id,
        "task_id": seeded.task.client_id,
        "workspace_id": seeded.workspace.client_id,
        "completion_requested_at": NOW.isoformat(),
        "performed_by_user_id": seeded.worker.client_id,
        "credited_user_id": seeded.manager.client_id,
        "pause_reason_id": None,
        "description": None,
    }
    await module.handle_finalize_pending_step_completion(payload, "exec_c1l")

    task_after = await _fresh_task(db_session, seeded.task.client_id)
    assert task_after.state == TaskStateEnum.READY
    assignment = await _fresh_assignment(db_session, assignment_id)
    assert assignment.state == S.AWAITING
    assert assignment.updated_by_id == payload["performed_by_user_id"]


# ---------------------------------------------------------------------------
# C2(a) — UNFAILABLE BY DESIGN (owner ruling, 2026-09-21, card 2): kept as a
# cheap regression guard. Its real evidence is the C4 registry guard, which
# refuses a sync call inside the three shared helpers.
# ---------------------------------------------------------------------------


async def test_c2a_s8_removing_one_of_two_completed_steps_keeps_ready_untouched(
    db_session, monkeypatch
):
    from beyo_manager.domain.task_steps.enums import TaskStepStateEnum

    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row)
    section = await _section(db_session, seeded, "C2a section")
    step_one = await _add_step(
        db_session, seeded, seeded.task, section,
        state=TaskStepStateEnum.COMPLETED, sequence_order=1,
    )
    await _add_step(
        db_session, seeded, seeded.task, section,
        state=TaskStepStateEnum.COMPLETED, sequence_order=2,
    )
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.AWAITING,
        workspace_id=seeded.workspace.client_id, actor_user_id=seeded.manager.client_id,
        now=NOW, trigger="test",
    )
    await _set_task_state(db_session, seeded.task, TaskStateEnum.READY)
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        assignment = await _fresh_assignment(db_session, assignment_id)
        memory_before = assignment.credited_history_record_id
        captured = capture_dispatch(
            monkeypatch,
            "beyo_manager.services.commands.task_steps.remove_task_step.event_bus.dispatch",
        )
        ctx = make_ctx(
            db_session, seeded, role_name="manager",
            incoming_data={
                "task_id": seeded.task.client_id,
                "step_id": step_one.client_id,
            },
        )
        await remove_task_step(ctx)

        task_after = await _fresh_task(db_session, seeded.task.client_id)
        assert task_after.state == TaskStateEnum.READY
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.AWAITING
        assert await _goal_awaiting(db_session, goal.client_id) == 4
        assert assignment.credited_history_record_id == memory_before
        assert [
            event for event in captured if event.event_name.startswith("stock_")
        ] == []

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C3 — the sync never moves a TERMINAL assignment, whatever the task does
# (§5 r1, §14F F3). Fixtures resolve through the real Scanner webhook (`PR`).
# ---------------------------------------------------------------------------


def _pr_ctx(session, numbers):
    import json

    from beyo_manager.services.context import ServiceContext

    body = json.dumps([{"article_number": n} for n in numbers]).encode("utf-8")
    return ServiceContext(
        identity={},
        incoming_data={"raw_body": body, "headers": {"x-api-key": SCANNER_KEY}},
        session=session,
        now=NOW,
    )


async def _resolve_via_scanner(db_session, seeded, monkeypatch, numbers):
    from beyo_manager.config import settings
    from beyo_manager.services.commands.stock_report.process_items_processed import (
        process_items_processed,
    )

    monkeypatch.setattr(settings, "manager_api_key_to_location_tracker_app", SCANNER_KEY)
    monkeypatch.setattr(
        settings, "location_tracker_webhook_workspace_id", seeded.workspace.client_id
    )
    return await process_items_processed(_pr_ctx(db_session, numbers))


async def test_c3a_s7_reopen_never_moves_a_resolved_assignment(db_session, monkeypatch):
    """C3(a): T `ready`, Scanner resolves A, then S7 reopens the task — A stays
    `resolved`, counters unchanged, no stock event."""
    from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
    from beyo_manager.services.commands.task_steps.add_task_steps import add_task_steps

    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    section = await _section(db_session, seeded, "C3a section")
    await _add_step(
        db_session, seeded, seeded.task, section, state=TaskStepStateEnum.COMPLETED
    )
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.AWAITING,
        workspace_id=seeded.workspace.client_id, actor_user_id=seeded.manager.client_id,
        now=NOW, trigger="test",
    )
    await _set_task_state(db_session, seeded.task, TaskStateEnum.READY)
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        response = await _resolve_via_scanner(
            db_session, seeded, monkeypatch, [seeded.item.article_number]
        )
        assert response["results"][0]["outcome"] == "resolved"
        counters_before = await _counters(db_session, row.client_id)
        await db_session.commit()

        captured = capture_dispatch(
            monkeypatch,
            "beyo_manager.services.commands.task_steps.add_task_steps.event_bus.dispatch",
        )
        ctx = make_ctx(
            db_session, seeded, role_name="manager",
            incoming_data={
                "task_id": seeded.task.client_id,
                "steps": [{"working_section_id": section.client_id}],
            },
        )
        await add_task_steps(ctx)

        task_after = await _fresh_task(db_session, seeded.task.client_id)
        assert task_after.state == TaskStateEnum.WORKING
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.RESOLVED
        assert await _counters(db_session, row.client_id) == counters_before
        assert [
            event for event in captured if event.event_name.startswith("stock_")
        ] == []

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c3b_s8_reopen_never_moves_a_failed_assignment(db_session, monkeypatch):
    """C3(b): A `failed` (T failed); `remove_task_step` takes T back to `pending`
    (the X1 path) — A stays `failed`, no stock event."""
    from beyo_manager.domain.task_steps.enums import TaskStepStateEnum

    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    section = await _section(db_session, seeded, "C3b section")
    step = await _add_step(
        db_session, seeded, seeded.task, section, state=TaskStepStateEnum.WORKING
    )
    await _set_task_state(db_session, seeded.task, TaskStateEnum.WORKING)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        await fail_task(await _terminal_ctx(db_session, seeded, seeded.task))
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.FAILED
        await db_session.commit()

        captured = capture_dispatch(
            monkeypatch,
            "beyo_manager.services.commands.task_steps.remove_task_step.event_bus.dispatch",
        )
        ctx = make_ctx(
            db_session, seeded, role_name="manager",
            incoming_data={"task_id": seeded.task.client_id, "step_id": step.client_id},
        )
        await remove_task_step(ctx)

        task_after = await _fresh_task(db_session, seeded.task.client_id)
        assert task_after.state == TaskStateEnum.PENDING
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.FAILED
        assert await _counters(db_session, row.client_id) == (0, 0, 0)
        assert [
            event for event in captured if event.event_name.startswith("stock_")
        ] == []

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C3(c)-(f) — §14F F3: a `resolved_early` assignment is never moved by the sync,
# whichever exit the task then takes. One row per task exit named by F3.
# ---------------------------------------------------------------------------


async def _resolved_early_via_scanner(db_session, seeded, monkeypatch, row):
    """A `in_progress` on a `working` T, then Scanner resolves it early: A
    `resolved_early`, `G == 4`, `mem == G` (§14F F4)."""
    from beyo_manager.domain.task_steps.enums import TaskStepStateEnum

    goal = await _make_goal(db_session, seeded, row)
    section = await _section(db_session, seeded, "C3cf section")
    step = await _add_step(
        db_session, seeded, seeded.task, section, state=TaskStepStateEnum.WORKING
    )
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id, actor_user_id=seeded.manager.client_id,
        now=NOW, trigger="test",
    )
    await _set_task_state(db_session, seeded.task, TaskStateEnum.WORKING)
    await db_session.commit()

    response = await _resolve_via_scanner(
        db_session, seeded, monkeypatch, [seeded.item.article_number]
    )
    assert response["results"][0] == {
        "article_number": seeded.item.article_number,
        "outcome": "resolved",
        "reason": "early",
    }
    await db_session.commit()
    assignment = await _fresh_assignment(db_session, assignment_id)
    assert assignment.state == S.RESOLVED_EARLY
    assert await _goal_awaiting(db_session, goal.client_id) == 4
    assert assignment.credited_history_record_id == goal.client_id
    return assignment_id, goal, step, section


@pytest.mark.parametrize(
    "exit_name,dispatch_site,expected_task_state",
    [
        pytest.param(
            "s1_complete_last_step",
            "beyo_manager.services.commands.task_steps.transition_step_state.event_bus.dispatch",
            TaskStateEnum.READY,
            id="c3c-s1-last-step-completed",
        ),
        pytest.param(
            "s5_fail_task",
            "beyo_manager.services.commands.tasks.fail_task.event_bus.dispatch",
            TaskStateEnum.FAILED,
            id="c3d-s5-fail-task",
        ),
        pytest.param(
            "s6_cancel_task",
            "beyo_manager.services.commands.tasks.cancel_task.event_bus.dispatch",
            TaskStateEnum.CANCELLED,
            id="c3e-s6-cancel-task",
        ),
        pytest.param(
            "s8_remove_the_only_step",
            "beyo_manager.services.commands.task_steps.remove_task_step.event_bus.dispatch",
            TaskStateEnum.PENDING,
            id="c3f-s8-remove-task-step",
        ),
    ],
)
async def test_c3cf_the_sync_never_moves_a_resolved_early_assignment(
    db_session, monkeypatch, exit_name, dispatch_site, expected_task_state
):
    from beyo_manager.services.commands.task_steps.transition_step_state import (
        transition_step_state,
    )

    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id, goal, step, _section_obj = await _resolved_early_via_scanner(
        db_session, seeded, monkeypatch, row
    )

    workspace_id = seeded.workspace.client_id
    try:
        captured = capture_dispatch(monkeypatch, dispatch_site)
        if exit_name == "s1_complete_last_step":
            await transition_step_state(
                make_ctx(
                    db_session, seeded, role_name="worker",
                    incoming_data={
                        "step_id": step.client_id,
                        "task_id": seeded.task.client_id,
                        "new_state": "completed",
                    },
                )
            )
        elif exit_name == "s5_fail_task":
            await fail_task(await _terminal_ctx(db_session, seeded, seeded.task))
        elif exit_name == "s6_cancel_task":
            await cancel_task(await _terminal_ctx(db_session, seeded, seeded.task))
        else:
            await remove_task_step(
                make_ctx(
                    db_session, seeded, role_name="manager",
                    incoming_data={
                        "task_id": seeded.task.client_id,
                        "step_id": step.client_id,
                    },
                )
            )

        task_after = await _fresh_task(db_session, seeded.task.client_id)
        assert task_after.state == expected_task_state
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.RESOLVED_EARLY
        assert await _counters(db_session, row.client_id) == (0, 0, 0)
        assert await _goal_awaiting(db_session, goal.client_id) == 4
        assert assignment.credited_history_record_id == goal.client_id
        assert [
            event for event in captured if event.event_name.startswith("stock_")
        ] == []

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C6(b) / C7 — the sync's clock, its event hand-up, and its repair trigger.
# ---------------------------------------------------------------------------


async def test_c6b_the_synced_move_stamps_the_commands_own_now(db_session, monkeypatch):
    """C6(b): `assignment.updated_at` is the **command's** `now`, never a clock read
    inside the sync.

    Proven at S8 `remove_task_step`, the one site whose `now` is `ctx.now` and so the
    only one a test can pin to an exact instant (the implementer's judgment call,
    plan 10 §8). The other eight sites pass their own locally computed `now`, which
    no fixture can name; relocating this row to S8 is a fixture choice, not a
    narrower surface — S8 is a full command boundary."""
    from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
    from beyo_manager.services.context import ServiceContext

    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    section = await _section(db_session, seeded, "C6b section")
    step = await _add_step(
        db_session, seeded, seeded.task, section, state=TaskStepStateEnum.WORKING
    )
    await _set_task_state(db_session, seeded.task, TaskStateEnum.WORKING)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id, actor_user_id=seeded.manager.client_id,
        now=NOW, trigger="test",
    )
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        ctx = ServiceContext(
            identity={
                "workspace_id": seeded.workspace.client_id,
                "user_id": seeded.manager.client_id,
                "role_name": "manager",
            },
            incoming_data={
                "task_id": seeded.task.client_id,
                "step_id": step.client_id,
            },
            session=db_session,
            now=NOW,
        )
        await remove_task_step(ctx)

        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.IN_QUEUE
        assert assignment.updated_at == NOW

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c7a_s4_hands_its_stock_events_up_to_the_commands_one_dispatch(
    db_session, monkeypatch
):
    """C7(a) (MC-19 hand-up): the sync returns its events to the command; the command
    dispatches **once**, after commit, with its own task events and the stock events
    in the same list."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id, actor_user_id=seeded.manager.client_id,
        now=NOW, trigger="test",
    )
    await _set_task_state(db_session, seeded.task, TaskStateEnum.WORKING)
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    calls: list[list] = []
    try:
        async def _capture_call(events):
            calls.append(list(events))

        monkeypatch.setattr(
            "beyo_manager.services.commands.tasks.resolve_task.event_bus.dispatch",
            _capture_call,
        )
        await resolve_task(await _terminal_ctx(db_session, seeded, seeded.task))

        assert len(calls) == 1, f"{len(calls)} dispatch calls, expected one"
        names = [event.event_name for event in calls[0]]
        assert "task:state-changed" in names
        assert "stock_task_assignment:state-changed" in names
        assert "stock_report_item:updated" in names

        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.AWAITING

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c7b_a_refused_resolve_task_dispatches_no_stock_event(
    db_session, monkeypatch
):
    """C7(b) — UNFAILABLE BY DESIGN (owner ruling, 2026-09-21, card 3). Kept as a
    cheap regression guard; the label is the point. No edit in this phase turns it
    red: `resolve_task` refuses on its first check, long before the sync would run.
    Reviewer's structural check: the sync call sits after the refusal."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await _set_task_state(db_session, seeded.task, TaskStateEnum.RESOLVED)
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    task_id = seeded.task.client_id
    user_ids = [seeded.manager.client_id, seeded.worker.client_id]
    try:
        captured = capture_dispatch(
            monkeypatch,
            "beyo_manager.services.commands.tasks.resolve_task.event_bus.dispatch",
        )
        ctx = make_ctx(
            db_session, seeded, role_name="manager",
            incoming_data={"client_id": task_id},
        )
        with pytest.raises(Exception):
            await resolve_task(ctx)
        # The refusal rolls its request back and the session expires every instance,
        # so from here the test uses ids captured before the call, never `seeded.*`.
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.IN_QUEUE
        assert [
            event for event in captured if event.event_name.startswith("stock_")
        ] == []
    finally:
        await _cleanup_task_side_effects_by_ids(db_session, workspace_id, user_ids)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c7c_the_syncs_inline_repair_carries_the_task_sync_trigger(
    db_session, monkeypatch
):
    """C7(c) (§12A): drift on R healed by a synced move is recorded with
    `trigger == "inline:task_sync"`."""
    from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
    from beyo_manager.models.tables.stock_report.stock_report_repair_record import (
        StockReportRepairRecord,
    )
    from beyo_manager.services.commands.task_steps.transition_step_state import (
        transition_step_state,
    )

    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    section = await _section(db_session, seeded, "C7c section")
    step = await _add_step(
        db_session, seeded, seeded.task, section, state=TaskStepStateEnum.PENDING
    )
    await _set_task_state(db_session, seeded.task, TaskStateEnum.ASSIGNED)
    await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await db_session.execute(
        StockReportItem.__table__.update()
        .where(StockReportItem.client_id == row.client_id)
        .values(quantity_in_queue=0)
    )
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        ctx = make_ctx(
            db_session, seeded, role_name="worker",
            incoming_data={
                "step_id": step.client_id,
                "task_id": seeded.task.client_id,
                "new_state": "working",
            },
        )
        await transition_step_state(ctx)

        repairs = (
            await db_session.execute(
                select(StockReportRepairRecord).where(
                    StockReportRepairRecord.workspace_id == workspace_id
                )
            )
        ).scalars().all()
        assert len(repairs) == 1
        assert repairs[0].field == "quantity_in_queue"
        assert repairs[0].trigger == "inline:task_sync"
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C8(a) — sync_task_stock_assignments's own contract (rule 18's third instance,
# the twin of plan 9 C8(c)). Owed: the two existing direct-call tests above
# (`test_sync_never_moves_a_resolved_early_assignment`,
# `test_sync_no_ops_when_the_assignment_is_already_at_target`) both assert
# `events == []`, so neither exercises a moved assignment nor pins the returned
# event-kind set (review, plan 10 §8). This row is the contract only — the
# argument shape and the returned event kinds — never a second copy of the nine
# call sites' own behaviour, which C1 and C4 already own.
# ---------------------------------------------------------------------------


async def test_c8a_sync_task_stock_assignments_contract(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    old_state = seeded.task.state  # pending, A in_queue
    await _set_task_state(db_session, seeded.task, TaskStateEnum.WORKING)
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        task = await _fresh_task(db_session, seeded.task.client_id)

        events = await sync_task_stock_assignments(
            db_session,
            [(task, old_state)],
            workspace_id=workspace_id,
            actor_user_id=seeded.manager.client_id,
            now=NOW,
        )

        event_names = [event.event_name for event in events]
        assert event_names.count("stock_task_assignment:state-changed") == 1
        assert event_names.count("stock_report_item:updated") == 1
        assert len(events) == 2

        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.IN_PROGRESS

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()
