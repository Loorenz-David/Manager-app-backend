"""Wire builders for the typical-time and budget-allocation read surfaces."""

from __future__ import annotations

from collections.abc import Iterable

from beyo_manager.domain.item_economics.budget_division import ALLOCATION_METHOD
from beyo_manager.domain.item_economics.budget_division import (
    TYPICAL_METHOD,
    TYPICAL_MIN_SAMPLE_SIZE,
    TYPICAL_WINDOW_DAYS,
)


def _decimal(value: object) -> str | None:
    return str(value) if value is not None else None


def serialize_typical_time(row: dict) -> dict:
    return {
        "working_section_id": row["working_section_id"],
        "section_name": row["section_name"],
        "typical_worker_seconds": row["typical_worker_seconds"],
        "sample_count": row["sample_count"],
        "method": row["method"],
        "window_days": row["window_days"],
        "min_sample_size": row["min_sample_size"],
    }


def serialize_typical_times(rows: Iterable[dict]) -> dict:
    return {"typical_times": [serialize_typical_time(row) for row in rows]}


def serialize_budget_step(row: dict) -> dict:
    return {
        "step_id": row["step_id"],
        "working_section_id": row["working_section_id"],
        "section_name_snapshot": row["section_name_snapshot"],
        "typical_worker_seconds": row["typical_worker_seconds"],
        "allowance_seconds": row["allowance_seconds"],
        "worked_seconds": row["worked_seconds"],
        "left_seconds": row["left_seconds"],
        "share_state": row["share_state"],
    }


def serialize_budget_allocation(row: dict) -> dict:
    return {
        "task_id": row["task_id"],
        "status": row["status"],
        "allowed_worker_minutes": _decimal(row["allowed_worker_minutes"]),
        "actual_worker_seconds": row["actual_worker_seconds"],
        "remaining_worker_minutes": _decimal(row["remaining_worker_minutes"]),
        "allocation_method": row.get("allocation_method", ALLOCATION_METHOD),
        "steps": [serialize_budget_step(step) for step in row["steps"]],
    }


def serialize_budget_allocations(rows: Iterable[dict]) -> dict:
    return {"budget_allocations": [serialize_budget_allocation(row) for row in rows]}


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)


def _serialize_production_time_final(result: object, percent_consumed: object | None) -> dict:
    """Serialize the frozen result with the live percentage and no money."""

    return {
        "actual_worker_minutes": _decimal(result.actual_worker_minutes),
        "variance_worker_minutes": _decimal(result.variance_worker_minutes),
        "percent_consumed": _decimal(percent_consumed),
        "task_state_snapshot": _enum_value(result.task_state_snapshot),
        "computed_at": result.computed_at.isoformat(),
    }


def serialize_production_time_section(row: dict, typical: dict | None = None) -> dict:
    typical = typical or {
        "typical_worker_seconds": None,
        "sample_count": 0,
        "method": TYPICAL_METHOD,
        "window_days": TYPICAL_WINDOW_DAYS,
        "min_sample_size": TYPICAL_MIN_SAMPLE_SIZE,
    }
    entered_at = row.get("state_entered_at")
    return {
        "working_section_id": row["working_section_id"],
        "section_name": row.get("section_name"),
        "section_name_snapshot": row.get("section_name_snapshot"),
        "order_list": row.get("order_list"),
        "state": row.get("state"),
        "state_entered_at": entered_at.isoformat() if hasattr(entered_at, "isoformat") else entered_at,
        "worked_seconds": row["worked_seconds"],
        "step_count": row["step_count"],
        "allowance_seconds": row.get("allowance_seconds"),
        "left_seconds": row.get("left_seconds"),
        "share_state": row["share_state"],
        "typical": {
            "typical_worker_seconds": typical.get("typical_worker_seconds"),
            "sample_count": typical.get("sample_count", 0),
            "method": typical.get("method", TYPICAL_METHOD),
            "window_days": typical.get("window_days", TYPICAL_WINDOW_DAYS),
            "min_sample_size": typical.get("min_sample_size", TYPICAL_MIN_SAMPLE_SIZE),
        },
    }


def serialize_task_production_time(row: dict) -> dict:
    status = row["status"]
    percent_consumed = row.get("percent_consumed")
    result = row.get("result")
    division = row["division"]
    return {
        "task_id": row["task_id"],
        "status": _enum_value(status),
        "item_binding": row["item_binding"],
        "allocation_method": ALLOCATION_METHOD,
        "budget": {
            "allowed_worker_minutes": _decimal(row.get("allowed_worker_minutes")),
            "actual_worker_seconds": row.get("actual_worker_seconds"),
            "actual_worker_minutes": _decimal(row.get("actual_worker_minutes")),
            "remaining_worker_minutes": _decimal(row.get("remaining_worker_minutes")),
            "percent_consumed": _decimal(percent_consumed),
        },
        "final": (
            _serialize_production_time_final(result, percent_consumed)
            if result is not None
            else None
        ),
        "sections": [
            serialize_production_time_section(
                section,
                row.get("typicals", {}).get(section["working_section_id"]),
            )
            for section in division["sections"]
        ],
    }


__all__ = [
    "serialize_budget_allocation",
    "serialize_budget_allocations",
    "serialize_budget_step",
    "serialize_typical_time",
    "serialize_typical_times",
    "serialize_production_time_section",
    "serialize_task_production_time",
]
