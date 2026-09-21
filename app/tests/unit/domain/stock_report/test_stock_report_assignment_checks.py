from types import SimpleNamespace

from beyo_manager.domain.stock_report.assignment_checks import (
    evaluate_assignment_checks,
    first_failed_check,
)
from beyo_manager.domain.stock_report.enums import StockAssignmentCheckResultEnum as R
from beyo_manager.domain.tasks.enums import TaskStateEnum


def test_assignment_checks_returns_all_results_in_precedence_order():
    results = evaluate_assignment_checks(
        row=SimpleNamespace(is_deleted=False, item_category_id="category-1"),
        task=SimpleNamespace(is_deleted=False, state=TaskStateEnum.FAILED),
        item=SimpleNamespace(is_deleted=False, item_category_id="category-2"),
        task_id="task-1",
        item_id="item-1",
        primary_pairs=set(),
        processed_pairs=set(),
        active_item_ids={"item-1"},
    )

    assert [result.check for result in results] == [
        "stock_report_item_not_found",
        "task_not_found",
        "item_not_found",
        "item_not_task_primary",
        "already_processed_by_scanner",
        "task_failed_or_cancelled",
        "item_already_assigned",
        "item_has_no_category",
        "category_mismatch",
    ]
    assert [result.result for result in results] == [
        R.PASS,
        R.PASS,
        R.PASS,
        R.FAIL,
        R.PASS,
        R.FAIL,
        R.FAIL,
        R.PASS,
        R.FAIL,
    ]
    assert [result.advisory for result in results].count(True) == 1
    assert results[6].advisory is True
    assert first_failed_check(results) == "item_not_task_primary"
