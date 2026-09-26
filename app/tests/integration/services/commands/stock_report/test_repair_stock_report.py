from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.domain.stock_report.enums import (
    StockReportHistoryRecordTypeEnum,
    StockReportPriorityEnum,
    StockTaskAssignmentStateEnum,
)
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.stock_report.stock_report_repair_record import (
    StockReportRepairRecord,
)
from beyo_manager.services.commands.stock_report.repair_stock_report import (
    repair_stock_report,
)
from beyo_manager.services.commands.stock_report._locks import lock_stock_report_items
from beyo_manager.services.queries.stock_report.consistency import (
    compute_stock_report_divergences,
)
from tests.helpers.stock_report import (
    assert_stock_report_clean,
    capture_dispatch,
    make_ctx,
    seed_stock_report_workspace,
)
from tests.helpers.statement_listener import count_writes, record_statements

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

_NOW = datetime(2026, 9, 26, 12, 0, 0, tzinfo=timezone.utc)


async def _snapshotted(db_session, seeded, specs):
    """Rows plus their active snapshots inside one version — the fixture shape for
    the ordering repairs since the position moved to the snapshot (2026-09-26).
    `specs` is `[(properties, category_index, priority, priority_order), ...]`;
    returns the snapshots in the same order."""
    version = StockReportSnapshotVersion(
        workspace_id=seeded.workspace.client_id, active_at=_NOW, created_at=_NOW
    )
    db_session.add(version)
    await db_session.flush()
    snapshots = []
    for properties, category_index, priority, order in specs:
        row = StockReportItem(
            workspace_id=seeded.workspace.client_id,
            item_category_id=seeded.categories[category_index].client_id,
            properties=properties,
            properties_signature=compute_stock_criteria_signature(properties),
        )
        db_session.add(row)
        await db_session.flush()
        snapshot = StockReportItemSnapshot(
            workspace_id=seeded.workspace.client_id,
            version_id=version.client_id,
            stock_report_item_id=row.client_id,
            priority=priority,
            priority_order=order,
            active_at=_NOW,
            created_at=_NOW,
        )
        db_session.add(snapshot)
        snapshots.append(snapshot)
    await db_session.flush()
    return snapshots


async def test_manual_repair_fixes_counter_and_task_flag_and_records_each_change(
    db_session,
):
    seeded = await seed_stock_report_workspace(db_session)
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={},
        properties_signature=compute_stock_criteria_signature({}),
        quantity_in_queue=5,
    )

    db_session.add(row)
    await db_session.flush()
    db_session.add(
        StockTaskAssignment(
            workspace_id=seeded.workspace.client_id,
            stock_report_item_id=row.client_id,
            task_id=seeded.task.client_id,
            item_id=seeded.item.client_id,
            quantity=4,
            state=StockTaskAssignmentStateEnum.IN_QUEUE,
        )
    )
    await db_session.flush()
    ctx = make_ctx(db_session, seeded)
    result = await repair_stock_report(ctx)
    assert {entry["kind"] for entry in result["repaired"]} == {
        "counter_in_queue",
        "task_flag",
    }
    records = (
        await db_session.scalars(
            select(StockReportRepairRecord).where(
                StockReportRepairRecord.workspace_id == seeded.workspace.client_id,
            )
        )
    ).all()
    assert {
        (
            record.target_kind.value,
            record.target_client_id,
            record.field,
            record.stored_value,
            record.recomputed_value,
            record.trigger,
            record.created_by_id,
            record.created_at,
        )
        for record in records
    } == {
        (
            "stock_report_item",
            row.client_id,
            "quantity_in_queue",
            "5",
            "4",
            "manual",
            seeded.manager.client_id,
            ctx.now,
        ),
        (
            "task",
            seeded.task.client_id,
            "is_stock_assignment",
            "false",
            "true",
            "manual",
            seeded.manager.client_id,
            ctx.now,
        ),
    }
    assert (
        await compute_stock_report_divergences(db_session, seeded.workspace.client_id)
        == []
    )


