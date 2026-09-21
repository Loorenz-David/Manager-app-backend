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
    make_ctx,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)


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
    history_record_ids = (
        await db_session.execute(
            select(HistoryRecord.client_id).where(
                HistoryRecord.created_by_id.in_(
                    [seeded.manager.client_id, seeded.worker.client_id]
                )
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
        .where(TaskStep.workspace_id == seeded.workspace.client_id)
        .values(latest_state_record_id=None)
    )
    await db_session.execute(
        delete(StepStateRecord).where(StepStateRecord.workspace_id == seeded.workspace.client_id)
    )
    await db_session.execute(
        delete(TaskStep).where(TaskStep.workspace_id == seeded.workspace.client_id)
    )
    await db_session.execute(
        delete(WorkingSection).where(WorkingSection.workspace_id == seeded.workspace.client_id)
    )


async def _terminal_ctx(db_session, seeded, task):
    return make_ctx(
        db_session,
        seeded,
        role_name="manager",
        incoming_data={"client_id": task.client_id},
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
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
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
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        ctx = await _terminal_ctx(db_session, seeded, seeded.task)
        await cancel_task(ctx)

        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.FAILED

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _cleanup_task_side_effects(db_session, seeded)
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c6a_credited_user_is_the_performer_not_a_third_party(db_session, monkeypatch):
    """C6(a): `updated_by_id` is the ctx performer, not any other identity."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        ctx = make_ctx(
            db_session, seeded, role_name="manager", user=seeded.manager,
            incoming_data={"client_id": seeded.task.client_id},
        )
        await fail_task(ctx)

        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.updated_by_id == seeded.manager.client_id

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
