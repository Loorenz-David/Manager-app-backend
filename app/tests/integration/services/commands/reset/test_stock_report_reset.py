import pytest
from sqlalchemy import func, select

from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.domain.stock_report.enums import (
    StockReportHistoryRecordTypeEnum,
    StockReportRepairTargetKindEnum,
    StockTaskAssignmentStateEnum,
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
from beyo_manager.services.commands.reset.reset_app import reset_app
from tests.helpers.stock_report import (
    capture_dispatch,
    make_ctx,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)
from beyo_manager.models.tables.workspaces.workspace import Workspace

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _seed_report_graph(session, seeded):
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties={},
        properties_signature=compute_stock_criteria_signature({}),
    )
    session.add(row)
    await session.flush()
    history = StockReportHistoryRecord(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        type=StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
    )
    session.add(history)
    await session.flush()
    session.add_all(
        [
            StockTaskAssignment(
                workspace_id=seeded.workspace.client_id,
                stock_report_item_id=row.client_id,
                task_id=seeded.task.client_id,
                item_id=seeded.item.client_id,
                quantity=4,
                state=StockTaskAssignmentStateEnum.IN_QUEUE,
                credited_history_record_id=history.client_id,
            ),
            StockReportRepairRecord(
                workspace_id=seeded.workspace.client_id,
                target_kind=StockReportRepairTargetKindEnum.STOCK_REPORT_ITEM,
                target_client_id=row.client_id,
                field="quantity_in_queue",
                stored_value="4",
                recomputed_value="0",
                trigger="manual",
            ),
        ]
    )
    await session.flush()


async def _count(session, model, workspace_id):
    return await session.scalar(
        select(func.count())
        .select_from(model)
        .where(model.workspace_id == workspace_id)
    )


async def test_reset_removes_stock_report_graph_before_task_deletion_and_keeps_other_workspace(
    db_session, monkeypatch
):
    own = await seed_stock_report_workspace(db_session, suffix="reset-own")
    foreign = await seed_stock_report_workspace(db_session, suffix="reset-foreign")
    await _seed_report_graph(db_session, own)
    await _seed_report_graph(db_session, foreign)
    own_workspace_id = own.workspace.client_id
    foreign_workspace_id = foreign.workspace.client_id
    ctx = make_ctx(
        db_session, own, incoming_data={"delete_orphan_bootstrap_users": False}
    )
    await db_session.commit()
    dispatched = capture_dispatch(
        monkeypatch, "beyo_manager.services.commands.reset.reset_app.dispatch"
    )
    try:
        await reset_app(ctx)

        for model in (
            StockReportItem,
            StockTaskAssignment,
            StockReportHistoryRecord,
            StockReportRepairRecord,
        ):
            assert await _count(db_session, model, own_workspace_id) == 0
            assert await _count(db_session, model, foreign_workspace_id) == 1
        assert (
            await db_session.scalar(
                select(Workspace.client_id).where(
                    Workspace.client_id == own_workspace_id
                )
            )
            is None
        )
        assert [event.event_name for event in dispatched] == ["workspace:reset"]
    finally:
        await purge_stock_report_workspace(db_session, foreign_workspace_id)
        await db_session.commit()