async def test_manual_repair_clears_false_positive_task_flag(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.execute(
        text("UPDATE tasks SET is_stock_assignment = true WHERE client_id = :task_id"),
        {"task_id": seeded.task.client_id},
    )
    ctx = make_ctx(db_session, seeded)
    result = await repair_stock_report(ctx)
    assert [entry["kind"] for entry in result["repaired"]] == ["task_flag"]
    assert (
        await db_session.scalar(
            text("SELECT is_stock_assignment FROM tasks WHERE client_id = :task_id"),
            {"task_id": seeded.task.client_id},
        )
        is False
    )
    records = (
        await db_session.scalars(
            select(StockReportRepairRecord).where(
                StockReportRepairRecord.workspace_id == seeded.workspace.client_id,
            )
        )
    ).all()
    assert {
        (
            record.target_kind.value,
            record.target_client_id,
            record.field,
            record.stored_value,
            record.recomputed_value,
            record.trigger,
            record.created_by_id,
            record.created_at,
        )
        for record in records
    } == {
        (
            "task",
            seeded.task.client_id,
            "is_stock_assignment",
            "true",
            "false",
            "manual",
            seeded.manager.client_id,
            ctx.now,
        )
    }
    assert (
        await compute_stock_report_divergences(db_session, seeded.workspace.client_id)
        == []
    )


@pytest.mark.parametrize(
    ("state", "field"),
    [
        (StockTaskAssignmentStateEnum.IN_PROGRESS, "quantity_in_progress"),
        (StockTaskAssignmentStateEnum.AWAITING, "quantity_awaiting"),
    ],
)
async def test_manual_repair_fixes_each_active_counter_and_records_exact_fields(
    db_session, state, field
):
    seeded = await seed_stock_report_workspace(db_session)
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={"state": state.value},
        properties_signature=compute_stock_criteria_signature({"state": state.value}),
        **{field: 5},
    )
    db_session.add(row)
    await db_session.flush()
    db_session.add(
        StockTaskAssignment(
            workspace_id=seeded.workspace.client_id,
            stock_report_item_id=row.client_id,
            task_id=seeded.task.client_id,
            item_id=seeded.item.client_id,
            quantity=4,
            state=state,
        )
    )
    await db_session.flush()
    ctx = make_ctx(db_session, seeded)
    await repair_stock_report(ctx)
    record = (
        await db_session.scalars(
            select(StockReportRepairRecord).where(
                StockReportRepairRecord.target_client_id == row.client_id,
                StockReportRepairRecord.field == field,
            )
        )
    ).one()
    assert (
        record.target_kind.value,
        record.field,
        record.stored_value,
        record.recomputed_value,
        record.trigger,
        record.created_by_id,
        record.created_at,
    ) == (
        "stock_report_item",
        field,
        "5",
        "4",
        "manual",
        seeded.manager.client_id,
        ctx.now,
    )
    assert await compute_stock_report_divergences(
        db_session, seeded.workspace.client_id
    ) == []


async def test_stock_report_row_lock_is_workspace_scoped(db_session):
    own = await seed_stock_report_workspace(db_session, suffix="lock-own")
    foreign = await seed_stock_report_workspace(db_session, suffix="lock-foreign")
    own_row = StockReportItem(
        workspace_id=own.workspace.client_id,
        item_category_id=own.categories[0].client_id,
        properties={},
        properties_signature=compute_stock_criteria_signature({}),
    )
    foreign_row = StockReportItem(
        workspace_id=foreign.workspace.client_id,
        item_category_id=foreign.categories[0].client_id,
        properties={},
        properties_signature=compute_stock_criteria_signature({}),
    )
    db_session.add_all([own_row, foreign_row])
    await db_session.flush()
    locked = await lock_stock_report_items(
        db_session,
        own.workspace.client_id,
        [own_row.client_id, foreign_row.client_id],
    )
    assert set(locked) == {own_row.client_id}


