from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from beyo_manager.domain.items.enums import ItemStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from tests.helpers.stock_report import (
    seed_stock_report_workspace,
    assert_stock_report_clean,
)
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)
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

_NOW = datetime(2026, 9, 26, 12, 0, 0, tzinfo=timezone.utc)


async def _version(db_session, workspace_id):
    version = StockReportSnapshotVersion(
        workspace_id=workspace_id, active_at=_NOW, created_at=_NOW
    )
    db_session.add(version)
    await db_session.flush()
    return version


def _snapshot(version, row, priority, order):
    """A row's active snapshot carrying the position under test (2026-09-26: the
    ordering checks read the snapshot, and name it in `client_id`)."""
    return StockReportItemSnapshot(
        workspace_id=row.workspace_id,
        version_id=version.client_id,
        stock_report_item_id=row.client_id,
        quantity_requested_scanner=row.quantity_requested,
        quantity_missing=0,
        priority=priority,
        priority_order=order,
        active_at=_NOW,
        created_at=_NOW,
    )


async def _snapshotted(db_session, seeded, specs):
    """`[(properties, category_index, priority, priority_order), ...]` -> snapshots."""
    version = await _version(db_session, seeded.workspace.client_id)
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
        snapshot = _snapshot(version, row, priority, order)
        db_session.add(snapshot)
        snapshots.append(snapshot)
    await db_session.flush()
    return snapshots


async def _foreign_task_item(db_session, seeded, suffix):
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


@pytest.mark.parametrize(("priority", "order"), [(StockReportPriorityEnum.HIGH, None), (None, 1)])
async def test_a_half_null_position_is_unstorable_so_nullness_needs_no_check(
    db_session, priority, order
):
    """The row table used to allow `priority` without `priority_order` (and the
    reverse), and `priority_order_nullness` repaired it. On the snapshot table
    `ck_stock_report_item_snapshots_priority_order_pairing` refuses the state at
    write time, so the kind was retired with the move (2026-09-26)."""
    seeded = await seed_stock_report_workspace(db_session)
    with pytest.raises(IntegrityError) as excinfo:
        await _snapshotted(db_session, seeded, [({"half": True}, 0, priority, order)])
    assert "ck_stock_report_item_snapshots_priority_order_pairing" in str(excinfo.value)
    await db_session.rollback()


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
    )
    db_session.add(row)
    await db_session.flush()
    snapshot = _snapshot(
        await _version(db_session, seeded.workspace.client_id),
        row,
        StockReportPriorityEnum.HIGH,
        5,
    )
    db_session.add(snapshot)
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
        "client_id": snapshot.client_id,
        "field": "priority_order",
        "stored": 5,
        "expected": 1,
    }


