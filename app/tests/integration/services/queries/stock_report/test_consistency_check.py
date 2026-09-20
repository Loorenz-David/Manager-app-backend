import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import text
from beyo_manager.models import Base
from tests.helpers.stock_report import (
    seed_stock_report_workspace,
    assert_stock_report_clean,
)
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.domain.stock_report.enums import (
    StockReportPriorityEnum,
    StockTaskAssignmentStateEnum,
    StockReportHistoryRecordTypeEnum,
)
from beyo_manager.services.queries.stock_report.consistency import (
    compute_stock_report_divergences,
)
from beyo_manager.services.queries.stock_report.get_stock_report_consistency import (
    get_stock_report_consistency,
)
from tests.helpers.stock_report import make_ctx

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def test_clean_seed_has_no_stock_report_divergences(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_counter_and_signature_divergences_are_reported(db_session):
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
    divergences = await compute_stock_report_divergences(
        db_session, seeded.workspace.client_id
    )
    assert divergences == [
        {
            "kind": "counter_in_queue",
            "client_id": row.client_id,
            "field": "quantity_in_queue",
            "stored": 5,
            "expected": 4,
        },
        {
            "kind": "task_flag",
            "client_id": seeded.task.client_id,
            "field": "is_stock_assignment",
            "stored": "false",
            "expected": "true",
        },
    ]


async def test_consistency_service_returns_workspace_timestamp_and_divergences(
    db_session,
):
    seeded = await seed_stock_report_workspace(db_session)
    context = make_ctx(db_session, seeded)
    tables = (
        "stock_report_items",
        "stock_task_assignments",
        "stock_report_history_records",
        "stock_report_repair_records",
        "tasks",
    )

    async def snapshot():
        return {
            table: (
                await db_session.execute(
                    text(f"SELECT * FROM {table} WHERE workspace_id = :workspace_id ORDER BY client_id"),
                    {"workspace_id": seeded.workspace.client_id},
                )
            ).all()
            for table in tables
        }

    before = await snapshot()
    result = await get_stock_report_consistency(context)
    after = await snapshot()
    assert result == {
        "workspace_id": seeded.workspace.client_id,
        "checked_at": context.now.isoformat(),
        "divergences": [],
    }
    assert after == before


async def test_consistency_matches_migrated_worker_schema(db_session):
    connection = await db_session.connection()

    def compare(sync_connection):
        context = MigrationContext.configure(sync_connection, opts={"compare_type": True})
        return compare_metadata(context, Base.metadata)

    diffs = await connection.run_sync(compare)
    owned = {
        "stock_report_items",
        "stock_task_assignments",
        "stock_report_history_records",
        "stock_report_repair_records",
        "tasks",
    }
    assert [diff for diff in diffs if any(table in repr(diff) for table in owned)] == []


async def test_resolved_early_is_terminal_but_still_counts_toward_goal_total(
    db_session,
):
    seeded = await seed_stock_report_workspace(db_session)
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={},
        properties_signature=compute_stock_criteria_signature({}),
    )
    db_session.add(row)
    await db_session.flush()
    history = StockReportHistoryRecord(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        type=StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
        quantity_awaiting=4,
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
            state=StockTaskAssignmentStateEnum.RESOLVED_EARLY,
            credited_history_record_id=history.client_id,
        )
    )
    await db_session.flush()
    divergences = await compute_stock_report_divergences(
        db_session, seeded.workspace.client_id
    )
    assert [(entry["kind"], entry["field"]) for entry in divergences] == [
        ("task_flag", "is_stock_assignment")
    ]


