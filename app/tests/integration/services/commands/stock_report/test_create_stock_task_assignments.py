"""Plan 8 — `create_stock_task_assignments` (master plan §6.5; intention §9C MC-12,
MC-13 as amended by §14F F9/P44).

F0 (master plan §6.8): workspace W, manager U, category K, item I (`quantity 4`,
`properties {"wood_type": "Teak", "upholstery": "Down"}`), task T (`pending`,
PRIMARY = I), row R (identity K + `{"wood_group": ["teak"]}`, `quantity_requested 10`).
`CR(entries)` = `create_stock_task_assignments(make_ctx(role worker, incoming_data=
{"entries": entries}))`.

This file builds the behaviour and exercises one representative row per distinct code
path; it is not a row-by-row transcription of plan 8's criteria table (that discipline
and the mutation ledger belong to the tester — see the phase's Review log and the
implementer handoff for the rows this file does not exercise).
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from beyo_manager.domain.items.enums import ItemStateEnum
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.domain.stock_report.enums import (
    StockReportHistoryRecordTypeEnum,
    StockTaskAssignmentStateEnum as S,
)
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.errors.stock_report import (
    StockAssignmentPropertyMismatch,
    StockAssignmentRefused,
)
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.stock_report._move_assignment import (
    ASSIGNMENT_DELETE,
    move_assignment,
)
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from tests.helpers.statement_listener import count_writes, record_statements
from tests.helpers.stock_report import (
    assert_stock_report_clean,
    capture_dispatch,
    make_ctx,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
PROPERTIES = {"wood_type": "Teak", "upholstery": "Down"}


async def _make_row(db_session, seeded, *, criteria=None, quantity_requested=10, category=None):
    criteria = criteria if criteria is not None else {"wood_group": ["teak"]}
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=(category or seeded.categories[0]).client_id,
        properties=criteria,
        properties_signature=compute_stock_criteria_signature(criteria),
        quantity_requested=quantity_requested,
    )
    db_session.add(row)
    await db_session.flush()
    return row


async def _second_pair(db_session, seeded, suffix, *, quantity=4, category=None, primary=True):
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
        item_category_id=(category or seeded.categories[0]).client_id,
        properties=dict(PROPERTIES),
    )
    db_session.add_all([task, item])
    await db_session.flush()
    db_session.add(
        TaskItem(
            client_id=f"tim_{suffix}_{seeded.workspace.client_id}",
            workspace_id=seeded.workspace.client_id,
            task_id=task.client_id,
            item_id=item.client_id,
            role=TaskItemRoleEnum.PRIMARY if primary else TaskItemRoleEnum.RELATED,
            created_by_id=seeded.manager.client_id,
        )
    )
    await db_session.flush()
    return task, item


def _entry(row, task, item, *, override=False):
    """`row`/`task`/`item` may be a real ORM instance or a plain client_id string —
    the latter is used to name an id that must not resolve to anything."""
    return {
        "stock_report_item_id": row if isinstance(row, str) else row.client_id,
        "task_id": task if isinstance(task, str) else task.client_id,
        "item_id": item if isinstance(item, str) else item.client_id,
        "override_property_mismatch": override,
    }


async def _CR(db_session, seeded, entries, *, user=None):
    ctx = make_ctx(
        db_session,
        seeded,
        role_name="worker",
        user=user,
        incoming_data={"entries": entries},
    )
    return await create_stock_task_assignments(ctx)


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


async def _set_task_state(db_session, task, state):
    await db_session.execute(
        Task.__table__.update().where(Task.client_id == task.client_id).values(state=state)
    )


async def _make_goal(db_session, seeded, row, *, created_at=NOW):
    """The row's current goal record G (MC-5) — a `quantity_requested_change`
    history record. Rows C4(e)/C4(f) name `G` in their outcome."""
    record = StockReportHistoryRecord(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        type=StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
        quantity_requested=row.quantity_requested,
        quantity_awaiting=0,
        created_at=created_at,
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


async def _fresh_assignment(db_session, client_id):
    return (
        await db_session.execute(
            select(StockTaskAssignment)
            .where(StockTaskAssignment.client_id == client_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


async def _create_and_move(db_session, seeded, row, target, *, task=None, item=None):
    """Create A through `CR` (plan 8 §6: assignments in fixtures come from the
    command) and walk it to `target` with phase 4's `move_assignment` — `PR`
    (phase 9) does not exist in batch C1."""
    result = await _CR(
        db_session, seeded, [_entry(row, task or seeded.task, item or seeded.item)]
    )
    assignment_id = result["stock_task_assignments"][0]["client_id"]
    for state in target:
        assignment = await _fresh_assignment(db_session, assignment_id)
        await move_assignment(
            db_session, assignment, state,
            workspace_id=seeded.workspace.client_id,
            actor_user_id=seeded.manager.client_id, now=NOW, trigger="test",
        )
    return assignment_id


# ---------------------------------------------------------------------------
# Happy path — the write and the response shape
# ---------------------------------------------------------------------------


async def test_creates_assignment_moves_counters_and_returns_full_read_shape(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)

    result = await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])

    assignments = result["stock_task_assignments"]
    assert len(assignments) == 1
    payload = assignments[0]
    assert payload["state"] == "in_queue"
    assert payload["stock_report_item_id"] == row.client_id
    assert payload["task_id"] == seeded.task.client_id
    assert payload["item_id"] == seeded.item.client_id
    assert payload["quantity"] == 4
    assert payload["property_mismatch_overridden"] is False
    assert payload["created_by_id"] == seeded.manager.client_id
    assert payload["updated_by_id"] is None
    assert payload["updated_at"] is None
    assert set(payload) == {
        "client_id", "state", "stock_report_item_id", "task_id", "item_id",
        "quantity", "property_mismatch_overridden", "credited_history_record_id",
        "created_at", "created_by_id", "updated_at", "updated_by_id", "item", "task",
    }
    assert payload["item"]["client_id"] == seeded.item.client_id
    assert payload["task"]["client_id"] == seeded.task.client_id

    assert await _counters(db_session, row.client_id) == (4, 0, 0)

    refreshed_task = await db_session.get(Task, seeded.task.client_id)
    assert refreshed_task.is_stock_assignment is True

    assignment = await db_session.get(StockTaskAssignment, payload["client_id"])
    assert assignment.updated_by_id is None
    assert assignment.updated_at is None

    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_quantity_floors_at_one(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await db_session.execute(
        Item.__table__.update().where(Item.client_id == seeded.item.client_id).values(quantity=0)
    )

    result = await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])

    assert result["stock_task_assignments"][0]["quantity"] == 1
    assert await _counters(db_session, row.client_id) == (1, 0, 0)
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


@pytest.mark.parametrize(
    ("task_state", "expected_state", "expected_counters"),
    [
        (TaskStateEnum.ASSIGNED, "in_queue", (4, 0, 0)),
        (TaskStateEnum.WORKING, "in_progress", (0, 4, 0)),
        (TaskStateEnum.STALLED, "in_progress", (0, 4, 0)),
    ],
)
async def test_assignment_state_follows_the_task_state(
    db_session, task_state, expected_state, expected_counters
):
    """C4(b) `assigned`, C4(c) `working`, C4(d) `stalled` — one row per cell of
    `ASSIGNMENT_STATE_BY_TASK_STATE` that this phase's criteria name. The counters
    are moved by the operation, never written by the test."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _set_task_state(db_session, seeded.task, task_state)

    result = await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])

    assert result["stock_task_assignments"][0]["state"] == expected_state
    assert (await _counters(db_session, row.client_id)) == expected_counters
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c4e_ready_task_creates_awaiting_and_credits_the_goal(db_session):
    """C4(e): `ready` -> `awaiting`, counters `(0, 0, 4)`, the row's goal record G
    credited 4, and the assignment's credit memory pointing at G (MC-5)."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row)
    await _set_task_state(db_session, seeded.task, TaskStateEnum.READY)

    result = await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])

    payload = result["stock_task_assignments"][0]
    assert payload["state"] == "awaiting"
    assert (await _counters(db_session, row.client_id)) == (0, 0, 4)
    assert await _goal_awaiting(db_session, goal.client_id) == 4
    assignment = await _fresh_assignment(db_session, payload["client_id"])
    assert assignment.credited_history_record_id == goal.client_id
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_resolved_task_may_still_be_assigned(db_session):
    """C4(f): a `resolved` task may still be assigned — `awaiting`, and the goal
    record G is credited."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row)
    await _set_task_state(db_session, seeded.task, TaskStateEnum.RESOLVED)

    result = await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])

    assert result["stock_task_assignments"][0]["state"] == "awaiting"
    assert (await _counters(db_session, row.client_id)) == (0, 0, 4)
    assert await _goal_awaiting(db_session, goal.client_id) == 4
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c4g_quantity_is_copied_from_the_item(db_session):
    """C4(g): the assignment's quantity is the item's, not a constant. Distinct
    from C4(h), which exercises the `max(..., 1)` floor."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await db_session.execute(
        Item.__table__.update().where(Item.client_id == seeded.item.client_id).values(quantity=8)
    )

    result = await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])

    assert result["stock_task_assignments"][0]["quantity"] == 8
    assert (await _counters(db_session, row.client_id)) == (8, 0, 0)
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_two_entries_ascending_item_id_response_order_and_summed_counters(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    task2, item2 = await _second_pair(db_session, seeded, "c4k")

    ordered_pair = sorted([seeded.item.client_id, item2.client_id])
    entries_by_item = {
        seeded.item.client_id: _entry(row, seeded.task, seeded.item),
        item2.client_id: _entry(row, task2, item2),
    }
    # Supplied descending, to prove the response is sorted at build time and not by
    # request or creation order (master plan §10).
    entries = [entries_by_item[item_id] for item_id in reversed(ordered_pair)]

    result = await _CR(db_session, seeded, entries)

    returned_item_ids = [a["item_id"] for a in result["stock_task_assignments"]]
    assert returned_item_ids == ordered_pair
    assert (await _counters(db_session, row.client_id)) == (8, 0, 0)
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


# ---------------------------------------------------------------------------
# Phase 3 — the refusal chain (one representative row per reason)
# ---------------------------------------------------------------------------


async def test_stock_report_item_absent_is_refused(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(
            db_session,
            seeded,
            [_entry("sri_absent", seeded.task, seeded.item)],
        )
    assert excinfo.value.details == [{"index": 0, "reason": "stock_report_item_not_found"}]


async def test_row_soft_deleted_is_refused(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await db_session.execute(
        StockReportItem.__table__.update()
        .where(StockReportItem.client_id == row.client_id)
        .values(is_deleted=True)
    )
    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])
    assert excinfo.value.details == [{"index": 0, "reason": "stock_report_item_not_found"}]


async def test_c1c_row_in_a_foreign_workspace_is_refused(db_session):
    """C1(c): a **cross-workspace reference** — the foreign row carries this
    workspace's own category and criteria, so it is an otherwise-valid target and
    tenancy is the only reason the call refuses (plan 8 §6)."""
    seeded = await seed_stock_report_workspace(db_session)
    foreign_workspace = Workspace(
        client_id=f"ws_frn_{seeded.workspace.client_id}", name="Foreign"
    )
    db_session.add(foreign_workspace)
    await db_session.flush()
    criteria = {"wood_group": ["teak"]}
    foreign_row = StockReportItem(
        workspace_id=foreign_workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties=criteria,
        properties_signature=compute_stock_criteria_signature(criteria),
        quantity_requested=10,
    )
    db_session.add(foreign_row)
    await db_session.flush()

    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(db_session, seeded, [_entry(foreign_row, seeded.task, seeded.item)])
    assert excinfo.value.details == [{"index": 0, "reason": "stock_report_item_not_found"}]


async def test_c1e_absent_item_id_is_refused_item_not_found(db_session):
    """C1(e). `item_not_found` precedes `item_not_task_primary` in MC-13's order."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(db_session, seeded, [_entry(row, seeded.task, "itm_absent")])
    assert excinfo.value.details == [{"index": 0, "reason": "item_not_found"}]


