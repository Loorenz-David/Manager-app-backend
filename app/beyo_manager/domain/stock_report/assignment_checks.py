from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping

from beyo_manager.domain.stock_report.enums import (
    StockAssignmentCheckResultEnum,
)
from beyo_manager.domain.tasks.enums import TaskStateEnum


@dataclass(frozen=True)
class AssignmentCheckResult:
    check: str
    result: StockAssignmentCheckResultEnum
    advisory: bool


ADVISORY_CHECKS = frozenset({"item_already_assigned"})
PASS_BY_CONSTRUCTION_CHECKS = frozenset(
    {
        "task_failed_or_cancelled",
        "item_not_task_primary",
        "already_processed_by_scanner",
    }
)

_CHECK_ORDER = (
    "stock_report_item_not_found",
    "task_not_found",
    "item_not_found",
    "item_not_task_primary",
    "already_processed_by_scanner",
    "task_failed_or_cancelled",
    "item_already_assigned",
    "item_has_no_category",
    "category_mismatch",
)
_TASK_FAILED_OR_CANCELLED_STATES = frozenset(
    {TaskStateEnum.FAILED, TaskStateEnum.CANCELLED}
)


def evaluate_assignment_checks(
    *,
    row,
    task,
    item,
    task_id: str | None,
    item_id: str | None,
    primary_pairs,
    processed_pairs,
    active_item_ids,
    assumed: Mapping[str, StockAssignmentCheckResultEnum] | None = None,
) -> list[AssignmentCheckResult]:
    assumed = assumed or {}
    results: list[AssignmentCheckResult] = []

    for check in _CHECK_ORDER:
        advisory = check in ADVISORY_CHECKS
        if check in assumed:
            results.append(AssignmentCheckResult(check, assumed[check], advisory))
            continue

        if check == "stock_report_item_not_found":
            failed = row is None or row.is_deleted
        elif check == "task_not_found":
            failed = task is None or task.is_deleted
        elif check == "item_not_found":
            failed = item is None or item.is_deleted
        elif check == "item_not_task_primary":
            failed = (task_id, item_id) not in primary_pairs
        elif check == "already_processed_by_scanner":
            failed = (task_id, item_id) in processed_pairs
        elif check == "task_failed_or_cancelled":
            failed = task is not None and task.state in _TASK_FAILED_OR_CANCELLED_STATES
        elif check == "item_already_assigned":
            failed = item_id in active_item_ids
        elif check == "item_has_no_category":
            failed = item is not None and item.item_category_id is None
        elif check == "category_mismatch":
            failed = (
                row is not None
                and item is not None
                and item.item_category_id is not None
                and item.item_category_id != row.item_category_id
            )
        else:  # pragma: no cover - _CHECK_ORDER is closed above.
            raise AssertionError(f"Unknown assignment check: {check}")

        results.append(
            AssignmentCheckResult(
                check,
                StockAssignmentCheckResultEnum.FAIL
                if failed
                else StockAssignmentCheckResultEnum.PASS,
                advisory,
            )
        )

    return results


def first_failed_check(results: list[AssignmentCheckResult]) -> str | None:
    for result in results:
        if result.result is StockAssignmentCheckResultEnum.FAIL:
            return result.check
    return None
