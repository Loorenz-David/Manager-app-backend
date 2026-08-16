"""Wire builders for the typical-time and budget-allocation read surfaces."""

from __future__ import annotations

from collections.abc import Iterable

from beyo_manager.domain.item_economics.budget_division import ALLOCATION_METHOD


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


__all__ = [
    "serialize_budget_allocation",
    "serialize_budget_allocations",
    "serialize_budget_step",
    "serialize_typical_time",
    "serialize_typical_times",
]
