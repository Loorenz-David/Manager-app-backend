import pytest
from sqlalchemy import select, text
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
    capture_dispatch,
    make_ctx,
    seed_stock_report_workspace,
)
from tests.helpers.statement_listener import count_writes, record_statements

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


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
    result = await repair_stock_report(make_ctx(db_session, seeded))
    assert {entry["kind"] for entry in result["repaired"]} == {
        "counter_in_queue",
        "task_flag",
    }
    records = (
        await db_session.scalars(
            select(StockReportRepairRecord).where(
                StockReportRepairRecord.workspace_id == seeded.workspace.client_id,
                StockReportRepairRecord.target_client_id == seeded.task.client_id,
                StockReportRepairRecord.field == "is_stock_assignment",
            )
        )
    ).all()
    assert [(record.stored_value, record.recomputed_value) for record in records] == [
        ("false", "true")
    ]
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
    result = await repair_stock_report(make_ctx(db_session, seeded))
    assert [entry["kind"] for entry in result["repaired"]] == ["task_flag"]
    assert (
        await db_session.scalar(
            text("SELECT is_stock_assignment FROM tasks WHERE client_id = :task_id"),
            {"task_id": seeded.task.client_id},
        )
        is False
    )


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


async def test_repair_applies_nullness_before_priority_density(db_session):
    seeded = await seed_stock_report_workspace(db_session)

    def row(index, order):
        return StockReportItem(
            workspace_id=seeded.workspace.client_id,
            item_category_id=seeded.categories[0].client_id,
            properties={"index": index},
            properties_signature=compute_stock_criteria_signature({"index": index}),
            priority=StockReportPriorityEnum.HIGH,
            priority_order=order,
        )

    first, third, missing = row(1, 1), row(2, 3), row(3, None)
    db_session.add_all([first, third, missing])
    await db_session.flush()
    await repair_stock_report(make_ctx(db_session, seeded))
    await db_session.refresh(first)
    await db_session.refresh(third)
    await db_session.refresh(missing)
    assert (first.priority_order, third.priority_order, missing.priority_order) == (
        1,
        2,
        3,
    )
    assert (
        await compute_stock_report_divergences(db_session, seeded.workspace.client_id)
        == []
    )


async def test_repair_records_one_net_change_per_priority_order_field(db_session):
    seeded = await seed_stock_report_workspace(db_session)

    def row(index, order):
        return StockReportItem(
            workspace_id=seeded.workspace.client_id,
            item_category_id=seeded.categories[0].client_id,
            properties={"index": index},
            properties_signature=compute_stock_criteria_signature({"index": index}),
            priority=StockReportPriorityEnum.HIGH,
            priority_order=order,
        )

    first, gapped, missing = row(1, 1), row(2, 3), row(3, None)
    db_session.add_all([first, gapped, missing])
    await db_session.flush()
    await repair_stock_report(make_ctx(db_session, seeded))
    records = (
        (
            await db_session.execute(
                __import__("sqlalchemy")
                .select(StockReportRepairRecord)
                .where(
                    StockReportRepairRecord.workspace_id == seeded.workspace.client_id,
                    StockReportRepairRecord.field == "priority_order",
                )
            )
        )
        .scalars()
        .all()
    )
    assert {
        (record.target_client_id, record.stored_value, record.recomputed_value)
        for record in records
    } == {
        (gapped.client_id, "3", "2"),
        (missing.client_id, None, "3"),
    }
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
        "priority": None,
        "priority_order": None,
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
