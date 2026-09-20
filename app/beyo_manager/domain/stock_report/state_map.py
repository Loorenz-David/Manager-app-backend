from beyo_manager.domain.stock_report.enums import StockTaskAssignmentStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum

ASSIGNMENT_STATE_BY_TASK_STATE = {
    TaskStateEnum.PENDING: StockTaskAssignmentStateEnum.IN_QUEUE,
    TaskStateEnum.ASSIGNED: StockTaskAssignmentStateEnum.IN_QUEUE,
    TaskStateEnum.WORKING: StockTaskAssignmentStateEnum.IN_PROGRESS,
    TaskStateEnum.STALLED: StockTaskAssignmentStateEnum.IN_PROGRESS,
    TaskStateEnum.READY: StockTaskAssignmentStateEnum.AWAITING,
    TaskStateEnum.RESOLVED: StockTaskAssignmentStateEnum.AWAITING,
    TaskStateEnum.FAILED: StockTaskAssignmentStateEnum.FAILED,
    TaskStateEnum.CANCELLED: StockTaskAssignmentStateEnum.FAILED,
}
