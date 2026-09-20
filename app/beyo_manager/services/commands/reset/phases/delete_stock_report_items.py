from sqlalchemy import delete
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
async def delete_stock_report_items(session, workspace_id):
    await session.execute(delete(StockReportItem).where(StockReportItem.workspace_id == workspace_id))
