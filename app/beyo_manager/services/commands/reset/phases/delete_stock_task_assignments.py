from sqlalchemy import delete
from beyo_manager.models.tables.stock_report.stock_task_assignment import StockTaskAssignment
async def delete_stock_task_assignments(session, workspace_id):
    await session.execute(delete(StockTaskAssignment).where(StockTaskAssignment.workspace_id == workspace_id))
