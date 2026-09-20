import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from beyo_manager.domain.items.enums import ItemStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.domain.stock_report.enums import StockTaskAssignmentStateEnum
from beyo_manager.domain.stock_report.enums import StockReportHistoryRecordTypeEnum
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models import Base
from tests.helpers.stock_report import seed_stock_report_workspace

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _extra_task(db_session, seeded, suffix="extra"):
    task = Task(
        client_id=f"tsk_{suffix}_{seeded.workspace.client_id}",
        workspace_id=seeded.workspace.client_id,
        task_scalar_id=2,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=seeded.manager.client_id,
    )
    db_session.add(task)
    await db_session.flush()
    return task


async def _extra_item(db_session, seeded, suffix="extra"):
    item = Item(
        client_id=f"itm_{suffix}_{seeded.workspace.client_id}",
        workspace_id=seeded.workspace.client_id,
        article_number=f"{suffix}-{seeded.workspace.client_id}",
        state=ItemStateEnum.PENDING,
        quantity=1,
        item_category_id=seeded.categories[0].client_id,
    )
    db_session.add(item)
    await db_session.flush()
    return item


async def test_active_row_identity_is_unique_but_soft_deleted_identity_is_reusable(
    db_session,
):
    seeded = await seed_stock_report_workspace(db_session)
    values = dict(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={},
        properties_signature=compute_stock_criteria_signature({}),
    )
    db_session.add(StockReportItem(**values))
    await db_session.flush()
    async with db_session.begin_nested():
        db_session.add(StockReportItem(**values))
        with pytest.raises(
            IntegrityError, match="uix_stock_report_items_identity_active"
        ):
            await db_session.flush()
    db_session.add(StockReportItem(**values, is_deleted=True))
    await db_session.flush()


async def test_terminal_assignment_does_not_block_new_active_assignment(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    other_task = await _extra_task(db_session, seeded)
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={},
        properties_signature=compute_stock_criteria_signature({}),
    )
    db_session.add(row)
    await db_session.flush()
    terminal = StockTaskAssignment(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        task_id=seeded.task.client_id,
        item_id=seeded.item.client_id,
        quantity=1,
        state=StockTaskAssignmentStateEnum.RESOLVED_EARLY,
    )
    db_session.add(terminal)
    await db_session.flush()
    active = StockTaskAssignment(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        task_id=seeded.task.client_id,
        item_id=seeded.item.client_id,
        quantity=1,
        state=StockTaskAssignmentStateEnum.IN_QUEUE,
    )
    db_session.add(active)
    await db_session.flush()
    async with db_session.begin_nested():
        db_session.add(
            StockTaskAssignment(
                workspace_id=seeded.workspace.client_id,
                stock_report_item_id=row.client_id,
                task_id=other_task.client_id,
                item_id=seeded.item.client_id,
                quantity=1,
                state=StockTaskAssignmentStateEnum.IN_PROGRESS,
            )
        )
        with pytest.raises(
            IntegrityError, match="uix_stock_task_assignments_item_active"
        ):
            await db_session.flush()


async def test_active_assignments_on_same_task_and_different_items_hit_task_index(
    db_session,
):
    seeded = await seed_stock_report_workspace(db_session)
    other_item = await _extra_item(db_session, seeded)
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={"task-index": True},
        properties_signature=compute_stock_criteria_signature({"task-index": True}),
    )
    db_session.add(row)
    await db_session.flush()
    db_session.add(
        StockTaskAssignment(
            workspace_id=seeded.workspace.client_id,
            stock_report_item_id=row.client_id,
            task_id=seeded.task.client_id,
            item_id=seeded.item.client_id,
            quantity=1,
            state=StockTaskAssignmentStateEnum.IN_QUEUE,
        )
    )
    await db_session.flush()
    async with db_session.begin_nested():
        db_session.add(
            StockTaskAssignment(
                workspace_id=seeded.workspace.client_id,
                stock_report_item_id=row.client_id,
                task_id=seeded.task.client_id,
                item_id=other_item.client_id,
                quantity=1,
                state=StockTaskAssignmentStateEnum.IN_PROGRESS,
            )
        )
        with pytest.raises(
            IntegrityError, match="uix_stock_task_assignments_task_active"
        ):
            await db_session.flush()


@pytest.mark.parametrize(
    "terminal_state",
    [
        StockTaskAssignmentStateEnum.RESOLVED,
        StockTaskAssignmentStateEnum.FAILED,
        StockTaskAssignmentStateEnum.RESOLVED_EARLY,
    ],
)
async def test_terminal_states_do_not_block_new_active_assignment(
    db_session, terminal_state
):
    seeded = await seed_stock_report_workspace(db_session)
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={"terminal": terminal_state.value},
        properties_signature=compute_stock_criteria_signature(
            {"terminal": terminal_state.value}
        ),
    )
    db_session.add(row)
    await db_session.flush()
    db_session.add(
        StockTaskAssignment(
            workspace_id=seeded.workspace.client_id,
            stock_report_item_id=row.client_id,
            task_id=seeded.task.client_id,
            item_id=seeded.item.client_id,
            quantity=1,
            state=terminal_state,
        )
    )
    await db_session.flush()
    db_session.add(
        StockTaskAssignment(
            workspace_id=seeded.workspace.client_id,
            stock_report_item_id=row.client_id,
            task_id=seeded.task.client_id,
            item_id=seeded.item.client_id,
            quantity=1,
            state=StockTaskAssignmentStateEnum.IN_QUEUE,
        )
    )
    await db_session.flush()


