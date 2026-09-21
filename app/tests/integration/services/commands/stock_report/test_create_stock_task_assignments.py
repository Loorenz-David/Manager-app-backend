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
from beyo_manager.domain.stock_report.enums import StockTaskAssignmentStateEnum as S
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.errors.stock_report import (
    StockAssignmentPropertyMismatch,
    StockAssignmentRefused,
)
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.stock_report._move_assignment import move_assignment
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


async def test_resolved_task_may_still_be_assigned(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await db_session.execute(
        Task.__table__.update().where(Task.client_id == seeded.task.client_id).values(
            state=TaskStateEnum.RESOLVED
        )
    )

    result = await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])

    assert result["stock_task_assignments"][0]["state"] == "awaiting"
    assert (await _counters(db_session, row.client_id)) == (0, 0, 4)


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


async def test_related_item_is_refused_item_not_task_primary(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    task2, related_item = await _second_pair(db_session, seeded, "c1f", primary=False)
    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(db_session, seeded, [_entry(row, task2, related_item)])
    assert excinfo.value.details == [{"index": 0, "reason": "item_not_task_primary"}]


async def test_already_resolved_pair_is_refused_already_processed_by_scanner(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    result = await _CR(db_session, seeded, [_entry(row, seeded.task, seeded.item)])
    assignment = await db_session.get(StockTaskAssignment, result["stock_task_assignments"][0]["client_id"])
    await move_assignment(
        db_session, assignment, S.AWAITING, workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id, now=NOW, trigger="test",
    )
    await move_assignment(
        db_session, assignment, S.RESOLVED, workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id, now=NOW, trigger="test",
    )
    row2 = await _make_row(db_session, seeded, criteria={"wood_group": ["oak"]}, quantity_requested=1)
    with pytest.raises(StockAssignmentRefused) as excinfo:
        await _CR(db_session, seeded, [_entry(row2, seeded.task, seeded.item)])
    assert excinfo.value.details == [{"index": 0, "reason": "already_processed_by_scanner"}]


async def test_failed_task_is_refused(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await db_session.execute(
        Task.__table__.update().where(Task.client_id == seeded.task.client_id).values(
            state=TaskStateEnum.FAILED
        )
    )
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


# ---------------------------------------------------------------------------
# Phase 4 — the property matcher
# ---------------------------------------------------------------------------


async def test_property_mismatch_without_override_raises_409_with_sorted_failures(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(
        db_session, seeded, criteria={"quantity": ["4"], "upholstery": ["down"], "wood_group": ["teak"]}
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


async def test_override_on_a_matching_entry_is_ignored(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    result = await _CR(
        db_session, seeded, [_entry(row, seeded.task, seeded.item, override=True)]
    )
    assert result["stock_task_assignments"][0]["property_mismatch_overridden"] is False


async def test_unknown_top_level_field_is_refused_422(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    ctx = make_ctx(
        db_session,
        seeded,
        role_name="worker",
        incoming_data={"entries": [], "unexpected": True},
    )
    with pytest.raises(ValidationError):
        await create_stock_task_assignments(ctx)


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
