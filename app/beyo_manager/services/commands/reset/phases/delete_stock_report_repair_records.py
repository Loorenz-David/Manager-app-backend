from sqlalchemy import delete
from beyo_manager.models.tables.stock_report.stock_report_repair_record import StockReportRepairRecord
async def delete_stock_report_repair_records(session, workspace_id):
    await session.execute(delete(StockReportRepairRecord).where(StockReportRepairRecord.workspace_id == workspace_id))
