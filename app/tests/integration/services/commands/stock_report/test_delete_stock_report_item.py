"""Plan 13 — `delete_stock_report_item` and the MC-16 cascade (master plan §6.5;
intention §5A MC-16, MC-1's second trigger and instrument (c), MC-5, MC-17, MC-19).

Fixture, per plan 13 §6: assignments are created through `CR`; terminal states are
reached with phase 4's `move_assignment` and **never** with `PR` (this phase depends
on 12 and 8, not on 9, so the fixture must stay armed whatever order the batches
run in). `priority`/`priority_order` are written by raw SQL, and the seed orders the
group **against** its ordering key — A holds order 1 with the group's largest
`client_id` — so a gap close that renumbers by `client_id` cannot pass.

This file exercises one representative case per code path; row-by-row transcription
and mutation arming belong to the tester (see the implementer handoff).
"""

import itertools
import time
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from beyo_manager.config import Settings
from beyo_manager.domain.items.enums import ItemStateEnum
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
    normalize_stock_criteria,
)
from beyo_manager.domain.stock_report.enums import (
    StockReportHistoryRecordTypeEnum,
    StockReportRepairTargetKindEnum,
    StockTaskAssignmentStateEnum as S,
)
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
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
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.stock_report._move_assignment import move_assignment
from beyo_manager.services.commands.stock_report.apply_stock_demand import (
    apply_stock_demand,
)
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from beyo_manager.services.commands.stock_report.delete_stock_report_item import (
    delete_stock_report_item,
)
from beyo_manager.services.commands.stock_report.stock_demand_entries import DemandEntry
from tests.helpers.stock_report import (
    ensure_active_snapshots,
    latest_snapshot,
    set_snapshot_position,
    snapshot_id_of,
    snapshot_positions,
    assert_stock_report_clean,
    capture_dispatch,
    make_ctx,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
DELETE_SITE = (
    "beyo_manager.services.commands.stock_report.delete_stock_report_item.dispatch"
)
CRITERIA = {"wood_group": ["teak"]}
_TIMEOUT_MS = Settings.model_fields["stock_demand_webhook_timeout_ms"].default


async def _make_row(session, seeded, *, criteria=None, quantity_requested=10):
    criteria = CRITERIA if criteria is None else criteria
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties=criteria,
        properties_signature=compute_stock_criteria_signature(criteria),
        quantity_requested=quantity_requested,
    )
    session.add(row)
    await session.flush()
    return row


_scalar_ids = itertools.count(2)


async def _make_pair(session, seeded, *, quantity):
    """One more (item, task) pair shaped like F0's, so a second assignment is
    reachable: a task holds one active PRIMARY item and an item holds one active
    assignment (§6.1b)."""
    suffix = uuid4().hex[:10]
    item = Item(
        client_id=f"itm_sr_{suffix}",
        workspace_id=seeded.workspace.client_id,
        article_number=f"SR-{suffix}",
        state=ItemStateEnum.PENDING,
        quantity=quantity,
        item_category_id=seeded.categories[0].client_id,
        properties={"wood_type": "Teak", "upholstery": "Down"},
    )
    task = Task(
        client_id=f"tsk_sr_{suffix}",
        workspace_id=seeded.workspace.client_id,
        task_scalar_id=next(_scalar_ids),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=seeded.manager.client_id,
    )
    session.add_all([item, task])
    await session.flush()
    session.add(
        TaskItem(
            client_id=f"tim_sr_{suffix}",
            workspace_id=seeded.workspace.client_id,
            task_id=task.client_id,
            item_id=item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=seeded.manager.client_id,
        )
    )
    await session.flush()
    return item, task