async def test_c1g_retired_primary_link_is_refused_item_not_task_primary(db_session):
    """C1(g): the PRIMARY link exists but carries `removed_at`."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await db_session.execute(
        TaskItem.__table__.update()
        .where(TaskItem.task_id == seeded.task.client_id)
        .values(removed_at=NOW)
    )
    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])
    assert excinfo.value.details == [{"index": 0, "reason": "item_not_task_primary"}]


async def test_c1k_item_already_assigned_on_the_same_row_refuses_before_any_write(
    db_session,
):
    """C1(k) (owner card A): the pre-check refuses *before* attempting the write.
    The reason alone does not separate the pre-check from the `IntegrityError`
    backstop — `count_writes == 0` is the clause that does (master plan §9 rule 7,
    fifth ratified use)."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])

    async with record_statements(db_session) as statements:
        with pytest.raises(StockAssignmentRefused) as excinfo:
            await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])
    assert excinfo.value.details == [{"index": 0, "reason": "item_already_assigned"}]
    assert count_writes(statements, {"stock_task_assignments"}) == 0


async def test_c1n_category_mismatch_precedes_the_property_matcher(db_session):
    """C1(n) (U18): phase 3 runs to completion before phase 4, so a row that is
    both in the wrong category and failing the matcher answers 422
    `category_mismatch`, never the 409."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(
        db_session,
        seeded,
        criteria={"upholstery": ["velvet"]},
        category=seeded.categories[1],
    )
    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])
    assert excinfo.value.details == [{"index": 0, "reason": "category_mismatch"}]


async def test_related_item_is_refused_item_not_task_primary(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    task2, related_item = await _second_pair(db_session, seeded, "c1f", primary=False)
    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(db_session, seeded, [_entry(row, task2, related_item)])
    assert excinfo.value.details == [{"index": 0, "reason": "item_not_task_primary"}]


async def test_already_resolved_pair_is_refused_already_processed_by_scanner(db_session):
    """C1(p). Fixture per the plan: the retry names **R**, the same row, so the
    named mutation ("drop the check") lets a second assignment be born rather than
    producing some other refusal."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _create_and_move(db_session, seeded, row, (S.AWAITING, S.RESOLVED))

    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])
    assert excinfo.value.details == [{"index": 0, "reason": "already_processed_by_scanner"}]