async def test_manual_repair_leaves_signature_divergence_unrepaired(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={"wood_group": ["teak"]},
        properties_signature="stale",
    )
    db_session.add(row)
    await db_session.flush()
    result = await repair_stock_report(make_ctx(db_session, seeded))
    await db_session.refresh(row)
    assert result == {
        "repaired": [],
        "not_repaired": [
            {
                "kind": "signature",
                "client_id": row.client_id,
                "field": "properties_signature",
                "stored": "stale",
                "expected": compute_stock_criteria_signature(row.properties),
            }
        ],
    }
    assert row.properties_signature == "stale"
    records = (
        (
            await db_session.execute(
                __import__("sqlalchemy")
                .select(StockReportRepairRecord)
                .where(
                    StockReportRepairRecord.workspace_id == seeded.workspace.client_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert records == []


async def test_manual_repair_reports_signature_kind_once_for_multiple_rows(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    rows = [
        StockReportItem(
            workspace_id=seeded.workspace.client_id,
            item_category_id=category.client_id,
            properties={"row": index},
            properties_signature="stale",
        )
        for index, category in enumerate(seeded.categories)
    ]
    db_session.add_all(rows)
    await db_session.flush()
    result = await repair_stock_report(make_ctx(db_session, seeded))
    assert result["repaired"] == []
    assert [entry["kind"] for entry in result["not_repaired"]] == [
        "signature",
        "signature",
    ]


async def test_clean_manual_repair_makes_no_stock_writes_or_events(
    db_session, monkeypatch
):
    seeded = await seed_stock_report_workspace(db_session)
    dispatch_calls = []

    async def fake_dispatch(events):
        dispatch_calls.append(events)

    monkeypatch.setattr(
        "beyo_manager.services.commands.stock_report.repair_stock_report.dispatch",
        fake_dispatch,
    )
    async with record_statements(db_session) as statements:
        result = await repair_stock_report(make_ctx(db_session, seeded))
    assert result == {"repaired": [], "not_repaired": []}
    assert (
        count_writes(
            statements,
            {
                "stock_report_items",
                "stock_task_assignments",
                "stock_report_history_records",
                "stock_report_repair_records",
                "tasks",
            },
        )
        == 0
    )
    assert dispatch_calls == []


async def test_repair_records_one_net_change_per_priority_order_field(db_session):
    """`high` = 1, 3, 6: two gaps, and the repair renumbers 3 -> 2 and 6 -> 3 with one
    `group` record each — never an intermediate value. (Nullness has no repair since
    2026-09-26: the pairing check makes a half-null position unstorable.)"""
    seeded = await seed_stock_report_workspace(db_session)
    first, gapped, far = await _snapshotted(
        db_session,
        seeded,
        [
            ({"index": 1}, 0, StockReportPriorityEnum.HIGH, 1),
            ({"index": 2}, 0, StockReportPriorityEnum.HIGH, 3),
            ({"index": 3}, 0, StockReportPriorityEnum.HIGH, 6),
        ],
    )
    await repair_stock_report(make_ctx(db_session, seeded))
    records = (
        (
            await db_session.execute(
                select(StockReportRepairRecord).where(
                    StockReportRepairRecord.workspace_id == seeded.workspace.client_id,
                    StockReportRepairRecord.field == "priority_order",
                )
            )
        )
        .scalars()
        .all()
    )
    assert {
        (
            record.target_kind.value,
            record.target_client_id,
            record.stored_value,
            record.recomputed_value,
        )
        for record in records
    } == {
        ("group", gapped.client_id, "3", "2"),
        ("group", far.client_id, "6", "3"),
    }
    await db_session.refresh(first)
    assert first.priority_order == 1
    assert (
        await compute_stock_report_divergences(db_session, seeded.workspace.client_id)
        == []
    )


async def test_repair_dispatches_only_changed_stock_report_rows(
    db_session, monkeypatch
):
    seeded = await seed_stock_report_workspace(db_session)
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={},
        properties_signature=compute_stock_criteria_signature({}),
        quantity_in_queue=5,
    )
    db_session.add(row)
    await db_session.flush()
    history = StockReportHistoryRecord(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        type=StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
        quantity_awaiting=5,
    )
    db_session.add(history)
    await db_session.flush()
    db_session.add(
        StockTaskAssignment(
            workspace_id=seeded.workspace.client_id,
            stock_report_item_id=row.client_id,
            task_id=seeded.task.client_id,
            item_id=seeded.item.client_id,
            quantity=4,
            state=StockTaskAssignmentStateEnum.IN_QUEUE,
            credited_history_record_id=history.client_id,
        )
    )
    await db_session.flush()
    dispatched = capture_dispatch(
        monkeypatch,
        "beyo_manager.services.commands.stock_report.repair_stock_report.dispatch",
    )
    await repair_stock_report(make_ctx(db_session, seeded))
    assert [(event.event_name, event.client_id) for event in dispatched] == [
        ("stock_report_item:updated", row.client_id)
    ]
    assert dispatched[0].extra == {
        "quantity_requested": 0,
        "quantity_in_queue": 4,
        "quantity_in_progress": 0,
        "quantity_awaiting": 0,
    }


async def test_task_flag_repair_does_not_change_task_stamps(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    original_updated_at = seeded.task.updated_at
    original_updated_by_id = seeded.task.updated_by_id
    await db_session.execute(
        text("UPDATE tasks SET is_stock_assignment = true WHERE client_id = :task_id"),
        {"task_id": seeded.task.client_id},
    )
    await repair_stock_report(make_ctx(db_session, seeded))
    await db_session.refresh(seeded.task)
    assert seeded.task.is_stock_assignment is False
    assert seeded.task.updated_at == original_updated_at
    assert seeded.task.updated_by_id == original_updated_by_id


async def test_counter_repair_stamps_only_the_changed_stock_report_row(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    changed = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={"changed": True},
        properties_signature=compute_stock_criteria_signature({"changed": True}),
        quantity_in_queue=5,
    )
    unchanged = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[1].client_id,
        properties={"unchanged": True},
        properties_signature=compute_stock_criteria_signature({"unchanged": True}),
    )
    db_session.add_all([changed, unchanged])
    await db_session.flush()
    db_session.add(
        StockTaskAssignment(
            workspace_id=seeded.workspace.client_id,
            stock_report_item_id=changed.client_id,
            task_id=seeded.task.client_id,
            item_id=seeded.item.client_id,
            quantity=4,
            state=StockTaskAssignmentStateEnum.IN_QUEUE,
        )
    )
    await db_session.flush()
    ctx = make_ctx(db_session, seeded)
    await repair_stock_report(ctx)
    await db_session.refresh(changed)
    await db_session.refresh(unchanged)
    assert (changed.updated_at, changed.updated_by_id) == (
        ctx.now,
        seeded.manager.client_id,
    )
    assert (unchanged.updated_at, unchanged.updated_by_id) == (None, None)


async def test_density_repair_stamps_only_the_renumbered_row(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    unchanged, moved = await _snapshotted(
        db_session,
        seeded,
        [
            ({"order": 1}, 0, StockReportPriorityEnum.HIGH, 1),
            ({"order": 3}, 1, StockReportPriorityEnum.HIGH, 3),
        ],
    )
    ctx = make_ctx(db_session, seeded)
    await repair_stock_report(ctx)
    await db_session.refresh(unchanged)
    await db_session.refresh(moved)
    assert (moved.priority_order, moved.updated_at, moved.updated_by_id) == (
        2,
        ctx.now,
        seeded.manager.client_id,
    )
    assert (unchanged.priority_order, unchanged.updated_at, unchanged.updated_by_id) == (
        1,
        None,
        None,
    )


async def test_a_half_null_position_is_refused_by_the_snapshot_table(db_session):
    """What `priority_order_nullness` used to repair on the row is now impossible to
    store: the snapshot table pairs the two columns with a check constraint."""
    seeded = await seed_stock_report_workspace(db_session)
    with pytest.raises(IntegrityError) as excinfo:
        await _snapshotted(db_session, seeded, [({"priority": None}, 0, None, 1)])
    assert "ck_stock_report_item_snapshots_priority_order_pairing" in str(excinfo.value)
    await db_session.rollback()


async def test_assert_stock_report_clean_rejects_a_stray_repair_record(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    db_session.add(
        StockReportRepairRecord(
            workspace_id=seeded.workspace.client_id,
            target_kind="stock_report_item",
            target_client_id="sri_missing",
            field="quantity_in_queue",
            stored_value="1",
            recomputed_value="0",
            trigger="manual",
        )
    )
    await db_session.flush()
    with pytest.raises(AssertionError):
        await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_manual_repair_fixes_goal_total_and_writes_history_record(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={"goal": True},
        properties_signature=compute_stock_criteria_signature({"goal": True}),
    )
    db_session.add(row)
    await db_session.flush()
    history = StockReportHistoryRecord(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        type=StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
        quantity_awaiting=5,
    )
    db_session.add(history)
    await db_session.flush()
    db_session.add(
        StockTaskAssignment(
            workspace_id=seeded.workspace.client_id,
            stock_report_item_id=row.client_id,
            task_id=seeded.task.client_id,
            item_id=seeded.item.client_id,
            quantity=4,
            state=StockTaskAssignmentStateEnum.AWAITING,
            credited_history_record_id=history.client_id,
        )
    )
    await db_session.flush()
    await repair_stock_report(make_ctx(db_session, seeded))
    await db_session.refresh(history)
    assert history.quantity_awaiting == 4
    record = (
        await db_session.scalars(
            select(StockReportRepairRecord).where(
                StockReportRepairRecord.target_client_id == history.client_id
            )
        )
    ).one()
    assert (
        record.target_kind.value,
        record.field,
        record.stored_value,
        record.recomputed_value,
    ) == (
        "history_record",
        "quantity_awaiting",
        "5",
        "4",
    )
