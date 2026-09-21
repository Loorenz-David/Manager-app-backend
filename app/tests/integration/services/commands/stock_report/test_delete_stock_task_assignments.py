"""Plan 8 — `delete_stock_task_assignments` (master plan §6.5; intention §9 "assignment
deletion"). Builds on `create_stock_task_assignments` (`CR`) for fixtures, per plan 8
§6's "from this phase on, every fixture's assignments come from CR."

This file exercises one representative row per distinct code path; row-by-row
transcription and mutation arming belong to the tester (see the implementer handoff).
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from beyo_manager.domain.stock_report.enums import (
    StockReportHistoryRecordTypeEnum,
    StockTaskAssignmentStateEnum as S,
)
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.errors.not_found import NotFound
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
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.services.commands.stock_report._move_assignment import move_assignment
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from beyo_manager.services.commands.stock_report.delete_stock_task_assignments import (
    delete_stock_task_assignments,
)
from tests.helpers.stock_report import (
    assert_stock_report_clean,
    capture_dispatch,
    make_ctx,
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


async def _CR(db_session, seeded, entries):
    ctx = make_ctx(
        db_session, seeded, role_name="worker", incoming_data={"entries": entries}
    )
    return await create_stock_task_assignments(ctx)


async def _DL(db_session, seeded, client_ids):
    ctx = make_ctx(
        db_session,
        seeded,
        role_name="worker",
        incoming_data={"client_ids": client_ids},
    )
    return await delete_stock_task_assignments(ctx)


async def _create_one(db_session, seeded, row):
    result = await _CR(
        db_session,
        seeded,
        [
            {
                "stock_report_item_id": row.client_id,
                "task_id": seeded.task.client_id,
                "item_id": seeded.item.client_id,
                "override_property_mismatch": False,
            }
        ],
    )
    return result["stock_task_assignments"][0]["client_id"]


async def _fresh_assignment(db_session, client_id):
    return (
        await db_session.execute(
            select(StockTaskAssignment)
            .where(StockTaskAssignment.client_id == client_id)
            .execution_options(populate_existing=True)
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


async def _make_goal(db_session, seeded, row):
    """The row's current goal record G (MC-5) — rows C6(b) and C6(i) name `G`."""
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
    return await db_session.scalar(
        select(StockReportHistoryRecord.quantity_awaiting).where(
            StockReportHistoryRecord.client_id == goal_id
        )
    )


