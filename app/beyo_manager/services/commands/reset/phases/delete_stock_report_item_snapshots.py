from sqlalchemy import delete
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)


async def delete_stock_report_item_snapshots(session, workspace_id):
    await session.execute(
        delete(StockReportItemSnapshot).where(
            StockReportItemSnapshot.workspace_id == workspace_id
        )
    )
