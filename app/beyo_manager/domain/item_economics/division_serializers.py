"""Wire builders for the typical-time and budget-allocation read surfaces."""

from __future__ import annotations

from collections.abc import Iterable

from beyo_manager.domain.item_economics.budget_division import ALLOCATION_METHOD
from beyo_manager.domain.item_economics.budget_division import (
    TYPICAL_METHOD,
    TYPICAL_MIN_SAMPLE_SIZE,
    TYPICAL_WINDOW_DAYS,
)
from beyo_manager.domain.item_economics.calculator import calculate_percent_consumed
from beyo_manager.domain.item_economics.typical_filters import TaskTypicalSelection, TypicalFilterSpec


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
        "typical_basis": row.get("typical_basis", "insufficient_sample"),
        "sample_count": row.get("sample_count", 0),
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
        "typical_resolution": serialize_typical_resolution(row.get("typical_resolution")),
        "steps": [serialize_budget_step(step) for step in row["steps"]],
    }


def serialize_budget_allocations(rows: Iterable[dict]) -> dict:
    return {"budget_allocations": [serialize_budget_allocation(row) for row in rows]}


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)


def serialize_filter_spec(spec: TypicalFilterSpec | None) -> dict | None:
    if spec is None:
        return None
    payload = {}
    for name in (
        "item_category_ids", "major_categories", "width_cm", "height_cm",
        "depth_cm", "can_have_upholstery", "designers",
    ):
        value = getattr(spec, name)
        if value is None:
            continue
        if isinstance(value, frozenset):
            payload[name] = sorted(_enum_value(item) for item in value)
        elif isinstance(value, tuple):
            payload[name] = list(value)
        else:
            payload[name] = value
    return payload


def serialize_typical_resolution(selection: TaskTypicalSelection | None) -> dict:
    counts = {"item_narrowed": 0, "section_wide": 0, "insufficient_sample": 0}
    if selection is not None:
        for section_id in selection.participating_section_ids:
            basis = selection.selected.get(section_id)
            if basis is not None:
                counts[basis.typical_basis] += 1
        return {
            "task_typical_basis": selection.task_typical_basis,
            "reconciliation_method": selection.reconciliation_method,
            "comparability_profile": selection.comparability_profile,
            "applied_filter": serialize_filter_spec(selection.applied_filter),
            "participating_section_count": len(selection.participating_section_ids),
            "sections_by_basis": counts,
        }
    return {
        "task_typical_basis": "section_wide_uniform",
        "reconciliation_method": "uniform_basis_v1",
        "comparability_profile": "primary_item_category_v1",
        "applied_filter": None,
        "participating_section_count": 0,
        "sections_by_basis": counts,
    }


def _serialize_production_time_final(result: object, percent_consumed: object | None) -> dict:
    """Serialize the frozen result with its frozen percentage and no money."""

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
            "typical_basis": typical.get("typical_basis", "insufficient_sample"),
            "narrowed_sample_count": typical.get("narrowed_sample_count", 0),
            "section_sample_count": typical.get("section_sample_count", 0),
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
    frozen_percent_consumed = None
    if result is not None:
        # The budget-status serializer names this feed site: both freeze the
        # percentage from the stored result so the final block never ticks.
        frozen_percent_consumed = calculate_percent_consumed(
            result.actual_worker_minutes + result.variance_worker_minutes,
            result.actual_worker_minutes,
        )
    return {
        "task_id": row["task_id"],
        "status": _enum_value(status),
        "item_binding": row["item_binding"],
        "allocation_method": ALLOCATION_METHOD,
        "typical_resolution": serialize_typical_resolution(row.get("typical_resolution")),
        "budget": {
            "allowed_worker_minutes": _decimal(row.get("allowed_worker_minutes")),
            "actual_worker_seconds": row.get("actual_worker_seconds"),
            "actual_worker_minutes": _decimal(row.get("actual_worker_minutes")),
            "remaining_worker_minutes": _decimal(row.get("remaining_worker_minutes")),
            "percent_consumed": _decimal(percent_consumed),
        },
        "final": (
            _serialize_production_time_final(result, frozen_percent_consumed)
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
    "serialize_filter_spec",
    "serialize_typical_resolution",
]