async def test_deletes_in_queue_assignment_zeroes_counters_and_clears_flag(
    db_session, monkeypatch
):
    """C6(a): every clause of the row — counters, the three deletion stamps, the
    task flag, and the exact dispatched event list."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _create_one(db_session, seeded, row)
    captured = capture_dispatch(
        monkeypatch,
        "beyo_manager.services.commands.stock_report.delete_stock_task_assignments.dispatch",
    )

    ctx = make_ctx(
        db_session,
        seeded,
        role_name="worker",
        incoming_data={"client_ids": [assignment_id]},
    )
    result = await delete_stock_task_assignments(ctx)

    assert result["deleted_client_ids"] == [assignment_id]
    assignment = await _fresh_assignment(db_session, assignment_id)
    assert assignment.is_deleted is True
    assert assignment.deleted_by_id == seeded.manager.client_id
    assert assignment.deleted_at == ctx.now
    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    refreshed_task = await db_session.get(Task, seeded.task.client_id)
    assert refreshed_task.is_stock_assignment is False
    assert [event.event_name for event in captured] == [
        "stock_task_assignment:deleted",
        "stock_report_item:updated",
    ]
    assert captured[0].extra["state"] == "in_queue"
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_deleting_resolved_assignment_leaves_counters_untouched(
    db_session, monkeypatch
):
    """C6(c): deleting a terminal assignment moves no counter, so MC-19's
    net-change rule emits **no** `stock_report_item:updated` at all."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _create_one(db_session, seeded, row)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.AWAITING, workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id, now=NOW, trigger="test",
    )
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.RESOLVED, workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id, now=NOW, trigger="test",
    )
    captured = capture_dispatch(
        monkeypatch,
        "beyo_manager.services.commands.stock_report.delete_stock_task_assignments.dispatch",
    )

    await _DL(db_session, seeded, [assignment_id])

    assignment = await _fresh_assignment(db_session, assignment_id)
    assert assignment.is_deleted is True
    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    assert [event.event_name for event in captured] == ["stock_task_assignment:deleted"]
    refreshed_task = await db_session.get(Task, seeded.task.client_id)
    assert refreshed_task.is_stock_assignment is False
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c6b_deleting_an_awaiting_assignment_uncredits_the_goal(db_session):
    """C6(b) (MC-5 row 5): deleting an `awaiting` assignment gives the credited
    quantity back to the goal record and clears the assignment's credit memory."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row)
    assignment_id = await _create_one(db_session, seeded, row)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.AWAITING, workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id, now=NOW, trigger="test",
    )
    assert await _goal_awaiting(db_session, goal.client_id) == 4

    await _DL(db_session, seeded, [assignment_id])

    assert await _goal_awaiting(db_session, goal.client_id) == 0
    assignment = await _fresh_assignment(db_session, assignment_id)
    assert assignment.credited_history_record_id is None
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c6i_deleting_a_resolved_early_assignment_keeps_its_goal_credit(
    db_session, monkeypatch
):
    """C6(i) (§14F F1-F2/F4, MC-19): `resolved_early` is terminal *and* credited.
    Deleting it moves no counter, emits no `:updated`, and the goal credit and the
    credit memory are both kept."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row)
    assignment_id = await _create_one(db_session, seeded, row)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.RESOLVED_EARLY, workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id, now=NOW, trigger="test",
    )
    assert await _goal_awaiting(db_session, goal.client_id) == 4
    counters_before = await _counters(db_session, row.client_id)
    captured = capture_dispatch(
        monkeypatch,
        "beyo_manager.services.commands.stock_report.delete_stock_task_assignments.dispatch",
    )

    await _DL(db_session, seeded, [assignment_id])

    assert await _counters(db_session, row.client_id) == counters_before
    assert [event.event_name for event in captured] == ["stock_task_assignment:deleted"]
    assert captured[0].extra["state"] == "resolved_early"
    refreshed_task = await db_session.get(Task, seeded.task.client_id)
    assert refreshed_task.is_stock_assignment is False
    assert await _goal_awaiting(db_session, goal.client_id) == 4
    assignment = await _fresh_assignment(db_session, assignment_id)
    assert assignment.credited_history_record_id == goal.client_id
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c6g_flag_stays_true_while_another_assignment_of_the_task_survives(
    db_session,
):
    """C6(g) (MC-15/P21, owner card B): the task flag asks "does this task hold any
    non-deleted assignment", not "any *active* one" — a `failed` sibling keeps it
    true. B is built before A so neither the active index nor §14F F9 applies."""
    seeded = await seed_stock_report_workspace(db_session)
    row2 = await _make_row(db_session, seeded, criteria={"upholstery": ["down"]})
    b_id = await _create_one(db_session, seeded, row2)
    b = await _fresh_assignment(db_session, b_id)
    await move_assignment(
        db_session, b, S.FAILED, workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id, now=NOW, trigger="test",
    )
    row = await _make_row(db_session, seeded)
    a_id = await _create_one(db_session, seeded, row)

    await _DL(db_session, seeded, [a_id])

    refreshed_task = await db_session.get(Task, seeded.task.client_id)
    assert refreshed_task.is_stock_assignment is True
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_absent_id_refuses_the_whole_batch(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _create_one(db_session, seeded, row)

    with pytest.raises(NotFound):
        await _DL(db_session, seeded, [assignment_id, "sta_absent"])

    assignment = await _fresh_assignment(db_session, assignment_id)
    assert assignment.is_deleted is False


async def test_already_deleted_id_is_not_found(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _create_one(db_session, seeded, row)
    await _DL(db_session, seeded, [assignment_id])

    with pytest.raises(NotFound):
        await _DL(db_session, seeded, [assignment_id])


async def test_foreign_workspace_id_is_not_found(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    other = await seed_stock_report_workspace(db_session, suffix="foreign")
    other_row = await _make_row(db_session, other)
    foreign_assignment_id = await _create_one(db_session, other, other_row)

    with pytest.raises(NotFound):
        await _DL(db_session, seeded, [foreign_assignment_id])

    assignment = await _fresh_assignment(db_session, foreign_assignment_id)
    assert assignment.is_deleted is False

    from tests.helpers.stock_report import purge_stock_report_workspace

    await purge_stock_report_workspace(db_session, other.workspace.client_id)


async def test_two_assignments_on_one_row_coalesce_to_one_updated_event(
    db_session, monkeypatch
):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    first_id = await _create_one(db_session, seeded, row)

    from sqlalchemy import func

    from beyo_manager.domain.items.enums import ItemStateEnum
    from beyo_manager.domain.tasks.enums import TaskTypeEnum, TaskStateEnum as TState
    from beyo_manager.models.tables.items.item import Item

    next_scalar_id = (
        await db_session.scalar(
            select(func.max(Task.task_scalar_id)).where(
                Task.workspace_id == seeded.workspace.client_id
            )
        )
        or 0
    ) + 1
    from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
    from beyo_manager.models.tables.tasks.task_item import TaskItem

    task2 = Task(
        client_id=f"tsk_c6h_{seeded.workspace.client_id}",
        workspace_id=seeded.workspace.client_id,
        task_scalar_id=next_scalar_id,
        task_type=TaskTypeEnum.INTERNAL,
        state=TState.PENDING,
        created_by_id=seeded.manager.client_id,
    )
    item2 = Item(
        client_id=f"itm_c6h_{seeded.workspace.client_id}",
        workspace_id=seeded.workspace.client_id,
        article_number=f"c6h-{seeded.workspace.client_id}",
        state=ItemStateEnum.PENDING,
        quantity=4,
        item_category_id=seeded.categories[0].client_id,
        properties={"wood_type": "Teak", "upholstery": "Down"},
    )
    db_session.add_all([task2, item2])
    await db_session.flush()
    db_session.add(
        TaskItem(
            client_id=f"tim_c6h_{seeded.workspace.client_id}",
            workspace_id=seeded.workspace.client_id,
            task_id=task2.client_id,
            item_id=item2.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=seeded.manager.client_id,
        )
    )
    await db_session.flush()
    second_result = await _CR(
        db_session,
        seeded,
        [
            {
                "stock_report_item_id": row.client_id,
                "task_id": task2.client_id,
                "item_id": item2.client_id,
                "override_property_mismatch": False,
            }
        ],
    )
    second_id = second_result["stock_task_assignments"][0]["client_id"]

    captured = capture_dispatch(
        monkeypatch,
        "beyo_manager.services.commands.stock_report.delete_stock_task_assignments.dispatch",
    )

    result = await _DL(db_session, seeded, [first_id, second_id])

    assert set(result["deleted_client_ids"]) == {first_id, second_id}
    updated = [e for e in captured if e.event_name == "stock_report_item:updated"]
    deleted = [e for e in captured if e.event_name == "stock_task_assignment:deleted"]
    assert len(updated) == 1
    assert len(deleted) == 2
    assert updated[0].extra["quantity_in_queue"] == 0
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c6j_the_same_assignment_named_twice_in_one_delete_is_removed_once(
    db_session, monkeypatch
):
    """C6(j) (owner card 2, batch C1 review finding B2). Row header says
    `DL([A, A, B])`; built as `DL([A, A])` on a row that also holds an active,
    untouched B(4) — the row's own outcome cell ("ends at B's remaining 4") is
    only true if B is never named in the delete call, and master plan §9 rule 7's
    citation of the measured defect (line ~322: "`DL([A, A])` on a row also
    holding an active B(4)") confirms this reading; a literal `[A, A, B]` request
    would delete B too and leave the row at 0, contradicting its own outcome cell.
    Flagged as a fixture-header transcription defect in the Review log (§6
    preamble: "an outcome that disagrees with its own fixture is a plan defect:
    report it, never reconcile it in the test") — built on the outcome cell and
    the master plan's independent citation, not reconciled silently.

    The batch succeeds; A is removed **once**, so R's `quantity_in_queue` falls by
    4, not 8, and ends at B's remaining 4; exactly one
    `stock_task_assignment:deleted` for A; the response lists each id once,
    sorted."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    a_id = await _create_one(db_session, seeded, row)

    from sqlalchemy import func

    from beyo_manager.domain.items.enums import ItemStateEnum
    from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum as TState, TaskTypeEnum
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
    task_b = Task(
        client_id=f"tsk_c6j_{seeded.workspace.client_id}",
        workspace_id=seeded.workspace.client_id,
        task_scalar_id=next_scalar_id,
        task_type=TaskTypeEnum.INTERNAL,
        state=TState.PENDING,
        created_by_id=seeded.manager.client_id,
    )
    item_b = Item(
        client_id=f"itm_c6j_{seeded.workspace.client_id}",
        workspace_id=seeded.workspace.client_id,
        article_number=f"c6j-{seeded.workspace.client_id}",
        state=ItemStateEnum.PENDING,
        quantity=4,
        item_category_id=seeded.categories[0].client_id,
        properties={"wood_type": "Teak", "upholstery": "Down"},
    )
    db_session.add_all([task_b, item_b])
    await db_session.flush()
    db_session.add(
        TaskItem(
            client_id=f"tim_c6j_{seeded.workspace.client_id}",
            workspace_id=seeded.workspace.client_id,
            task_id=task_b.client_id,
            item_id=item_b.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=seeded.manager.client_id,
        )
    )
    await db_session.flush()
    b_result = await _CR(
        db_session,
        seeded,
        [
            {
                "stock_report_item_id": row.client_id,
                "task_id": task_b.client_id,
                "item_id": item_b.client_id,
                "override_property_mismatch": False,
            }
        ],
    )
    b_id = b_result["stock_task_assignments"][0]["client_id"]
    assert await _counters(db_session, row.client_id) == (8, 0, 0)
    captured = capture_dispatch(
        monkeypatch,
        "beyo_manager.services.commands.stock_report.delete_stock_task_assignments.dispatch",
    )

    result = await _DL(db_session, seeded, [a_id, a_id])

    assert result["deleted_client_ids"] == [a_id]
    assert await _counters(db_session, row.client_id) == (4, 0, 0)
    deleted_events = [e for e in captured if e.event_name == "stock_task_assignment:deleted"]
    assert len(deleted_events) == 1
    a = await _fresh_assignment(db_session, a_id)
    b = await _fresh_assignment(db_session, b_id)
    assert a.is_deleted is True
    assert b.is_deleted is False
    records = (
        (
            await db_session.execute(
                select(StockReportRepairRecord).where(
                    StockReportRepairRecord.workspace_id == seeded.workspace.client_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert records == []
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_repair_record_carries_the_delete_assignments_trigger(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _create_one(db_session, seeded, row)
    await db_session.execute(
        text(
            "UPDATE stock_report_items SET quantity_in_queue = 0 WHERE client_id = :id"
        ),
        {"id": row.client_id},
    )

    await _DL(db_session, seeded, [assignment_id])

    records = (
        (
            await db_session.execute(
                select(StockReportRepairRecord).where(
                    StockReportRepairRecord.workspace_id == seeded.workspace.client_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(records) == 1
    assert records[0].trigger == "inline:delete_assignments"


async def test_empty_client_ids_is_refused(db_session):
    """No lettered row names this. Kept as a **candidate criterion** (charter trace
    chain link 3): master plan §9 rule 18 asks every signature registered in §6.5 to
    be pinned by some row, and `DeleteStockTaskAssignmentsRequest`'s `min_length=1`
    is not. Renamed from `test_unknown_field_and_empty_client_ids_are_refused`,
    which claimed an unknown-field clause the body never exercised — the delete
    request model carries no `extra="forbid"`."""
    from beyo_manager.errors.validation import ValidationError

    seeded = await seed_stock_report_workspace(db_session)
    with pytest.raises(ValidationError):
        await delete_stock_task_assignments(
            make_ctx(
                db_session,
                seeded,
                role_name="worker",
                incoming_data={"client_ids": []},
            )
        )
