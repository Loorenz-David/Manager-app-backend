from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select, text

from beyo_manager.domain.items.enums import ItemStateEnum
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.domain.stock_report.enums import StockReportPriorityEnum
from beyo_manager.domain.stock_report.enums import StockTaskAssignmentStateEnum as S
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_repair_record import (
    StockReportRepairRecord,
)
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.services.commands.stock_report._move_assignment import (
    ASSIGNMENT_DELETE,
    IllegalAssignmentMove,
    move_assignment,
)
from beyo_manager.services.commands.stock_report.repair_stock_report import (
    repair_stock_report,
)
from tests.helpers.statement_listener import count_writes, record_statements
from tests.helpers.stock_report import (
    assert_stock_report_clean,
    make_ctx,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
PROPERTIES = {"wood_type": "Teak", "upholstery": "Down"}


# ---------------------------------------------------------------------------
# fixture helpers
# ---------------------------------------------------------------------------


async def _make_row(db_session, seeded, *, counters=None, priority=None, priority_order=None):
    counters = counters or {}
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties=PROPERTIES,
        properties_signature=compute_stock_criteria_signature(PROPERTIES),
        quantity_requested=10,
        quantity_in_queue=counters.get("quantity_in_queue", 0),
        quantity_in_progress=counters.get("quantity_in_progress", 0),
        quantity_awaiting=counters.get("quantity_awaiting", 0),
        priority=priority,
        priority_order=priority_order,
    )
    db_session.add(row)
    await db_session.flush()
    return row


async def _make_assignment(
    db_session,
    seeded,
    row,
    *,
    task=None,
    item=None,
    quantity=4,
    state,
    is_deleted=False,
    updated_by_id=None,
    updated_at=None,
):
    assignment = StockTaskAssignment(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        task_id=(task or seeded.task).client_id,
        item_id=(item or seeded.item).client_id,
        quantity=quantity,
        state=state,
        is_deleted=is_deleted,
        updated_by_id=updated_by_id,
        updated_at=updated_at,
    )
    if is_deleted:
        assignment.deleted_at = NOW
    db_session.add(assignment)
    await db_session.flush()
    return assignment


async def _seed_flag(db_session, task, value):
    await db_session.execute(
        text("UPDATE tasks SET is_stock_assignment = :v WHERE client_id = :t"),
        {"v": value, "t": task.client_id},
    )


async def _hold_caller_locks(db_session, *, row, assignment=None, task=None):
    """S2 (batch B1 fix 1): models the locks the real caller already holds before
    invoking move_assignment/remove_assignment (MC-1's lock order, master plan §9
    rule 4) — task first (only relevant ahead of remove_assignment, whose tasks write
    happens *after* the row and assignment locks, inverting MC-1's order; that is safe
    only because the caller already holds the task lock), then the stock_report_items
    row, then the stock_task_assignment. Column-only SELECTs, never a full-entity
    select, so nothing here repopulates an identity-mapped instance a test deliberately
    keeps stale (C4(c), C7(d)). Locking a row this same transaction already holds is a
    no-op in Postgres. Asserts nothing about internals — fixture fidelity only."""
    if task is not None:
        await db_session.execute(
            select(Task.client_id).where(Task.client_id == task.client_id).with_for_update()
        )
    await db_session.execute(
        select(StockReportItem.client_id)
        .where(StockReportItem.client_id == row.client_id)
        .with_for_update()
    )
    if assignment is not None and assignment.client_id is not None:
        await db_session.execute(
            select(StockTaskAssignment.client_id)
            .where(StockTaskAssignment.client_id == assignment.client_id)
            .with_for_update()
        )


async def _second_pair(db_session, seeded, suffix):
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
        quantity=1,
        item_category_id=seeded.categories[0].client_id,
    )
    db_session.add_all([task, item])
    await db_session.flush()
    return task, item


async def _counters(db_session, row_id):
    row = (
        await db_session.execute(
            select(
                StockReportItem.quantity_in_queue,
                StockReportItem.quantity_in_progress,
                StockReportItem.quantity_awaiting,
            ).where(StockReportItem.client_id == row_id)
        )
    ).one()
    return tuple(row)