async def test_task_flag_divergence_is_reported_when_assignment_is_missing(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.execute(
        text("UPDATE tasks SET is_stock_assignment = true WHERE client_id = :task_id"),
        {"task_id": seeded.task.client_id},
    )
    assert await compute_stock_report_divergences(
        db_session, seeded.workspace.client_id
    ) == [
        {
            "kind": "task_flag",
            "client_id": seeded.task.client_id,
            "field": "is_stock_assignment",
            "stored": "true",
            "expected": "false",
        }
    ]


async def test_deleted_credited_assignment_still_counts_toward_goal_total(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={},
        properties_signature=compute_stock_criteria_signature({}),
    )
    db_session.add(row)
    await db_session.flush()
    history = StockReportHistoryRecord(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        type=StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
        quantity_awaiting=4,
    )
    db_session.add(history)
    await db_session.flush()
    assignment = StockTaskAssignment(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        task_id=seeded.task.client_id,
        item_id=seeded.item.client_id,
        quantity=4,
        state=StockTaskAssignmentStateEnum.RESOLVED_EARLY,
        credited_history_record_id=history.client_id,
    )
    db_session.add(assignment)
    await db_session.flush()
    await db_session.execute(
        text("UPDATE stock_task_assignments SET is_deleted = true WHERE client_id = :id"),
        {"id": assignment.client_id},
    )
    divergences = await compute_stock_report_divergences(
        db_session, seeded.workspace.client_id
    )
    assert divergences == []


async def test_deleted_active_assignment_does_not_count_toward_row_counter(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={},
        properties_signature=compute_stock_criteria_signature({}),
    )
    db_session.add(row)
    await db_session.flush()
    assignment = StockTaskAssignment(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        task_id=seeded.task.client_id,
        item_id=seeded.item.client_id,
        quantity=4,
        state=StockTaskAssignmentStateEnum.IN_QUEUE,
    )
    db_session.add(assignment)
    await db_session.flush()
    await db_session.execute(
        text("UPDATE stock_task_assignments SET is_deleted = true WHERE client_id = :id"),
        {"id": assignment.client_id},
    )
    assert await compute_stock_report_divergences(
        db_session, seeded.workspace.client_id
    ) == []


async def test_null_priority_order_appends_after_the_group_maximum(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    rows = [
        StockReportItem(
            workspace_id=seeded.workspace.client_id,
            item_category_id=seeded.categories[0].client_id,
            properties={"n": number},
            properties_signature=compute_stock_criteria_signature({"n": number}),
            priority=StockReportPriorityEnum.HIGH,
            priority_order=order,
        )
    for number, order in ((1, 1), (2, 2), (3, None))
    ]
    db_session.add_all(rows)
    await db_session.flush()
    divergences = await compute_stock_report_divergences(
        db_session, seeded.workspace.client_id
    )
    nullness = next(
        divergence
        for divergence in divergences
        if divergence["kind"] == "priority_order_nullness"
    )
    assert nullness == {
        "kind": "priority_order_nullness",
        "client_id": rows[2].client_id,
        "field": "priority_order",
        "stored": None,
        "expected": 3,
    }


async def test_null_priority_order_reports_after_sparse_group_maximum(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    rows = [
        StockReportItem(
            workspace_id=seeded.workspace.client_id,
            item_category_id=seeded.categories[0].client_id,
            properties={"n": number},
            properties_signature=compute_stock_criteria_signature({"n": number}),
            priority=StockReportPriorityEnum.HIGH,
            priority_order=order,
        )
        for number, order in ((1, 1), (2, 7), (3, None))
    ]
    db_session.add_all(rows)
    await db_session.flush()
    nullness = next(
        divergence
        for divergence in await compute_stock_report_divergences(
            db_session, seeded.workspace.client_id
        )
        if divergence["kind"] == "priority_order_nullness"
    )
    assert nullness["expected"] == 8


async def test_null_priority_order_is_reported_when_priority_is_missing(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={"null_priority": True},
        properties_signature=compute_stock_criteria_signature({"null_priority": True}),
        priority=None,
        priority_order=1,
    )
    db_session.add(row)
    await db_session.flush()
    assert await compute_stock_report_divergences(
        db_session, seeded.workspace.client_id
    ) == [
        {
            "kind": "priority_order_nullness",
            "client_id": row.client_id,
            "field": "priority_order",
            "stored": 1,
            "expected": None,
        }
    ]


@pytest.mark.parametrize(
    ("state", "field", "kind"),
    [
        (
            StockTaskAssignmentStateEnum.IN_PROGRESS,
            "quantity_in_progress",
            "counter_in_progress",
        ),
        (
            StockTaskAssignmentStateEnum.AWAITING,
            "quantity_awaiting",
            "counter_awaiting",
        ),
    ],
)
async def test_active_counter_divergence_kinds_are_reported(
    db_session, state, field, kind
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
    divergence = next(
        entry
        for entry in await compute_stock_report_divergences(
            db_session, seeded.workspace.client_id
        )
        if entry["kind"] == kind
    )
    assert divergence == {
        "kind": kind,
        "client_id": row.client_id,
        "field": field,
        "stored": 5,
        "expected": 4,
    }


async def test_goal_signature_and_density_divergences_are_reported(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={"wood_group": ["Teak"]},
        properties_signature="stale",
        priority=StockReportPriorityEnum.HIGH,
        priority_order=5,
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
    divergences = await compute_stock_report_divergences(
        db_session, seeded.workspace.client_id
    )
    assert [entry["kind"] for entry in divergences] == [
        "counter_awaiting",
        "goal_total",
        "order_density",
        "signature",
        "task_flag",
    ]
    found = {entry["kind"]: entry for entry in divergences}
    assert found["goal_total"] == {
        "kind": "goal_total",
        "client_id": history.client_id,
        "field": "quantity_awaiting",
        "stored": 5,
        "expected": 4,
    }
    assert found["signature"] == {
        "kind": "signature",
        "client_id": row.client_id,
        "field": "properties_signature",
        "stored": "stale",
        "expected": compute_stock_criteria_signature(row.properties),
    }
    assert found["order_density"] == {
        "kind": "order_density",
        "client_id": row.client_id,
        "field": "priority_order",
        "stored": 5,
        "expected": 1,
    }


async def test_order_density_reports_only_the_row_that_needs_renumbering(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    rows = [
        StockReportItem(
            workspace_id=seeded.workspace.client_id,
            item_category_id=seeded.categories[index % 2].client_id,
            properties={"order": order},
            properties_signature=compute_stock_criteria_signature({"order": order}),
            priority=StockReportPriorityEnum.HIGH,
            priority_order=order,
        )
        for index, order in enumerate((1, 2, 5))
    ]
    db_session.add_all(rows)
    await db_session.flush()
    density = [
        divergence
        for divergence in await compute_stock_report_divergences(
            db_session, seeded.workspace.client_id
        )
        if divergence["kind"] == "order_density"
    ]
    assert density == [
        {
            "kind": "order_density",
            "client_id": rows[2].client_id,
            "field": "priority_order",
            "stored": 5,
            "expected": 3,
        }
    ]


async def test_consistency_does_not_report_foreign_workspace_drift(db_session):
    own = await seed_stock_report_workspace(db_session, suffix="consistency-own")
    foreign = await seed_stock_report_workspace(
        db_session, suffix="consistency-foreign"
    )
    row = StockReportItem(
        workspace_id=foreign.workspace.client_id,
        item_category_id=foreign.categories[0].client_id,
        properties={},
        properties_signature="stale",
        quantity_in_queue=99,
    )
    db_session.add(row)
    await db_session.flush()
    assert (
        await compute_stock_report_divergences(db_session, own.workspace.client_id)
        == []
    )


async def test_consistency_observes_raw_counter_drift_in_an_identity_mapped_row(
    db_session,
):
    seeded = await seed_stock_report_workspace(db_session)
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={"raw": True},
        properties_signature=compute_stock_criteria_signature({"raw": True}),
    )
    db_session.add(row)
    await db_session.flush()
    await db_session.execute(
        text(
            "UPDATE stock_report_items SET quantity_in_queue = 5 "
            "WHERE client_id = :client_id"
        ),
        {"client_id": row.client_id},
    )
    divergences = await compute_stock_report_divergences(
        db_session, seeded.workspace.client_id
    )
    assert {
        entry["kind"] for entry in divergences if entry["client_id"] == row.client_id
    } == {"counter_in_queue"}
