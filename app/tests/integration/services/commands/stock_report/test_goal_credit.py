from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.domain.stock_report.enums import (
    StockReportHistoryRecordTypeEnum,
    StockTaskAssignmentStateEnum as S,
)
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_repair_record import (
    StockReportRepairRecord,
)
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.stock_report._move_assignment import (
    ASSIGNMENT_DELETE,
    move_assignment,
)
from beyo_manager.services.commands.stock_report._remove_assignment import (
    remove_assignment,
)
from beyo_manager.services.commands.stock_report.repair_stock_report import (
    repair_stock_report,
)
from beyo_manager.services.queries.stock_report.consistency import (
    compute_stock_report_divergences,
    recompute_goal_total,
)
from tests.helpers.statement_listener import count_writes, record_statements
from tests.helpers.stock_report import assert_stock_report_clean, make_ctx, seed_stock_report_workspace

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
T1 = datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc)
PROPERTIES = {"wood_type": "Teak", "upholstery": "Down"}


async def _make_row(db_session, seeded, *, counters=None, quantity_requested=10):
    counters = counters or {}
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties=PROPERTIES,
        properties_signature=compute_stock_criteria_signature(PROPERTIES),
        quantity_requested=quantity_requested,
        quantity_in_queue=counters.get("quantity_in_queue", 0),
        quantity_in_progress=counters.get("quantity_in_progress", 0),
        quantity_awaiting=counters.get("quantity_awaiting", 0),
    )
    db_session.add(row)
    await db_session.flush()
    return row


async def _make_goal(db_session, seeded, row, *, quantity_awaiting=0, created_at):
    record = StockReportHistoryRecord(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        type=StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
        quantity_requested=row.quantity_requested,
        quantity_awaiting=quantity_awaiting,
        created_at=created_at,
    )
    db_session.add(record)
    await db_session.flush()
    return record


