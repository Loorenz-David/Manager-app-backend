from sqlalchemy import delete
from beyo_manager.models.tables.stock_report.stock_report_history_record import StockReportHistoryRecord
async def delete_stock_report_history_records(session, workspace_id):
    await session.execute(delete(StockReportHistoryRecord).where(StockReportHistoryRecord.workspace_id == workspace_id))