async def test_soft_deleted_active_assignment_does_not_block_new_active_assignment(
    db_session,
):
    seeded = await seed_stock_report_workspace(db_session)
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={"deleted": True},
        properties_signature=compute_stock_criteria_signature({"deleted": True}),
    )
    db_session.add(row)
    await db_session.flush()
    deleted = StockTaskAssignment(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        task_id=seeded.task.client_id,
        item_id=seeded.item.client_id,
        quantity=1,
        state=StockTaskAssignmentStateEnum.IN_QUEUE,
        is_deleted=True,
    )
    db_session.add(deleted)
    await db_session.flush()
    db_session.add(
        StockTaskAssignment(
            workspace_id=seeded.workspace.client_id,
            stock_report_item_id=row.client_id,
            task_id=seeded.task.client_id,
            item_id=seeded.item.client_id,
            quantity=1,
            state=StockTaskAssignmentStateEnum.IN_QUEUE,
        )
    )
    await db_session.flush()


async def test_same_identity_is_reusable_across_workspaces(db_session):
    own = await seed_stock_report_workspace(db_session, suffix="schema-own")
    foreign = await seed_stock_report_workspace(db_session, suffix="schema-foreign")
    for seeded in (own, foreign):
        db_session.add(
            StockReportItem(
                workspace_id=seeded.workspace.client_id,
                item_category_id=seeded.categories[0].client_id,
                properties={"same": True},
                properties_signature=compute_stock_criteria_signature({"same": True}),
            )
        )
    await db_session.flush()


async def test_stock_report_migration_matches_runtime_metadata(db_session):
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


@pytest.mark.parametrize(
    ("field", "value", "constraint"),
    [
        ("quantity_requested", -1, "ck_stock_report_items_quantity_requested_nonneg"),
        ("quantity_in_queue", -1, "ck_stock_report_items_quantity_in_queue_nonneg"),
        (
            "quantity_in_progress",
            -1,
            "ck_stock_report_items_quantity_in_progress_nonneg",
        ),
        ("quantity_awaiting", -1, "ck_stock_report_items_quantity_awaiting_nonneg"),
    ],
)
async def test_stock_report_counter_checks_are_enforced(
    db_session, field, value, constraint
):
    seeded = await seed_stock_report_workspace(db_session)
    values = {
        "workspace_id": seeded.workspace.client_id,
        "item_category_id": seeded.categories[0].client_id,
        "properties": {"field": field},
        "properties_signature": compute_stock_criteria_signature({"field": field}),
        field: value,
    }
    async with db_session.begin_nested():
        db_session.add(StockReportItem(**values))
        with pytest.raises(IntegrityError, match=constraint):
            await db_session.flush()


async def test_assignment_quantity_must_be_positive(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={},
        properties_signature=compute_stock_criteria_signature({}),
    )
    db_session.add(row)
    await db_session.flush()
    async with db_session.begin_nested():
        db_session.add(
            StockTaskAssignment(
                workspace_id=seeded.workspace.client_id,
                stock_report_item_id=row.client_id,
                task_id=seeded.task.client_id,
                item_id=seeded.item.client_id,
                quantity=0,
                state=StockTaskAssignmentStateEnum.IN_QUEUE,
            )
        )
        with pytest.raises(
            IntegrityError, match="ck_stock_task_assignments_quantity_positive"
        ):
            await db_session.flush()


async def test_history_awaiting_quantity_must_be_non_negative(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={},
        properties_signature=compute_stock_criteria_signature({}),
    )
    db_session.add(row)
    await db_session.flush()
    async with db_session.begin_nested():
        db_session.add(
            StockReportHistoryRecord(
                workspace_id=seeded.workspace.client_id,
                stock_report_item_id=row.client_id,
                type=StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
                quantity_awaiting=-1,
            )
        )
        with pytest.raises(
            IntegrityError,
            match="ck_stock_report_history_records_quantity_awaiting_nonneg",
        ):
            await db_session.flush()


async def test_task_stock_assignment_flag_has_a_database_default(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    task_id = "tsk_sr_raw_default"
    await db_session.execute(
        text(
            """
            INSERT INTO tasks
                (workspace_id, task_scalar_id, task_type, priority, state, created_at,
                 is_deleted, recorded_time_marked_wrong, taken_from_average, client_id)
            VALUES (
                :workspace_id, :task_scalar_id, 'internal', 'normal', 'pending',
                CURRENT_TIMESTAMP, false, false, false, :client_id
            )
            """
        ),
        {
            "workspace_id": seeded.workspace.client_id,
            "task_scalar_id": 999,
            "client_id": task_id,
        },
    )
    assert (
        await db_session.scalar(
            text("SELECT is_stock_assignment FROM tasks WHERE client_id = :client_id"),
            {"client_id": task_id},
        )
        is False
    )