async def _make_assignment(
    db_session,
    seeded,
    row,
    *,
    item=None,
    quantity=4,
    state,
    credited=None,
    is_deleted=False,
):
    assignment = StockTaskAssignment(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        task_id=seeded.task.client_id,
        item_id=(item or seeded.item).client_id,
        quantity=quantity,
        state=state,
        credited_history_record_id=credited,
        is_deleted=is_deleted,
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


async def _fresh_goal(db_session, record_id):
    return await db_session.scalar(
        select(StockReportHistoryRecord.quantity_awaiting).where(
            StockReportHistoryRecord.client_id == record_id
        )
    )


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


# ---------------------------------------------------------------------------
# C1 — the MC-5 table
# ---------------------------------------------------------------------------


async def test_c1_a_creation_into_awaiting_credits_the_goal(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row, created_at=T0)
    await _seed_flag(db_session, seeded.task, True)
    assignment = StockTaskAssignment(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        task_id=seeded.task.client_id,
        item_id=seeded.item.client_id,
        quantity=4,
    )
    await move_assignment(
        db_session,
        assignment,
        S.AWAITING,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="create_assignments",
        is_creation=True,
    )
    assert await _fresh_goal(db_session, goal.client_id) == 4
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.credited_history_record_id == goal.client_id
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


@pytest.mark.parametrize("from_state", [S.IN_QUEUE, S.IN_PROGRESS], ids=["c1b", "c1c"])
async def test_c1_b_c_active_to_awaiting_credits_the_goal(db_session, from_state):
    seeded = await seed_stock_report_workspace(db_session)
    counters = {"quantity_in_queue": 4} if from_state == S.IN_QUEUE else {"quantity_in_progress": 4}
    row = await _make_row(db_session, seeded, counters=counters)
    goal = await _make_goal(db_session, seeded, row, created_at=T0)
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=from_state)
    await move_assignment(
        db_session,
        assignment,
        S.AWAITING,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    assert await _fresh_goal(db_session, goal.client_id) == 4
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.credited_history_record_id == goal.client_id
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_d_no_goal_record_credits_nothing(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE)
    async with record_statements(db_session) as statements:
        await move_assignment(
            db_session,
            assignment,
            S.AWAITING,
            workspace_id=seeded.workspace.client_id,
            actor_user_id=seeded.manager.client_id,
            now=NOW,
            trigger="task_sync",
        )
    assert count_writes(statements, {"stock_report_history_records"}) == 0
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.credited_history_record_id is None
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_e_scanner_resolve_keeps_the_credit(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_awaiting": 4})
    goal = await _make_goal(db_session, seeded, row, quantity_awaiting=4, created_at=T0)
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(
        db_session, seeded, row, state=S.AWAITING, credited=goal.client_id
    )
    await move_assignment(
        db_session,
        assignment,
        S.RESOLVED,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=None,
        now=NOW,
        trigger="items_processed",
    )
    assert await _fresh_goal(db_session, goal.client_id) == 4
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.credited_history_record_id == goal.client_id
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


@pytest.mark.parametrize(
    ("target", "row_id"),
    [
        pytest.param(S.IN_QUEUE, "c1f", id="c1f"),
        pytest.param(S.IN_PROGRESS, "c1g", id="c1g"),
        pytest.param(S.FAILED, "c1h", id="c1h"),
        pytest.param(ASSIGNMENT_DELETE, "c1i", id="c1i"),
    ],
)
async def test_c1_f_to_i_leaving_awaiting_uncredits(db_session, target, row_id):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_awaiting": 4})
    goal = await _make_goal(db_session, seeded, row, quantity_awaiting=4, created_at=T0)
    ends_deleted = target is ASSIGNMENT_DELETE
    await _seed_flag(db_session, seeded.task, not ends_deleted)
    assignment = await _make_assignment(
        db_session, seeded, row, state=S.AWAITING, credited=goal.client_id
    )
    await move_assignment(
        db_session,
        assignment,
        target,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    assert await _fresh_goal(db_session, goal.client_id) == 0
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.credited_history_record_id is None
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_j_subtraction_lands_on_the_credited_record_not_the_current_one(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_awaiting": 4})
    goal = await _make_goal(db_session, seeded, row, quantity_awaiting=4, created_at=T0)
    goal2 = await _make_goal(db_session, seeded, row, quantity_awaiting=0, created_at=T1)
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(
        db_session, seeded, row, state=S.AWAITING, credited=goal.client_id
    )
    await move_assignment(
        db_session,
        assignment,
        S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    assert await _fresh_goal(db_session, goal.client_id) == 0
    assert await _fresh_goal(db_session, goal2.client_id) == 0
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_k_no_memory_before_any_goal_leaves_it_untouched(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_awaiting": 4})
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.AWAITING, credited=None)
    goal = await _make_goal(db_session, seeded, row, quantity_awaiting=0, created_at=T0)
    async with record_statements(db_session) as statements:
        await move_assignment(
            db_session,
            assignment,
            S.IN_QUEUE,
            workspace_id=seeded.workspace.client_id,
            actor_user_id=seeded.manager.client_id,
            now=NOW,
            trigger="task_sync",
        )
    assert await _fresh_goal(db_session, goal.client_id) == 0
    assert count_writes(statements, {"stock_report_history_records"}) == 0
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_l_resolved_to_delete_keeps_the_credit(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row, quantity_awaiting=4, created_at=T0)
    await _seed_flag(db_session, seeded.task, False)
    assignment = await _make_assignment(
        db_session, seeded, row, state=S.RESOLVED, credited=goal.client_id
    )
    await move_assignment(
        db_session,
        assignment,
        ASSIGNMENT_DELETE,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="delete_assignments",
    )
    assert await _fresh_goal(db_session, goal.client_id) == 4
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.credited_history_record_id == goal.client_id
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_m_active_to_terminal_credits_nothing(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    goal = await _make_goal(db_session, seeded, row, quantity_awaiting=0, created_at=T0)
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE, credited=None)
    async with record_statements(db_session) as statements:
        await move_assignment(
            db_session,
            assignment,
            S.FAILED,
            workspace_id=seeded.workspace.client_id,
            actor_user_id=seeded.manager.client_id,
            now=NOW,
            trigger="task_sync",
        )
    assert count_writes(statements, {"stock_report_history_records"}) == 0
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.credited_history_record_id is None
    assert await _fresh_goal(db_session, goal.client_id) == 0
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_n_entering_resolved_early_from_in_queue_credits_the_goal(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    goal = await _make_goal(db_session, seeded, row, created_at=T0)
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE, credited=None)
    await move_assignment(
        db_session,
        assignment,
        S.RESOLVED_EARLY,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=None,
        now=NOW,
        trigger="items_processed",
    )
    assert await _fresh_goal(db_session, goal.client_id) == 4
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.credited_history_record_id == goal.client_id
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_o_entering_resolved_early_from_in_progress_credits_the_goal(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_progress": 4})
    goal = await _make_goal(db_session, seeded, row, created_at=T0)
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_PROGRESS, credited=None)
    await move_assignment(
        db_session,
        assignment,
        S.RESOLVED_EARLY,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=None,
        now=NOW,
        trigger="items_processed",
    )
    assert await _fresh_goal(db_session, goal.client_id) == 4
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.credited_history_record_id == goal.client_id
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_p_resolved_early_no_goal_record_credits_nothing(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 4})
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE, credited=None)
    async with record_statements(db_session) as statements:
        await move_assignment(
            db_session,
            assignment,
            S.RESOLVED_EARLY,
            workspace_id=seeded.workspace.client_id,
            actor_user_id=None,
            now=NOW,
            trigger="items_processed",
        )
    assert count_writes(statements, {"stock_report_history_records"}) == 0
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.credited_history_record_id is None
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1_q_resolved_early_to_delete_keeps_the_credit(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row, quantity_awaiting=4, created_at=T0)
    await _seed_flag(db_session, seeded.task, False)
    assignment = await _make_assignment(
        db_session, seeded, row, state=S.RESOLVED_EARLY, credited=goal.client_id
    )
    await move_assignment(
        db_session,
        assignment,
        ASSIGNMENT_DELETE,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="delete_assignments",
    )
    assert await _fresh_goal(db_session, goal.client_id) == 4
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.credited_history_record_id == goal.client_id
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


# ---------------------------------------------------------------------------
# C2 — self-heal and recomputation
# ---------------------------------------------------------------------------


async def test_c2_a_downward_drift_self_heals_with_one_repair_record(db_session, caplog):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_awaiting": 4})
    goal = await _make_goal(db_session, seeded, row, quantity_awaiting=4, created_at=T0)
    await _seed_flag(db_session, seeded.task, True)
    assignment = await _make_assignment(
        db_session, seeded, row, state=S.AWAITING, credited=goal.client_id
    )
    await db_session.execute(
        text("UPDATE stock_report_history_records SET quantity_awaiting = 1 WHERE client_id = :g"),
        {"g": goal.client_id},
    )
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
    assert await _fresh_goal(db_session, goal.client_id) == 0
    records = await _repair_records(db_session, seeded.workspace.client_id)
    assert len(records) == 1
    record = records[0]
    assert record.target_kind.value == "history_record"
    assert record.target_client_id == goal.client_id
    assert record.field == "quantity_awaiting"
    assert record.stored_value == "1"
    assert record.recomputed_value == "0"
    assert record.trigger == "inline:task_sync"
    assert any("delta=-4" in message for message in caplog.messages)
    assert await compute_stock_report_divergences(db_session, seeded.workspace.client_id) == []


async def test_c2_b_recomputation_includes_deleted_resolved_credit(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_awaiting": 3})
    goal = await _make_goal(db_session, seeded, row, quantity_awaiting=0, created_at=T0)
    await _seed_flag(db_session, seeded.task, True)
    a1 = await _make_assignment(
        db_session,
        seeded,
        row,
        state=S.RESOLVED,
        quantity=2,
        credited=goal.client_id,
        is_deleted=True,
    )
    a2 = await _make_assignment(
        db_session, seeded, row, state=S.AWAITING, quantity=3, credited=goal.client_id
    )
    await db_session.execute(
        text("UPDATE stock_report_history_records SET quantity_awaiting = 0 WHERE client_id = :g"),
        {"g": goal.client_id},
    )
    await move_assignment(
        db_session,
        a2,
        S.IN_QUEUE,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    assert await _fresh_goal(db_session, goal.client_id) == 2
    records = await _repair_records(db_session, seeded.workspace.client_id)
    assert len(records) == 1
    assert records[0].stored_value == "0"
    assert records[0].recomputed_value == "2"
    assert await recompute_goal_total(db_session, goal.client_id) == 2
    _ = a1  # kept for readability; a1 stays soft-deleted throughout


async def test_c2_c_upward_drift_is_not_self_healed_by_a_move(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_awaiting": 4})
    goal = await _make_goal(db_session, seeded, row, quantity_awaiting=4, created_at=T0)
    await _seed_flag(db_session, seeded.task, False)
    assignment = await _make_assignment(
        db_session, seeded, row, state=S.AWAITING, credited=goal.client_id
    )
    await db_session.execute(
        text("UPDATE stock_report_history_records SET quantity_awaiting = 5 WHERE client_id = :g"),
        {"g": goal.client_id},
    )
    await move_assignment(
        db_session,
        assignment,
        S.RESOLVED,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=None,
        now=NOW,
        trigger="items_processed",
    )
    await move_assignment(
        db_session,
        assignment,
        ASSIGNMENT_DELETE,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="delete_assignments",
    )
    assert await _repair_records(db_session, seeded.workspace.client_id) == []
    divergences = await compute_stock_report_divergences(db_session, seeded.workspace.client_id)
    goal_divergences = [d for d in divergences if d["kind"] == "goal_total"]
    assert goal_divergences == [
        {
            "kind": "goal_total",
            "client_id": goal.client_id,
            "field": "quantity_awaiting",
            "stored": 5,
            "expected": 4,
        }
    ]
    ctx = make_ctx(db_session, seeded, incoming_data={}, query_params={})
    ctx.now = NOW
    result = await repair_stock_report(ctx)
    assert [entry["kind"] for entry in result["repaired"]] == ["goal_total"]
    records = await _repair_records(db_session, seeded.workspace.client_id)
    assert len(records) == 1
    assert records[0].trigger == "manual"
    assert records[0].created_by_id == seeded.manager.client_id


async def test_c2_d_recomputation_includes_resolved_early_credit(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, counters={"quantity_in_queue": 2})
    goal = await _make_goal(db_session, seeded, row, quantity_awaiting=0, created_at=T0)
    await _seed_flag(db_session, seeded.task, True)
    a1 = await _make_assignment(db_session, seeded, row, state=S.IN_QUEUE, quantity=2, credited=None)
    await move_assignment(
        db_session,
        a1,
        S.RESOLVED_EARLY,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=None,
        now=NOW,
        trigger="items_processed",
    )
    assert await _fresh_goal(db_session, goal.client_id) == 2
    a2 = StockTaskAssignment(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        task_id=seeded.task.client_id,
        item_id=seeded.item.client_id,
        quantity=3,
    )
    await move_assignment(
        db_session,
        a2,
        S.AWAITING,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="create_assignments",
        is_creation=True,
    )
    assert await _fresh_goal(db_session, goal.client_id) == 5
    await db_session.execute(
        text("UPDATE stock_report_history_records SET quantity_awaiting = 0 WHERE client_id = :g"),
        {"g": goal.client_id},
    )
    await move_assignment(
        db_session,
        a2,
        S.IN_QUEUE,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    assert await _fresh_goal(db_session, goal.client_id) == 2
    records = await _repair_records(db_session, seeded.workspace.client_id)
    assert len(records) == 1
    assert records[0].stored_value == "0"
    assert records[0].recomputed_value == "2"


# ---------------------------------------------------------------------------
# C3 — the worked sequence
# ---------------------------------------------------------------------------


async def test_c3_a_worked_sequence(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal1 = await _make_goal(db_session, seeded, row, quantity_awaiting=0, created_at=T0)
    await _seed_flag(db_session, seeded.task, True)

    assignment = StockTaskAssignment(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        task_id=seeded.task.client_id,
        item_id=seeded.item.client_id,
        quantity=4,
    )
    # (1) ∅ -> awaiting
    await move_assignment(
        db_session,
        assignment,
        S.AWAITING,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="create_assignments",
        is_creation=True,
    )
    assert await _fresh_goal(db_session, goal1.client_id) == 4
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.credited_history_record_id == goal1.client_id

    # (2) a second, later goal record becomes current
    goal2 = await _make_goal(db_session, seeded, row, quantity_awaiting=0, created_at=T1)

    # (3) awaiting -> in_progress
    await move_assignment(
        db_session,
        assignment,
        S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    assert await _fresh_goal(db_session, goal1.client_id) == 0
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.credited_history_record_id is None

    # (4) in_progress -> awaiting (reopen): credits the now-current goal2
    await move_assignment(
        db_session,
        assignment,
        S.AWAITING,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="task_sync",
    )
    assert await _fresh_goal(db_session, goal2.client_id) == 4
    assert await _fresh_goal(db_session, goal1.client_id) == 0
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.credited_history_record_id == goal2.client_id

    # (5) awaiting -> resolved (Scanner): credit kept
    await move_assignment(
        db_session,
        assignment,
        S.RESOLVED,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=None,
        now=NOW,
        trigger="items_processed",
    )
    assert await _fresh_goal(db_session, goal2.client_id) == 4
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.credited_history_record_id == goal2.client_id

    # (6) remove the (now resolved) assignment: credit still kept
    await remove_assignment(
        db_session,
        assignment,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="delete_assignments",
    )
    row_counters = (
        await db_session.execute(
            select(
                StockReportItem.quantity_in_queue,
                StockReportItem.quantity_in_progress,
                StockReportItem.quantity_awaiting,
            ).where(StockReportItem.client_id == row.client_id)
        )
    ).one()
    assert tuple(row_counters) == (0, 0, 0)
    assert await _fresh_goal(db_session, goal2.client_id) == 4
    fresh = await _fresh_assignment(db_session, assignment.client_id)
    assert fresh.is_deleted is True
    assert await recompute_goal_total(db_session, goal1.client_id) == 0
    assert await recompute_goal_total(db_session, goal2.client_id) == 4
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)