async def test_order_density_reports_only_the_row_that_needs_renumbering(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    rows = await _snapshotted(
        db_session,
        seeded,
        [
            ({"order": order}, index % 2, StockReportPriorityEnum.HIGH, order)
            for index, order in enumerate((1, 2, 5))
        ],
    )
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

    own_rows = []
    for state, field in (
        (StockTaskAssignmentStateEnum.IN_QUEUE, "quantity_in_queue"),
        (StockTaskAssignmentStateEnum.IN_PROGRESS, "quantity_in_progress"),
        (StockTaskAssignmentStateEnum.AWAITING, "quantity_awaiting"),
    ):
        row = StockReportItem(
            workspace_id=own.workspace.client_id,
            item_category_id=own.categories[0].client_id,
            properties={"scope": field},
            properties_signature=compute_stock_criteria_signature({"scope": field}),
        )
        own_rows.append((row, state))
        db_session.add(row)
    await db_session.flush()

    own_history = StockReportHistoryRecord(
        workspace_id=own.workspace.client_id,
        stock_report_item_id=own_rows[0][0].client_id,
        type=StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
        quantity_awaiting=0,
    )
    db_session.add(own_history)
    await db_session.flush()

    foreign_task_ids = []
    for index, (state, field) in enumerate(
        (
            (StockTaskAssignmentStateEnum.IN_QUEUE, "quantity_in_queue"),
            (StockTaskAssignmentStateEnum.IN_PROGRESS, "quantity_in_progress"),
            (StockTaskAssignmentStateEnum.AWAITING, "quantity_awaiting"),
        )
    ):
        row = StockReportItem(
            workspace_id=foreign.workspace.client_id,
            item_category_id=foreign.categories[0].client_id,
            properties={"foreign_counter": field},
            properties_signature=compute_stock_criteria_signature(
                {"foreign_counter": field}
            ),
            **{field: 5},
        )
        db_session.add(row)
        await db_session.flush()
        task, item = await _foreign_task_item(db_session, foreign, f"counter{index}")
        foreign_task_ids.append(task.client_id)
        db_session.add(
            StockTaskAssignment(
                workspace_id=foreign.workspace.client_id,
                stock_report_item_id=row.client_id,
                task_id=task.client_id,
                item_id=item.client_id,
                quantity=4,
                state=state,
            )
        )
        await db_session.flush()

        cross_task, cross_item = await _foreign_task_item(
            db_session, foreign, f"cross{index}"
        )
        foreign_task_ids.append(cross_task.client_id)
        db_session.add(
            StockTaskAssignment(
                workspace_id=foreign.workspace.client_id,
                stock_report_item_id=own_rows[index][0].client_id,
                task_id=cross_task.client_id,
                item_id=cross_item.client_id,
                quantity=4,
                state=state,
            )
        )
        await db_session.flush()

    signature_row = StockReportItem(
        workspace_id=foreign.workspace.client_id,
        item_category_id=foreign.categories[0].client_id,
        properties={"wood_group": ["Teak"]},
        properties_signature="stale",
    )
    db_session.add(signature_row)
    await db_session.flush()

    # Foreign ordering drift lives on the foreign workspace's snapshots (density
    # only: a half-null position is unstorable since 2026-09-26).
    await _snapshotted(
        db_session,
        foreign,
        [
            ({"foreign_density": 1}, 0, StockReportPriorityEnum.HIGH, 1),
            ({"foreign_density": 3}, 0, StockReportPriorityEnum.HIGH, 3),
        ],
    )

    foreign_goal_row = StockReportItem(
        workspace_id=foreign.workspace.client_id,
        item_category_id=foreign.categories[0].client_id,
        properties={"foreign_goal": True},
        properties_signature=compute_stock_criteria_signature({"foreign_goal": True}),
    )
    db_session.add(foreign_goal_row)
    await db_session.flush()
    foreign_history = StockReportHistoryRecord(
        workspace_id=foreign.workspace.client_id,
        stock_report_item_id=foreign_goal_row.client_id,
        type=StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
        quantity_awaiting=5,
    )
    db_session.add(foreign_history)
    await db_session.flush()
    foreign_goal_task, foreign_goal_item = await _foreign_task_item(
        db_session, foreign, "foreign-goal"
    )
    foreign_task_ids.append(foreign_goal_task.client_id)
    db_session.add(
        StockTaskAssignment(
            workspace_id=foreign.workspace.client_id,
            stock_report_item_id=foreign_goal_row.client_id,
            task_id=foreign_goal_task.client_id,
            item_id=foreign_goal_item.client_id,
            quantity=4,
            state=StockTaskAssignmentStateEnum.RESOLVED_EARLY,
            credited_history_record_id=foreign_history.client_id,
        )
    )
    await db_session.flush()

    cross_goal_task, cross_goal_item = await _foreign_task_item(
        db_session, foreign, "cross-goal"
    )
    foreign_task_ids.append(cross_goal_task.client_id)
    db_session.add(
        StockTaskAssignment(
            workspace_id=foreign.workspace.client_id,
            stock_report_item_id=foreign_goal_row.client_id,
            task_id=cross_goal_task.client_id,
            item_id=cross_goal_item.client_id,
            quantity=4,
            state=StockTaskAssignmentStateEnum.RESOLVED_EARLY,
            credited_history_record_id=own_history.client_id,
        )
    )
    await db_session.flush()

    task_flag_task, task_flag_item = await _foreign_task_item(
        db_session, foreign, "cross-task-flag"
    )
    foreign_task_ids.append(task_flag_task.client_id)
    db_session.add(
        StockTaskAssignment(
            workspace_id=foreign.workspace.client_id,
            stock_report_item_id=foreign_goal_row.client_id,
            task_id=own.task.client_id,
            item_id=task_flag_item.client_id,
            quantity=1,
            state=StockTaskAssignmentStateEnum.RESOLVED_EARLY,
        )
    )
    await db_session.flush()
    for task_id in foreign_task_ids:
        await db_session.execute(
            text(
                "UPDATE tasks SET is_stock_assignment = true "
                "WHERE workspace_id = :workspace_id AND client_id = :task_id"
            ),
            {"workspace_id": foreign.workspace.client_id, "task_id": task_id},
        )
    await db_session.execute(
        text("UPDATE tasks SET is_stock_assignment = true WHERE client_id = :task_id"),
        {"task_id": foreign.task.client_id},
    )
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
