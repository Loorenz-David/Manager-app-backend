import pytest
from beyo_manager.domain.stock_report.enums import StockTaskAssignmentStateEnum
from beyo_manager.domain.stock_report.state_map import ASSIGNMENT_STATE_BY_TASK_STATE
from beyo_manager.domain.tasks.enums import TaskStateEnum


@pytest.mark.unit
def test_task_state_map_is_total():
    assert set(ASSIGNMENT_STATE_BY_TASK_STATE) == set(TaskStateEnum)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("task_state", "assignment_state"),
    [
        (TaskStateEnum.PENDING, StockTaskAssignmentStateEnum.IN_QUEUE),
        (TaskStateEnum.ASSIGNED, StockTaskAssignmentStateEnum.IN_QUEUE),
        (TaskStateEnum.WORKING, StockTaskAssignmentStateEnum.IN_PROGRESS),
        (TaskStateEnum.STALLED, StockTaskAssignmentStateEnum.IN_PROGRESS),
        (TaskStateEnum.READY, StockTaskAssignmentStateEnum.AWAITING),
        (TaskStateEnum.RESOLVED, StockTaskAssignmentStateEnum.AWAITING),
        (TaskStateEnum.FAILED, StockTaskAssignmentStateEnum.FAILED),
        (TaskStateEnum.CANCELLED, StockTaskAssignmentStateEnum.FAILED),
    ],
)
def test_task_state_map_is_exact(task_state, assignment_state):
    assert ASSIGNMENT_STATE_BY_TASK_STATE[task_state] is assignment_state


@pytest.mark.unit
def test_task_state_map_excludes_scanner_only_terminal_states():
    assert set(ASSIGNMENT_STATE_BY_TASK_STATE.values()) == {
        StockTaskAssignmentStateEnum.IN_QUEUE,
        StockTaskAssignmentStateEnum.IN_PROGRESS,
        StockTaskAssignmentStateEnum.AWAITING,
        StockTaskAssignmentStateEnum.FAILED,
    }
