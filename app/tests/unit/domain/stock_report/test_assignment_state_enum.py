import pytest
from beyo_manager.domain.stock_report.enums import (
    ACTIVE_ASSIGNMENT_STATES,
    TERMINAL_ASSIGNMENT_STATES,
    StockTaskAssignmentStateEnum,
)


@pytest.mark.unit
def test_assignment_state_partition_includes_resolved_early_as_terminal():
    assert ACTIVE_ASSIGNMENT_STATES | TERMINAL_ASSIGNMENT_STATES == set(
        StockTaskAssignmentStateEnum
    )
    assert not ACTIVE_ASSIGNMENT_STATES & TERMINAL_ASSIGNMENT_STATES
    assert StockTaskAssignmentStateEnum.RESOLVED_EARLY in TERMINAL_ASSIGNMENT_STATES
