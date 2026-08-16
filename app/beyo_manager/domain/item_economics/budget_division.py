"""Pure production-budget division rules for the read-only allocation surface."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from fractions import Fraction
from typing import Any

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum


TYPICAL_WINDOW_DAYS = 90
TYPICAL_MIN_SAMPLE_SIZE = 5
TYPICAL_METHOD = "median_completed_section_totals"
ALLOCATION_METHOD = "static_proportional_v1"
EXCLUDED_STEP_STATES = frozenset(
    {
        TaskStepStateEnum.SKIPPED,
        TaskStepStateEnum.CANCELLED,
        TaskStepStateEnum.FAILED,
    }
)


@dataclass(frozen=True)
class DivisionStep:
    """Small input shape used by tests and by the query service."""

    client_id: str
    state: TaskStepStateEnum | str
    working_section_id: str
    total_working_seconds: int = 0
    sequence_order: int | None = None
    working_section_name_snapshot: str | None = None
    typical_worker_seconds: int | None = None
    is_deleted: bool = False


def _value(value: Any, name: str, default: Any = None) -> Any:
    return getattr(value, name, default)


def _state_value(value: Any) -> str:
    return getattr(value, "value", value)


def _as_fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, Decimal):
        return Fraction(value)
    if isinstance(value, int):
        return Fraction(value, 1)
    return Fraction(Decimal(str(value)))


def _budget_seconds(allowed_worker_minutes: Decimal | int | str) -> int:
    minutes = allowed_worker_minutes if isinstance(allowed_worker_minutes, Decimal) else Decimal(str(allowed_worker_minutes))
    return int((minutes * Decimal(60)).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))


def _median(values: Sequence[Fraction]) -> Fraction:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _sort_key(step: Any) -> tuple[bool, int, str]:
    sequence_order = _value(step, "sequence_order")
    client_id = str(_value(step, "client_id", ""))
    return (sequence_order is None, sequence_order if sequence_order is not None else 0, client_id)


def divide_production_budget(
    allowed_worker_minutes: Decimal | int | str | None,
    steps: Sequence[Any],
    typicals_by_section: Mapping[str, int | None] | None = None,
) -> dict[str, Any]:
    """Divide a task's budget across its current, non-deleted steps.

    The function deliberately accepts ORM instances as well as ``DivisionStep``
    instances. It performs no I/O and returns wire-ready field names without
    calculating any monetary value.
    """
    live_steps = [step for step in steps if not bool(_value(step, "is_deleted", False))]
    typicals = typicals_by_section or {}

    if allowed_worker_minutes is None:
        rows = [_step_result(step, None, None, "no_budget", typicals) for step in live_steps]
        for row in rows:
            row.pop("_sort_step", None)
        return {
            "budget_seconds": None,
            "charged_seconds": None,
            "distributable_seconds": None,
            "steps": rows,
        }

    budget_seconds = _budget_seconds(allowed_worker_minutes)
    excluded = [
        step
        for step in live_steps
        if _state_value(_value(step, "state")) in {state.value for state in EXCLUDED_STEP_STATES}
    ]
    allocated = [step for step in live_steps if step not in excluded]
    charged_seconds = sum(int(_value(step, "total_working_seconds", 0) or 0) for step in excluded)
    distributable_seconds = max(0, budget_seconds - charged_seconds)

    if not allocated:
        rows = [
            _step_result(
                step,
                None,
                None,
                "excluded",
                typicals,
            )
            for step in excluded
        ]
        for row in rows:
            row.pop("_sort_step", None)
        return {
            "budget_seconds": budget_seconds,
            "charged_seconds": charged_seconds,
            "distributable_seconds": distributable_seconds,
            "steps": rows,
        }

    resolved_weights: dict[str, Fraction] = {}
    usable: list[Fraction] = []
    for step in allocated:
        section_id = _value(step, "working_section_id")
        typical = typicals.get(section_id, _value(step, "typical_worker_seconds"))
        if typical is not None and _as_fraction(typical) > 0:
            usable.append(_as_fraction(typical))
    fallback = _median(usable) if usable else Fraction(1, 1)
    for step in allocated:
        section_id = _value(step, "working_section_id")
        typical = typicals.get(section_id, _value(step, "typical_worker_seconds"))
        resolved_weights[str(_value(step, "client_id"))] = (
            _as_fraction(typical) if typical is not None and _as_fraction(typical) > 0 else fallback
        )

    total_weight = sum(resolved_weights.values(), Fraction(0, 1))
    raw_shares = {
        str(_value(step, "client_id")): Fraction(distributable_seconds, 1)
        * resolved_weights[str(_value(step, "client_id"))]
        / total_weight
        for step in allocated
    }
    floors = {client_id: share.numerator // share.denominator for client_id, share in raw_shares.items()}
    remainders = {
        client_id: raw_shares[client_id] - floors[client_id]
        for client_id in raw_shares
    }
    remainder_units = distributable_seconds - sum(floors.values())
    by_id = {str(_value(step, "client_id")): step for step in allocated}
    ranked = sorted(
        raw_shares,
        key=lambda client_id: (
            -remainders[client_id],
            *_sort_key(by_id[client_id]),
        ),
    )
    allowances = dict(floors)
    for client_id in ranked[:remainder_units]:
        allowances[client_id] += 1

    rows = []
    for step in allocated:
        client_id = str(_value(step, "client_id"))
        allowance = allowances[client_id]
        worked = int(_value(step, "total_working_seconds", 0) or 0)
        rows.append(_step_result(step, allowance, allowance - worked, "on_track" if worked <= allowance else "over_share", typicals))
    rows.extend(
        _step_result(step, None, None, "excluded", typicals)
        for step in excluded
    )
    rows.sort(key=lambda row: _sort_key(row["_sort_step"]))
    for row in rows:
        row.pop("_sort_step", None)
    return {
        "budget_seconds": budget_seconds,
        "charged_seconds": charged_seconds,
        "distributable_seconds": distributable_seconds,
        "steps": rows,
    }


def _step_result(
    step: Any,
    allowance: int | None,
    left: int | None,
    share_state: str,
    typicals: Mapping[str, int | None],
) -> dict[str, Any]:
    section_id = _value(step, "working_section_id")
    return {
        "step_id": _value(step, "client_id"),
        "working_section_id": section_id,
        "section_name_snapshot": _value(step, "working_section_name_snapshot"),
        "typical_worker_seconds": typicals.get(section_id, _value(step, "typical_worker_seconds")),
        "allowance_seconds": allowance,
        "worked_seconds": int(_value(step, "total_working_seconds", 0) or 0),
        "left_seconds": left,
        "share_state": share_state,
        "_sort_step": step,
    }


__all__ = [
    "ALLOCATION_METHOD",
    "EXCLUDED_STEP_STATES",
    "TYPICAL_METHOD",
    "TYPICAL_MIN_SAMPLE_SIZE",
    "TYPICAL_WINDOW_DAYS",
    "DivisionStep",
    "divide_production_budget",
]