async def test_c1q_resolved_early_on_another_row_is_refused_already_processed(db_session):
    """C1(q): §14F F9 keys on the (task, item) pair, "on any row" — the retry names
    R2, a different row, and is still refused."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _create_and_move(db_session, seeded, row, (S.RESOLVED_EARLY,))
    # R2 is a different row that the item would otherwise match: §14F F9 is the
    # only reason the second request refuses.
    row2 = await _make_row(db_session, seeded, criteria={"upholstery": ["down"]})

    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(db_session, seeded, [_entry(row2, seeded.task, seeded.item)])
    assert excinfo.value.details == [{"index": 0, "reason": "already_processed_by_scanner"}]


async def test_c1r_a_new_task_for_the_same_item_is_not_affected(db_session):
    """C1(r): §14F F9 keys on the pair, not the item — a brand-new task for an item
    Scanner has already reported may be assigned."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _create_and_move(db_session, seeded, row, (S.AWAITING, S.RESOLVED))
    task2, _ = await _second_pair(db_session, seeded, "c1r", primary=False)
    # T's PRIMARY link is retired and T2 becomes the item's PRIMARY task.
    await db_session.execute(
        TaskItem.__table__.update()
        .where(TaskItem.task_id == seeded.task.client_id)
        .values(removed_at=NOW)
    )
    await db_session.execute(
        TaskItem.__table__.update()
        .where(TaskItem.task_id == task2.client_id)
        .values(item_id=seeded.item.client_id, role=TaskItemRoleEnum.PRIMARY)
    )

    result = await _CR(db_session, seeded, [_entry(row, task2, seeded.item)])

    assert result["stock_task_assignments"][0]["state"] == "in_queue"
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1s_a_soft_deleted_resolved_assignment_does_not_refuse(db_session):
    """C1(s): §14F F9 counts only non-deleted assignments — a user who unassigned
    the reported pair may assign it again."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _create_and_move(
        db_session, seeded, row, (S.AWAITING, S.RESOLVED)
    )
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, ASSIGNMENT_DELETE,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id, now=NOW, trigger="test",
    )

    result = await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])

    assert result["stock_task_assignments"][0]["state"] == "in_queue"
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c1t_item_not_task_primary_comes_before_already_processed(db_session):
    """C1(t): MC-13's adjacent pair `item_not_task_primary` -> `already_processed_
    by_scanner`. Both predicates hold; the earlier reason is the answer."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _create_and_move(db_session, seeded, row, (S.AWAITING, S.RESOLVED))
    await db_session.execute(
        TaskItem.__table__.update()
        .where(TaskItem.task_id == seeded.task.client_id)
        .values(role=TaskItemRoleEnum.RELATED)
    )

    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])
    assert excinfo.value.details == [{"index": 0, "reason": "item_not_task_primary"}]


async def test_c1v_soft_deleted_task_is_refused_task_not_found(db_session):
    """C1(v) (owner card 1, batch C1 review finding B1): T is soft-deleted but
    otherwise a valid target (`pending`, I PRIMARY on it, category and properties
    matching R) — MC-16's `tasks.is_deleted = false` creation-lookup predicate is
    the only reason the call refuses. Nothing is written: no assignment row, R's
    counters stay at F0's zeros, T's `is_stock_assignment` is not set."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await db_session.execute(
        Task.__table__.update()
        .where(Task.client_id == seeded.task.client_id)
        .values(is_deleted=True)
    )
    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])
    assert excinfo.value.details == [{"index": 0, "reason": "task_not_found"}]
    assert (
        await db_session.execute(
            select(StockTaskAssignment).where(
                StockTaskAssignment.workspace_id == seeded.workspace.client_id
            )
        )
    ).scalars().all() == []
    assert (await _counters(db_session, row.client_id)) == (0, 0, 0)
    refreshed_task = await db_session.get(Task, seeded.task.client_id)
    assert refreshed_task.is_stock_assignment is False


async def test_c1w_soft_deleted_item_is_refused_item_not_found(db_session):
    """C1(w) (owner card 1, batch C1 review finding B1): I is soft-deleted but
    otherwise a valid target (PRIMARY on a `pending` T, category and properties
    matching R) — MC-16's `items.is_deleted = false` creation-lookup predicate is
    the only reason the call refuses. Nothing is written: no assignment row, R's
    `quantity_in_queue` does not rise by I's quantity, T's `is_stock_assignment` is
    not set."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await db_session.execute(
        Item.__table__.update()
        .where(Item.client_id == seeded.item.client_id)
        .values(is_deleted=True)
    )
    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])
    assert excinfo.value.details == [{"index": 0, "reason": "item_not_found"}]
    assert (
        await db_session.execute(
            select(StockTaskAssignment).where(
                StockTaskAssignment.workspace_id == seeded.workspace.client_id
            )
        )
    ).scalars().all() == []
    assert (await _counters(db_session, row.client_id)) == (0, 0, 0)
    refreshed_task = await db_session.get(Task, seeded.task.client_id)
    assert refreshed_task.is_stock_assignment is False


async def test_c1u_already_processed_comes_before_task_failed_or_cancelled(db_session):
    """C1(u): MC-13's adjacent pair `already_processed_by_scanner` ->
    `task_failed_or_cancelled`. Both predicates hold; the earlier reason wins."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _create_and_move(db_session, seeded, row, (S.AWAITING, S.RESOLVED))
    await _set_task_state(db_session, seeded.task, TaskStateEnum.FAILED)

    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])
    assert excinfo.value.details == [{"index": 0, "reason": "already_processed_by_scanner"}]


@pytest.mark.parametrize(
    "task_state", [TaskStateEnum.FAILED, TaskStateEnum.CANCELLED]
)
async def test_failed_task_is_refused(db_session, task_state):
    """C1(h) (`failed`) and C1(i) (`cancelled`) — one row per member of the refused
    task-state set, never a sampled one (charter rule 2)."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _set_task_state(db_session, seeded.task, task_state)
    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])
    assert excinfo.value.details == [{"index": 0, "reason": "task_failed_or_cancelled"}]


async def test_item_already_assigned_is_refused_before_any_write(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])

    row2 = await _make_row(db_session, seeded, criteria={"wood_group": ["oak"]}, quantity_requested=1)
    task2, _ = await _second_pair(db_session, seeded, "c1j", primary=False)
    # Re-point task2's PRIMARY link onto seeded.item so it is a legal target of a
    # second entry naming the same (already-assigned) item.
    await db_session.execute(
        TaskItem.__table__.update()
        .where(TaskItem.task_id == task2.client_id)
        .values(item_id=seeded.item.client_id, role=TaskItemRoleEnum.PRIMARY)
    )

    async with record_statements(db_session) as statements:
        with pytest.raises(StockAssignmentRefused) as excinfo:
            await _CR(db_session, seeded, [_entry(row2, task2, seeded.item)])
    assert excinfo.value.details == [{"index": 0, "reason": "item_already_assigned"}]
    assert count_writes(statements, {"stock_task_assignments"}) == 0


async def test_item_has_no_category_is_refused(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await db_session.execute(
        Item.__table__.update().where(Item.client_id == seeded.item.client_id).values(
            item_category_id=None
        )
    )
    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])
    assert excinfo.value.details == [{"index": 0, "reason": "item_has_no_category"}]


async def test_category_mismatch_is_refused(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, category=seeded.categories[1])
    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])
    assert excinfo.value.details == [{"index": 0, "reason": "category_mismatch"}]


async def test_all_or_nothing_valid_entry_writes_nothing_when_a_later_entry_fails(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    row2 = await _make_row(db_session, seeded, criteria={"wood_group": ["oak"]}, quantity_requested=1)
    _, item2 = await _second_pair(db_session, seeded, "c1o", primary=False)
    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(
            db_session,
            seeded,
            [
                _entry(row, seeded.task, seeded.item),
                _entry(row2, "tsk_absent", item2),
            ],
        )
    assert excinfo.value.details == [{"index": 1, "reason": "task_not_found"}]
    assert (
        await db_session.execute(
            select(StockTaskAssignment).where(
                StockTaskAssignment.workspace_id == seeded.workspace.client_id
            )
        )
    ).scalars().all() == []


# ---------------------------------------------------------------------------
# Phase 1 — in-batch duplicates
# ---------------------------------------------------------------------------


async def test_duplicate_item_in_batch_names_every_offending_index(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    task2, _ = await _second_pair(db_session, seeded, "c2a", primary=False)
    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(
            db_session,
            seeded,
            [
                _entry(row, seeded.task, seeded.item),
                _entry(row, task2, seeded.item),
            ],
        )
    assert excinfo.value.details == [
        {"index": 0, "reason": "duplicate_item_in_batch"},
        {"index": 1, "reason": "duplicate_item_in_batch"},
    ]


async def test_duplicate_task_in_batch_names_every_offending_index(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    _, item2 = await _second_pair(db_session, seeded, "c2b", primary=False)
    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(
            db_session,
            seeded,
            [
                _entry(row, seeded.task, seeded.item),
                _entry(row, seeded.task, item2),
            ],
        )
    assert excinfo.value.details == [
        {"index": 0, "reason": "duplicate_task_in_batch"},
        {"index": 1, "reason": "duplicate_task_in_batch"},
    ]


async def test_c2c_phase1_and_phase3_reasons_arrive_in_one_error(db_session):
    """C2(c): phase 1's duplicates are *collected into* phase 3's error — one 422
    carrying all three offending indices, never a phase-1-only refusal."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    task_b, item_b = await _second_pair(db_session, seeded, "c2c1")
    task_c, _ = await _second_pair(db_session, seeded, "c2c2", primary=False)

    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(
            db_session,
            seeded,
            [
                _entry(row, seeded.task, seeded.item),
                _entry(row, task_b, item_b),
                _entry(row, task_c, seeded.item),
                _entry(row, "tsk_absent", "itm_absent"),
            ],
        )
    assert excinfo.value.details == [
        {"index": 0, "reason": "duplicate_item_in_batch"},
        {"index": 2, "reason": "duplicate_item_in_batch"},
        {"index": 3, "reason": "task_not_found"},
    ]


# ---------------------------------------------------------------------------
# Phase 4 — the property matcher
# ---------------------------------------------------------------------------


async def test_property_mismatch_without_override_raises_409_with_sorted_failures(db_session):
    """C3(a) (S3/S4 fold, 2026-09-21): the fixture carries a fourth, short
    late-alphabet key (`zone`) precisely because criteria are stored as JSONB and
    Postgres orders JSONB keys by length then bytes — for the original three keys
    that order happens to coincide with alphabetical, so the "sorted failures"
    sub-check could not fail (L-14). With `zone` present, JSONB order is
    `zone, quantity, upholstery, wood_group` while the assertion below is
    alphabetical, so dropping the matcher's sort reddens this test."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(
        db_session,
        seeded,
        criteria={
            "quantity": ["4"],
            "upholstery": ["down"],
            "wood_group": ["teak"],
            "zone": ["a1"],
        },
    )
    await db_session.execute(
        Item.__table__.update().where(Item.client_id == seeded.item.client_id).values(
            properties={}, quantity=1
        )
    )
    with pytest.raises(StockAssignmentPropertyMismatch) as excinfo:
        await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])
    assert excinfo.value.details == [
        {
            "index": 0,
            "stock_report_item_id": row.client_id,
            "task_id": seeded.task.client_id,
            "item_id": seeded.item.client_id,
            "failures": [
                {"key": "quantity", "reason": "value_not_accepted"},
                {"key": "upholstery", "reason": "missing_on_item"},
                {"key": "wood_group", "reason": "missing_on_item"},
                {"key": "zone", "reason": "missing_on_item"},
            ],
        }
    ]
    assert (
        await db_session.execute(
            select(StockTaskAssignment).where(
                StockTaskAssignment.workspace_id == seeded.workspace.client_id
            )
        )
    ).scalars().all() == []


async def test_override_on_a_mismatching_entry_creates_with_flag_true(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(
        db_session, seeded, criteria={"quantity": ["4"], "upholstery": ["down"], "wood_group": ["teak"]}
    )
    await db_session.execute(
        Item.__table__.update().where(Item.client_id == seeded.item.client_id).values(
            properties={}, quantity=1
        )
    )
    result = await _CR(
        db_session, seeded, [_entry(row, seeded.task, seeded.item, override=True)]
    )
    payload = result["stock_task_assignments"][0]
    assert payload["property_mismatch_overridden"] is True
    assert payload["state"] == "in_queue"
    assert (await _counters(db_session, row.client_id)) == (1, 0, 0)
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_override_on_a_matching_entry_is_ignored(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    result = await _CR(
        db_session, seeded, [_entry(row, seeded.task, seeded.item, override=True)]
    )
    assert result["stock_task_assignments"][0]["property_mismatch_overridden"] is False
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c3d_retry_after_a_409_is_re_evaluated_from_scratch(db_session):
    """C3(d): the retry is a fresh request — phase 3 runs again before phase 4, so
    a task cancelled since the 409 answers 422 `task_failed_or_cancelled` and the
    override never reaches the matcher."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(
        db_session, seeded, criteria={"upholstery": ["velvet"]}
    )
    with pytest.raises(StockAssignmentPropertyMismatch):
        await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])

    await _set_task_state(db_session, seeded.task, TaskStateEnum.CANCELLED)

    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(
            db_session, seeded, [_entry(row, seeded.task, seeded.item, override=True)]
        )
    assert excinfo.value.details == [{"index": 0, "reason": "task_failed_or_cancelled"}]


async def test_unknown_top_level_field_is_refused_422(db_session):
    """C3(e): an unknown field at either level is a 422. The entry list is
    **valid** here — an empty `entries` would refuse for C3(f)'s reason instead and
    leave this row unable to fail (charter rule 2's companion)."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    valid = _entry(row, seeded.task, seeded.item)

    with pytest.raises(ValidationError):
        await create_stock_task_assignments(
            make_ctx(
                db_session,
                seeded,
                role_name="worker",
                incoming_data={"entries": [valid], "unexpected": True},
            )
        )

    with pytest.raises(ValidationError):
        await create_stock_task_assignments(
            make_ctx(
                db_session,
                seeded,
                role_name="worker",
                incoming_data={"entries": [{**valid, "unexpected": True}]},
            )
        )


async def test_empty_entries_is_refused_422(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    ctx = make_ctx(
        db_session, seeded, role_name="worker", incoming_data={"entries": []}
    )
    with pytest.raises(ValidationError):
        await create_stock_task_assignments(ctx)


# ---------------------------------------------------------------------------
# Events — coalescing (MC-19)
# ---------------------------------------------------------------------------


async def test_two_entries_on_one_row_dispatch_two_created_and_one_coalesced_updated(
    db_session, monkeypatch
):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    task2, item2 = await _second_pair(db_session, seeded, "c7a")
    captured = capture_dispatch(
        monkeypatch,
        "beyo_manager.services.commands.stock_report.create_stock_task_assignments.dispatch",
    )

    await _CR(
        db_session,
        seeded,
        [_entry(row, seeded.task, seeded.item), _entry(row, task2, item2)],
    )

    created = [e for e in captured if e.event_name == "stock_task_assignment:created"]
    updated = [e for e in captured if e.event_name == "stock_report_item:updated"]
    assert len(created) == 2
    assert len(updated) == 1
    assert updated[0].extra["quantity_in_queue"] == 8
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_refused_request_dispatches_nothing(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    captured = capture_dispatch(
        monkeypatch,
        "beyo_manager.services.commands.stock_report.create_stock_task_assignments.dispatch",
    )
    with pytest.raises(StockAssignmentRefused):
        await _CR(
            db_session,
            seeded,
            [_entry(row, "tsk_absent", seeded.item)],
        )
    assert captured == []