async def _fresh_assignment(db_session, client_id):
    return (
        await db_session.execute(
            select(StockTaskAssignment)
            .where(StockTaskAssignment.client_id == client_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


async def _repair_records(db_session, workspace_id):
    return (
        (
            await db_session.execute(
                select(StockReportRepairRecord).where(
                    StockReportRepairRecord.workspace_id == workspace_id
                )
            )
        )
        .scalars()
        .all()
    )


def _assert_assignment_event(event, kind, *, client_id, workspace_id, row_id, task_id, state):
    assert event.event_name == f"stock_task_assignment:{kind}"
    assert event.client_id == client_id
    assert event.workspace_id == workspace_id
    assert event.extra == {
        "stock_report_item_id": row_id,
        "task_id": task_id,
        "state": state,
    }


def _assert_row_event(
    event,
    *,
    client_id,
    workspace_id,
    quantity_requested=10,
    quantity_in_queue,
    quantity_in_progress,
    quantity_awaiting,
    priority=None,
    priority_order=None,
):
    assert event.event_name == "stock_report_item:updated"
    assert event.client_id == client_id
    assert event.workspace_id == workspace_id
    assert event.extra == {
        "quantity_requested": quantity_requested,
        "quantity_in_queue": quantity_in_queue,
        "quantity_in_progress": quantity_in_progress,
        "quantity_awaiting": quantity_awaiting,
        "priority": priority,
        "priority_order": priority_order,
    }


# ---------------------------------------------------------------------------
# C1 — the allowed-move table, positive rows
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("target", "expected_counters"),
    [
        pytest.param(S.IN_QUEUE, (4, 0, 0), id="c1a"),
        pytest.param(S.IN_PROGRESS, (0, 4, 0), id="c1b"),
        pytest.param(S.AWAITING, (0, 0, 4), id="c1c"),
    ],
)
async def test_c1_a_to_c_creation(db_session, target, expected_counters):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _seed_flag(db_session, seeded.task, True)
    assignment = StockTaskAssignment(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        task_id=seeded.task.client_id,
        item_id=seeded.item.client_id,
        quantity=4,
    )
    await _hold_caller_locks(db_session, row=row)
    events = await move_assignment(
        db_session,
        assignment,
        target,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="create_assignments",
        is_creation=True,
    )
    assert await _counters(db_session, row.client_id) == expected_counters
    assert len(events) == 2
    _assert_assignment_event(
        events[0],
        "created",
        client_id=assignment.client_id,
        workspace_id=seeded.workspace.client_id,
        row_id=row.client_id,
        task_id=seeded.task.client_id,
        state=target.value,
    )
    _assert_row_event(
        events[1],
        client_id=row.client_id,
        workspace_id=seeded.workspace.client_id,
        quantity_in_queue=expected_counters[0],
        quantity_in_progress=expected_counters[1],
        quantity_awaiting=expected_counters[2],
    )
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_d_in_queue_to_in_progress(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE)
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    events = await move_assignment(
        db_session,
        assignment,
        S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    assert await _counters(db_session, row.client_id) == (0, 4, 0)
    assert len(events) == 2
    _assert_assignment_event(
        events[0],
        "state-changed",
        client_id=assignment.client_id,
        workspace_id=seeded.workspace.client_id,
        row_id=row.client_id,
        task_id=seeded.task.client_id,
        state="in_progress",
    )
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_e_in_queue_to_awaiting(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE)
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    await move_assignment(
        db_session,
        assignment,
        S.AWAITING,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    assert await _counters(db_session, row.client_id) == (0, 0, 4)
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_f_in_queue_to_failed(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE)
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    events = await move_assignment(
        db_session,
        assignment,
        S.FAILED,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.state == S.FAILED
    assert len(events) == 2
    _assert_assignment_event(
        events[0],
        "state-changed",
        client_id=assignment.client_id,
        workspace_id=seeded.workspace.client_id,
        row_id=row.client_id,
        task_id=seeded.task.client_id,
        state="failed",
    )
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_g_in_queue_to_delete(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE)
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    events = await move_assignment(
        db_session,
        assignment,
        ASSIGNMENT_DELETE,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="delete_assignments",
    )
    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.is_deleted is True
    assert fresh.deleted_at == NOW
    assert fresh.deleted_by_id == seeded.manager.client_id
    assert len(events) == 2
    _assert_assignment_event(
        events[0],
        "deleted",
        client_id=assignment.client_id,
        workspace_id=seeded.workspace.client_id,
        row_id=row.client_id,
        task_id=seeded.task.client_id,
        state="in_queue",
    )
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


@pytest.mark.parametrize(
    ("target", "expected_counters"),
    [
        pytest.param(S.IN_QUEUE, (4, 0, 0), id="c1h"),
        pytest.param(S.AWAITING, (0, 0, 4), id="c1i"),
        pytest.param(S.FAILED, (0, 0, 0), id="c1j"),
    ],
)
async def test_c1_h_to_j_in_progress_moves(db_session, target, expected_counters):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_progress": 4})
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_PROGRESS)
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    await move_assignment(
        db_session,
        assignment,
        target,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    assert await _counters(db_session, row.client_id) == expected_counters
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_k_in_progress_to_delete(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_progress": 4})
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_PROGRESS)
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    await move_assignment(
        db_session,
        assignment,
        ASSIGNMENT_DELETE,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="delete_assignments",
    )
    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


@pytest.mark.parametrize(
    ("target", "expected_counters"),
    [
        pytest.param(S.IN_QUEUE, (4, 0, 0), id="c1l"),
        pytest.param(S.IN_PROGRESS, (0, 4, 0), id="c1m"),
        pytest.param(S.FAILED, (0, 0, 0), id="c1o"),
    ],
)
async def test_c1_l_m_o_awaiting_moves(db_session, target, expected_counters):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_awaiting": 4})
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.AWAITING)
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    await move_assignment(
        db_session,
        assignment,
        target,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    assert await _counters(db_session, row.client_id) == expected_counters
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_n_awaiting_to_resolved_scanner(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_awaiting": 4})
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.AWAITING)
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    events = await move_assignment(
        db_session,
        assignment,
        S.RESOLVED,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=None,
        now=NOW,
        trigger="items_processed",
    )
    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.state == S.RESOLVED
    assert fresh.updated_by_id is None
    assert fresh.updated_at == NOW
    assert len(events) == 2
    _assert_assignment_event(
        events[0],
        "state-changed",
        client_id=assignment.client_id,
        workspace_id=seeded.workspace.client_id,
        row_id=row.client_id,
        task_id=seeded.task.client_id,
        state="resolved",
    )
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_p_awaiting_to_delete(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_awaiting": 4})
    assignment = await _make_assignment(db_session, seeded, row, state=S.AWAITING)
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    await move_assignment(
        db_session,
        assignment,
        ASSIGNMENT_DELETE,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="delete_assignments",
    )
    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


@pytest.mark.parametrize(
    ("from_state", "row_id"),
    [pytest.param(S.RESOLVED, "c1q"), pytest.param(S.FAILED, "c1r")],
)
async def test_c1_q_r_terminal_delete_moves_no_counter(db_session, from_state, row_id):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment = await _make_assignment(db_session, seeded, row, state=from_state)
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    events = await move_assignment(
        db_session,
        assignment,
        ASSIGNMENT_DELETE,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="delete_assignments",
    )
    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    assert len(events) == 1
    _assert_assignment_event(
        events[0],
        "deleted",
        client_id=assignment.client_id,
        workspace_id=seeded.workspace.client_id,
        row_id=row.client_id,
        task_id=seeded.task.client_id,
        state=from_state.value,
    )
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_s_in_queue_to_resolved_early(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    # S3 (batch B1 fix 1, MC-19 payload, owner card 1): priority + priority_order set
    # on R so the `:updated` payload carries a non-null priority — both fields, or
    # consistency.py's priority_order_nullness check fails the clean assertion below
    # for an unrelated reason.
    row = await _make_row(
        db_session,
        seeded,
        counters={"quantity_in_queue": 4},
        priority=StockReportPriorityEnum.HIGH,
        priority_order=1,
    )
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE)
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    events = await move_assignment(
        db_session,
        assignment,
        S.RESOLVED_EARLY,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=None,
        now=NOW,
        trigger="items_processed",
    )
    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.state == S.RESOLVED_EARLY
    assert fresh.updated_by_id is None
    assert fresh.updated_at == NOW
    assert len(events) == 2
    _assert_assignment_event(
        events[0],
        "state-changed",
        client_id=assignment.client_id,
        workspace_id=seeded.workspace.client_id,
        row_id=row.client_id,
        task_id=seeded.task.client_id,
        state="resolved_early",
    )
    _assert_row_event(
        events[1],
        client_id=row.client_id,
        workspace_id=seeded.workspace.client_id,
        quantity_in_queue=0,
        quantity_in_progress=0,
        quantity_awaiting=0,
        priority="high",
        priority_order=1,
    )
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_t_in_progress_to_resolved_early(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_progress": 4})
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_PROGRESS)
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    events = await move_assignment(
        db_session,
        assignment,
        S.RESOLVED_EARLY,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=None,
        now=NOW,
        trigger="items_processed",
    )
    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.state == S.RESOLVED_EARLY
    assert fresh.updated_by_id is None
    assert len(events) == 2
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_u_resolved_early_to_delete(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment = await _make_assignment(db_session, seeded, row, state=S.RESOLVED_EARLY)
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    events = await move_assignment(
        db_session,
        assignment,
        ASSIGNMENT_DELETE,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="delete_assignments",
    )
    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.is_deleted is True
    assert fresh.deleted_by_id == seeded.manager.client_id
    assert len(events) == 1
    _assert_assignment_event(
        events[0],
        "deleted",
        client_id=assignment.client_id,
        workspace_id=seeded.workspace.client_id,
        row_id=row.client_id,
        task_id=seeded.task.client_id,
        state="resolved_early",
    )
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


# ---------------------------------------------------------------------------
# C2 — '=' cells: every state to itself is a no-op
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "state",
    [
        pytest.param(S.IN_QUEUE, id="c2a"),
        pytest.param(S.IN_PROGRESS, id="c2b"),
        pytest.param(S.AWAITING, id="c2c"),
        pytest.param(S.RESOLVED, id="c2d"),
        pytest.param(S.FAILED, id="c2e"),
        pytest.param(S.RESOLVED_EARLY, id="c2f"),
    ],
)
async def test_c2_same_state_is_noop(db_session, state):
    seeded = await seed_stock_report_workspace(db_session)
    counters = {"quantity_" + state.value: 4} if state.value in (
        "in_queue",
        "in_progress",
        "awaiting",
    ) else {}
    row = await _make_row(db_session, seeded, counters=counters)
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=state)
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    async with record_statements(db_session) as statements:
        events = await move_assignment(
            db_session,
            assignment,
            state,
            workspace_id=seeded.workspace.client_id,
            actor_user_id=seeded.manager.client_id,
            now=NOW,
            trigger="task_sync",
        )
    assert events == []
    assert (
        count_writes(
            statements,
            {
                "stock_report_items",
                "stock_task_assignments",
                "stock_report_history_records",
                "stock_report_repair_records",
            },
        )
        == 0
    )
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.updated_by_id is None
    assert fresh.updated_at is None


# ---------------------------------------------------------------------------
# C3 — the forbidden transitions (guard rows, total over the table)
# ---------------------------------------------------------------------------


_FORBIDDEN = [
    pytest.param(None, S.RESOLVED, id="c3a"),
    pytest.param(None, S.FAILED, id="c3b"),
    pytest.param(None, ASSIGNMENT_DELETE, id="c3c"),
    pytest.param(S.IN_QUEUE, S.RESOLVED, id="c3d"),
    pytest.param(S.IN_PROGRESS, S.RESOLVED, id="c3e"),
    pytest.param(S.RESOLVED, S.IN_QUEUE, id="c3f"),
    pytest.param(S.RESOLVED, S.IN_PROGRESS, id="c3g"),
    pytest.param(S.RESOLVED, S.AWAITING, id="c3h"),
    pytest.param(S.RESOLVED, S.FAILED, id="c3i"),
    pytest.param(S.FAILED, S.IN_QUEUE, id="c3j"),
    pytest.param(S.FAILED, S.IN_PROGRESS, id="c3k"),
    pytest.param(S.FAILED, S.AWAITING, id="c3l"),
    pytest.param(S.FAILED, S.RESOLVED, id="c3m"),
    pytest.param(None, S.RESOLVED_EARLY, id="c3n"),
    pytest.param(S.AWAITING, S.RESOLVED_EARLY, id="c3o"),
    pytest.param(S.RESOLVED_EARLY, S.IN_QUEUE, id="c3p"),
    pytest.param(S.RESOLVED_EARLY, S.IN_PROGRESS, id="c3q"),
    pytest.param(S.RESOLVED_EARLY, S.AWAITING, id="c3r"),
    pytest.param(S.RESOLVED_EARLY, S.RESOLVED, id="c3s"),
    pytest.param(S.RESOLVED_EARLY, S.FAILED, id="c3t"),
    pytest.param(S.RESOLVED, S.RESOLVED_EARLY, id="c3u"),
    pytest.param(S.FAILED, S.RESOLVED_EARLY, id="c3v"),
]


@pytest.mark.parametrize(("from_state", "target"), _FORBIDDEN)
async def test_c3_forbidden_moves_raise(db_session, from_state, target):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    is_creation = from_state is None
    if is_creation:
        assignment = StockTaskAssignment(
            workspace_id=seeded.workspace.client_id,
            stock_report_item_id=row.client_id,
            task_id=seeded.task.client_id,
            item_id=seeded.item.client_id,
            quantity=4,
        )
    else:
        assignment = await _make_assignment(db_session, seeded, row, state=from_state)
    await _hold_caller_locks(
        db_session, row=row, assignment=None if is_creation else assignment
    )
    with pytest.raises(IllegalAssignmentMove):
        await move_assignment(
            db_session,
            assignment,
            target,
            workspace_id=seeded.workspace.client_id,
            actor_user_id=seeded.manager.client_id,
            now=NOW,
            trigger="task_sync",
            is_creation=is_creation,
        )
    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    assert await _repair_records(db_session, seeded.workspace.client_id) == []
    if not is_creation:
        fresh = await _fresh_assignment(db_session, assignment.client_id)
        assert fresh.state == from_state
        assert fresh.is_deleted is False


# ---------------------------------------------------------------------------
# C4 — units, not counts of 1; multi-assignment; RETURNING vs stale ORM
# ---------------------------------------------------------------------------


async def test_c4_a_units_not_one(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 8})
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, quantity=8, state=S.IN_QUEUE)
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    await move_assignment(
        db_session,
        assignment,
        S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    assert await _counters(db_session, row.client_id) == (0, 8, 0)
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c4_b_two_assignments_second_item_and_task(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 8})
    task2, item2 = await _second_pair(db_session, seeded, "c4b")
    await _seed_flag(db_session, seeded.task, True)
    await _seed_flag(db_session, task2, True)
    assignment_a = await _make_assignment(db_session, seeded, row, quantity=3, state=S.IN_QUEUE)
    await _make_assignment(
        db_session, seeded, row, task=task2, item=item2, quantity=5, state=S.IN_QUEUE
    )
    await _hold_caller_locks(db_session, row=row, assignment=assignment_a)
    await move_assignment(
        db_session,
        assignment_a,
        S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    assert await _counters(db_session, row.client_id) == (5, 3, 0)
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c4_c_updated_event_uses_returning_not_stale_orm(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE)
    loaded_row = await db_session.get(StockReportItem, row.client_id)
    assert loaded_row is not None
    await db_session.execute(
        text("UPDATE stock_report_items SET quantity_requested = 99 WHERE client_id = :r"),
        {"r": row.client_id},
    )
    # Column-only lock (never a full-entity select), so it does not touch the
    # identity-mapped `loaded_row`/`assignment` this test deliberately keeps stale.
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    events = await move_assignment(
        db_session,
        assignment,
        S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    row_event = events[1]
    assert row_event.extra["quantity_requested"] == 99


# ---------------------------------------------------------------------------
# C5 — inline self-heal instruments
# ---------------------------------------------------------------------------


async def test_c5_a_downward_drift_self_heals_with_one_repair_record(db_session, caplog):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE)
    await db_session.execute(
        text("UPDATE stock_report_items SET quantity_in_queue = 0 WHERE client_id = :r"),
        {"r": row.client_id},
    )
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    with caplog.at_level("WARNING"):
        await move_assignment(
            db_session,
            assignment,
            S.IN_PROGRESS,
            workspace_id=seeded.workspace.client_id,
            actor_user_id=seeded.manager.client_id,
            now=NOW,
            trigger="task_sync",
        )
    assert await _counters(db_session, row.client_id) == (0, 4, 0)
    records = await _repair_records(db_session, seeded.workspace.client_id)
    assert len(records) == 1
    record = records[0]
    assert record.target_kind.value == "stock_report_item"
    assert record.target_client_id == row.client_id
    assert record.field == "quantity_in_queue"
    assert record.stored_value == "0"
    assert record.recomputed_value == "0"
    assert record.trigger == "inline:task_sync"
    assert record.created_by_id is None
    assert any("delta=-4" in message for message in caplog.messages)
    from beyo_manager.services.queries.stock_report.consistency import (
        compute_stock_report_divergences,
    )

    assert await compute_stock_report_divergences(db_session, seeded.workspace.client_id) == []


async def test_c5_b_upward_drift_is_not_self_healed(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE)
    await db_session.execute(
        text("UPDATE stock_report_items SET quantity_in_queue = 5 WHERE client_id = :r"),
        {"r": row.client_id},
    )
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    await move_assignment(
        db_session,
        assignment,
        S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    assert await _counters(db_session, row.client_id) == (1, 4, 0)
    assert await _repair_records(db_session, seeded.workspace.client_id) == []
    from beyo_manager.services.queries.stock_report.consistency import (
        compute_stock_report_divergences,
    )

    # S1 (batch B1 fix 1): the row says "check reports one" — assert the divergence
    # list whole, not filtered to one kind, so a second, unrelated divergence would
    # not pass unnoticed.
    divergences = await compute_stock_report_divergences(db_session, seeded.workspace.client_id)
    assert divergences == [
        {
            "kind": "counter_in_queue",
            "client_id": row.client_id,
            "field": "quantity_in_queue",
            "stored": 1,
            "expected": 0,
        }
    ]

    # S1: the row's fourth clause — repair_stock_report then clears it — mirroring
    # test_c2_c's closing block (plan 5's twin of this row).
    ctx = make_ctx(db_session, seeded, incoming_data={}, query_params={})
    ctx.now = NOW
    result = await repair_stock_report(ctx)
    assert [entry["kind"] for entry in result["repaired"]] == ["counter_in_queue"]
    assert await _counters(db_session, row.client_id) == (0, 4, 0)
    records = await _repair_records(db_session, seeded.workspace.client_id)
    assert len(records) == 1
    assert records[0].trigger == "manual"
    assert records[0].created_by_id == seeded.manager.client_id


# ---------------------------------------------------------------------------
# C6, C7 handled in test_remove_assignment.py (C6) and here (C7, stamps)
# ---------------------------------------------------------------------------


async def test_c7_a_stamps_actor_and_now(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE)
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    await move_assignment(
        db_session,
        assignment,
        S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.updated_by_id == seeded.manager.client_id
    assert fresh.updated_at == NOW


async def test_c7_b_null_actor_means_scanner(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_awaiting": 4})
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.AWAITING)
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    await move_assignment(
        db_session,
        assignment,
        S.RESOLVED,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=None,
        now=NOW,
        trigger="items_processed",
    )
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.updated_by_id is None
    assert fresh.updated_at == NOW


async def test_c7_c_delete_stamps_deleted_only(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    assignment = await _make_assignment(
        db_session, seeded, row, state=S.IN_QUEUE, updated_by_id=seeded.worker.client_id
    )
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    await move_assignment(
        db_session,
        assignment,
        ASSIGNMENT_DELETE,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="delete_assignments",
    )
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.deleted_by_id == seeded.manager.client_id
    assert fresh.deleted_at == NOW
    assert fresh.updated_by_id == seeded.worker.client_id


async def test_c7_d_counter_move_does_not_stamp_the_row(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    await _seed_flag(db_session, seeded.task, True)
    t_seed = datetime(2020, 1, 1, tzinfo=timezone.utc)
    await db_session.execute(
        text(
            "UPDATE stock_report_items SET updated_at = :t, updated_by_id = :u"
            " WHERE client_id = :r"
        ),
        {"t": t_seed, "u": seeded.worker.client_id, "r": row.client_id},
    )
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE)
    # Column-only lock (never a full-entity select): must not disturb the raw-SQL
    # stamps just seeded on R, which this row's assertion depends on staying put.
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    await move_assignment(
        db_session,
        assignment,
        S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    fresh_row = (
        await db_session.execute(
            select(StockReportItem.updated_at, StockReportItem.updated_by_id).where(
                StockReportItem.client_id == row.client_id
            )
        )
    ).one()
    assert fresh_row.updated_at == t_seed
    assert fresh_row.updated_by_id == seeded.worker.client_id


# ---------------------------------------------------------------------------
# Required ledger row (charter rule 15, §12A (e)): plant a double decrement
# ---------------------------------------------------------------------------


async def test_required_ledger_row_double_decrement_self_heals(db_session):
    """Not a mutation itself — this is the correctness case the plan's required
    ledger row is measured against; the -2q mutation is applied at
    `_delta_vector` (definition site) and recorded separately in the handoff."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE)
    await _hold_caller_locks(db_session, row=row, assignment=assignment)
    await move_assignment(
        db_session,
        assignment,
        S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    assert await _counters(db_session, row.client_id) == (0, 4, 0)
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)
