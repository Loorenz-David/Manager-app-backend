from sqlalchemy import delete
from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)


async def delete_stock_report_snapshot_versions(session, workspace_id):
    await session.execute(
        delete(StockReportSnapshotVersion).where(
            StockReportSnapshotVersion.workspace_id == workspace_id
        )
    )