async def _CR(session, seeded, row, item, task):
    ctx = make_ctx(
        session,
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


async def _fresh_assignment(session, client_id):
    return (
        await session.execute(
            select(StockTaskAssignment)
            .where(StockTaskAssignment.client_id == client_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


async def _move(session, seeded, assignment_id, target):
    assignment = await _fresh_assignment(session, assignment_id)
    await move_assignment(
        session,
        assignment,
        target,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="test",
    )


async def _counters(session, row_id):
    return (
        await session.execute(
            select(
                StockReportItem.quantity_in_queue,
                StockReportItem.quantity_in_progress,
                StockReportItem.quantity_awaiting,
            ).where(StockReportItem.client_id == row_id)
        )
    ).one()


async def _make_goal(session, seeded, row):
    record = StockReportHistoryRecord(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        type=StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
        quantity_requested=row.quantity_requested,
        quantity_awaiting=0,
        created_at=NOW,
    )
    session.add(record)
    await session.flush()
    return record


async def _goal_awaiting(session, goal_id):
    return await session.scalar(
        select(StockReportHistoryRecord.quantity_awaiting).where(
            StockReportHistoryRecord.client_id == goal_id
        )
    )


async def _DR(session, seeded, client_id, *, monkeypatch=None):
    captured = (
        capture_dispatch(monkeypatch, DELETE_SITE) if monkeypatch is not None else None
    )
    ctx = make_ctx(session, seeded, incoming_data={"client_id": client_id})
    result = await delete_stock_report_item(ctx)
    return result, ctx, captured


async def _seed_high_group(session, seeded, row):
    """`high` = A1 R2 C3, with `priority_order` ascending disagreeing with
    `client_id` ascending: A carries the group's largest `client_id`."""
    others = [
        await _make_row(session, seeded, criteria={"wood_group": [f"oak{index}"]})
        for index in range(2)
    ]
    ids = sorted([row.client_id] + [other.client_id for other in others], reverse=True)
    # R keeps order 2 whatever its id sorts to; the other two take 1 and 3 so that
    # the largest id holds order 1.
    ordered = [client_id for client_id in ids if client_id != row.client_id]
    plan = [(ordered[0], 1), (row.client_id, 2), (ordered[1], 3)]
    # Positions live on the active item snapshot (2026-09-26).
    await ensure_active_snapshots(session, seeded.workspace.client_id, now=NOW)
    for client_id, order in plan:
        await set_snapshot_position(session, client_id, "high", order)
    await session.flush()
    return ordered[0], ordered[1]  # A (order 1), C (order 3)


async def _orders(session, workspace_id):
    """`row_id -> priority_order` over every snapshot of the workspace, the deleted
    row's closed one included (one version in these tests)."""
    return {
        row_id: order
        for row_id, (_priority, order) in (
            await snapshot_positions(session, workspace_id, include_closed=True)
        ).items()
    }


# ---------------------------------------------------------------------------
# The cascade
# ---------------------------------------------------------------------------


async def test_cascade_removes_every_assignment_and_soft_deletes_the_row(
    db_session, monkeypatch
):
    """C1(a): four assignments across all four relevant states; only the awaiting
    one's credit is subtracted (a `resolved` and a `resolved_early` credit are kept,
    §14F F4), the counters end at zero, every task flag clears, and the row and its
    history carry the deletion stamps."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row)
    workspace_id = seeded.workspace.client_id

    # A1 awaiting q=2 (credited), A2 resolved q=3 (credited via awaiting, kept),
    # A3 in_queue q=1 (never credited), A4 resolved_early q=5 (credited, kept).
    item1, task1 = await _make_pair(db_session, seeded, quantity=2)
    a1 = await _CR(db_session, seeded, row, item1, task1)
    await _move(db_session, seeded, a1, S.AWAITING)

    item2, task2 = await _make_pair(db_session, seeded, quantity=3)
    a2 = await _CR(db_session, seeded, row, item2, task2)
    await _move(db_session, seeded, a2, S.AWAITING)
    await _move(db_session, seeded, a2, S.RESOLVED)

    item3, task3 = await _make_pair(db_session, seeded, quantity=1)
    a3 = await _CR(db_session, seeded, row, item3, task3)

    item4, task4 = await _make_pair(db_session, seeded, quantity=5)
    a4 = await _CR(db_session, seeded, row, item4, task4)
    await _move(db_session, seeded, a4, S.RESOLVED_EARLY)

    assert await _goal_awaiting(db_session, goal.client_id) == 10

    _result, ctx, captured = await _DR(
        db_session, seeded, row.client_id, monkeypatch=monkeypatch
    )

    for assignment_id in (a1, a2, a3, a4):
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.is_deleted is True
        assert assignment.deleted_by_id == seeded.manager.client_id
        assert assignment.deleted_at == ctx.now
    # Only A1's credit is subtracted; A2's and A4's are kept.
    assert await _goal_awaiting(db_session, goal.client_id) == 8
    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    for task in (task1, task2, task3, task4):
        refreshed = await db_session.get(Task, task.client_id)
        await db_session.refresh(refreshed)
        assert refreshed.is_stock_assignment is False

    deleted_row = (
        await db_session.execute(
            select(StockReportItem)
            .where(StockReportItem.client_id == row.client_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert deleted_row.is_deleted is True
    assert deleted_row.deleted_at == ctx.now
    assert deleted_row.deleted_by_id == seeded.manager.client_id
    assert deleted_row.updated_at == ctx.now
    assert deleted_row.updated_by_id == seeded.manager.client_id

    history = (
        (
            await db_session.execute(
                select(StockReportHistoryRecord)
                .where(StockReportHistoryRecord.stock_report_item_id == row.client_id)
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    assert history and all(record.is_deleted for record in history)
    assert all(record.deleted_at == ctx.now for record in history)
    assert all(
        record.deleted_by_id == seeded.manager.client_id for record in history
    )

    # MC-19: one `:deleted` for the row, one per assignment, and **no** `:updated`
    # for the row even though its counters moved four times.
    names = [event.event_name for event in captured]
    assert names.count("stock_task_assignment:deleted") == 4
    assert names.count("stock_report_item:deleted") == 1
    assert "stock_report_item:updated" not in names

    # C3(b): the `:deleted` event's **shape** (master plan §6.7, §6.5, §9 rule 18;
    # the published frontend contract §7). Until this block existed the builder
    # was registered and pinned by nothing — the re-review set its payload to junk
    # and all six delete tests passed. `extra` is asserted as EQUALITY: a subset
    # check ("no forbidden key present") is what let the junk through.
    deleted_event = next(
        event for event in captured if event.event_name == "stock_report_item:deleted"
    )
    assert deleted_event.event_name == "stock_report_item:deleted"
    assert deleted_event.client_id == row.client_id
    assert deleted_event.workspace_id == deleted_row.workspace_id
    assert deleted_event.extra == {}
    assert await _goal_awaiting(db_session, goal.client_id) == 8
    assert (
        await db_session.execute(
            select(StockReportRepairRecord).where(
                StockReportRepairRecord.workspace_id == workspace_id
            )
        )
    ).scalars().all() == []


async def test_the_group_closes_its_gap_and_the_deleted_row_keeps_its_own_order(
    db_session, monkeypatch
):
    """C1(b): `high` = A1 R2 C3; after `DR(R)` the group is A1 C2 and R keeps
    `priority_order 2` on its own deleted row."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    A, C = await _seed_high_group(db_session, seeded, row)
    workspace_id = seeded.workspace.client_id

    _result, _ctx, captured = await _DR(
        db_session, seeded, row.client_id, monkeypatch=monkeypatch
    )

    orders = await _orders(db_session, workspace_id)
    assert orders[A] == 1
    assert orders[C] == 2
    assert orders[row.client_id] == 2  # the deleted row is outside every group
    deleted_snapshot = await latest_snapshot(db_session, row.client_id)
    assert deleted_snapshot.closed_at is not None
    assert deleted_snapshot.priority.value == "high"
    assert [
        (event.event_name, event.client_id) for event in captured
    ] == [
        ("stock_report_item_snapshot:updated", await snapshot_id_of(db_session, C)),
        ("stock_report_item:deleted", row.client_id),
    ]
    await assert_stock_report_clean(db_session, workspace_id)


async def test_a_counter_left_non_zero_is_repaired_to_zero_and_recorded(db_session):
    """C2(a): the second self-heal trigger. `quantity_in_queue` is drifted to 4 by
    raw SQL; A's move leaves 3 (no repair — 3 >= 0), and the post-loop trigger sets
    it to 0 with one record, then the deletion proceeds."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    item1, task1 = await _make_pair(db_session, seeded, quantity=1)
    await _CR(db_session, seeded, row, item1, task1)
    await db_session.execute(
        text(
            "UPDATE stock_report_items SET quantity_in_queue = 4 "
            "WHERE client_id = :client_id"
        ),
        {"client_id": row.client_id},
    )
    workspace_id = seeded.workspace.client_id

    _result, ctx, _captured = await _DR(db_session, seeded, row.client_id)

    assert await _counters(db_session, row.client_id) == (0, 0, 0)
    records = (
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
    assert len(records) == 1
    record = records[0]
    # C2(a) names the record's full shape, `stock_report_item` included: master
    # plan §6.5 maps a `counter_*` divergence to STOCK_REPORT_ITEM, and this is
    # the only assertion in the batch that pins the cascade's own mapping.
    assert record.target_kind == StockReportRepairTargetKindEnum.STOCK_REPORT_ITEM
    assert record.target_client_id == row.client_id
    assert record.field == "quantity_in_queue"
    assert record.stored_value == "3"
    assert record.recomputed_value == "0"
    assert record.trigger == "inline:delete_stock_report_item"
    assert record.created_by_id is None
    assert record.created_at == ctx.now
    deleted_row = (
        await db_session.execute(
            select(StockReportItem)
            .where(StockReportItem.client_id == row.client_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert deleted_row.is_deleted is True


async def test_instrument_c_reads_stored_before_fresh_after_the_guarded_statement(
    db_session,
):
    """C2(b): A1 q=2 and A2 q=3 both `in_queue` with the counter drifted to 3.
    A1's move leaves 1; A2's would write -2, so the guarded statement returns zero
    rows and the inline repair writes **one** record with `stored "1"` — the value
    a fresh `SELECT` sees, not the 3 the ORM instance was loaded with. No
    second-trigger record follows, because the counter is already 0."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    item1, task1 = await _make_pair(db_session, seeded, quantity=2)
    await _CR(db_session, seeded, row, item1, task1)
    item2, task2 = await _make_pair(db_session, seeded, quantity=3)
    await _CR(db_session, seeded, row, item2, task2)
    # The cascade's loop runs in ascending `client_id`, and a ULID carries no
    # monotonic counter (master plan §10) — so the quantities are bound to the
    # **sorted real ids**, not to creation order, or this row would assert a
    # different `stored_before` on half its runs.
    a1, a2 = sorted(
        (
            await db_session.execute(
                select(StockTaskAssignment.client_id).where(
                    StockTaskAssignment.stock_report_item_id == row.client_id
                )
            )
        )
        .scalars()
        .all()
    )
    for assignment_id, quantity in ((a1, 2), (a2, 3)):
        await db_session.execute(
            text(
                "UPDATE stock_task_assignments SET quantity = :quantity "
                "WHERE client_id = :client_id"
            ),
            {"quantity": quantity, "client_id": assignment_id},
        )
    await db_session.execute(
        text(
            "UPDATE stock_report_items SET quantity_in_queue = 3 "
            "WHERE client_id = :client_id"
        ),
        {"client_id": row.client_id},
    )
    workspace_id = seeded.workspace.client_id

    await _DR(db_session, seeded, row.client_id)

    records = (
        (
            await db_session.execute(
                select(StockReportRepairRecord)
                .where(StockReportRepairRecord.workspace_id == workspace_id)
                .order_by(StockReportRepairRecord.created_at)
            )
        )
        .scalars()
        .all()
    )
    assert [
        (r.field, r.stored_value, r.recomputed_value, r.trigger) for r in records
    ] == [
        ("quantity_in_queue", "1", "0", "inline:delete_stock_report_item"),
    ]
    assert await _counters(db_session, row.client_id) == (0, 0, 0)


async def test_delete_refuses_deleted_absent_and_foreign_rows(db_session):
    """C1(d): the foreign row is a cross-workspace reference — same category name,
    same properties — so tenancy is the only reason the call refuses."""
    seeded = await seed_stock_report_workspace(db_session)
    foreign = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    foreign_row = await _make_row(db_session, foreign)
    await db_session.execute(
        text(
            "UPDATE stock_report_items SET is_deleted = true WHERE client_id = :cid"
        ),
        {"cid": row.client_id},
    )
    await db_session.flush()

    for client_id in (row.client_id, "sri_absent", foreign_row.client_id):
        with pytest.raises(NotFound):
            await _DR(db_session, seeded, client_id)

    still_live = (
        await db_session.execute(
            select(StockReportItem.is_deleted)
            .where(StockReportItem.client_id == foreign_row.client_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert still_live is False


async def test_a_demand_for_the_same_identity_after_deletion_creates_a_new_row(
    db_session,
):
    """C1(c): after `DR(R)`, a **demand delivery** carrying R's identity produces a
    **new** live row with empty history — it does not revive R and does not inherit
    R's records.

    Proven at the delivery surface the row names (`apply_stock_demand`), not at
    `discover_live_rows_by_identity`: proving it at the lookup would be a §9 rule 17
    relocation to a narrower surface, which is the owner's. `apply_stock_demand`
    refuses a session already in a transaction, so this one test in the file is a
    committing test with a `purge` in `finally` (charter rule 11½).
    """
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _make_goal(db_session, seeded, row)
    workspace_id = seeded.workspace.client_id
    await db_session.commit()
    try:
        await _DR(db_session, seeded, row.client_id)
        await db_session.commit()

        properties = dict(CRITERIA)
        await apply_stock_demand(
            db_session,
            workspace_id=workspace_id,
            entries=[
                DemandEntry(
                    index=0,
                    item_category_raw=seeded.categories[0].name,
                    properties_raw=properties,
                    properties_normalized=normalize_stock_criteria(properties),
                    properties_signature=compute_stock_criteria_signature(properties),
                    quantity_requested=10,
                )
            ],
            now=NOW,
            deadline=time.monotonic() + 60,
            timeout_ms=_TIMEOUT_MS,
        )
        await db_session.commit()

        live = (
            (
                await db_session.execute(
                    select(StockReportItem).where(
                        StockReportItem.workspace_id == workspace_id,
                        StockReportItem.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(live) == 1
        fresh = live[0]
        # A **new** row, not the revived one.
        assert fresh.client_id != row.client_id
        assert fresh.item_category_id == seeded.categories[0].client_id
        assert fresh.properties_signature == compute_stock_criteria_signature(
            properties
        )
        # …with a fresh history: it inherits nothing from R. The delivery writes
        # this row's own first goal record (MC-6: 0 -> 10 is an increase), which is
        # why the cell's literal "empty history" is reported as an owner card
        # rather than asserted as `== []`.
        fresh_history = (
            (
                await db_session.execute(
                    select(StockReportHistoryRecord)
                    .where(
                        StockReportHistoryRecord.stock_report_item_id
                        == fresh.client_id
                    )
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )
        assert [
            (record.type, record.quantity_requested, record.is_deleted)
            for record in fresh_history
        ] == [
            (StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE, 10, False)
        ]
        old_history = (
            (
                await db_session.execute(
                    select(StockReportHistoryRecord).where(
                        StockReportHistoryRecord.stock_report_item_id == row.client_id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert old_history and all(record.is_deleted for record in old_history)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()
