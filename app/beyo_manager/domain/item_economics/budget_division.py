"""Pure production-budget division rules for the read-only allocation surfaces."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from fractions import Fraction
from typing import Any

from beyo_manager.domain.item_economics.typical_constants import (
    TYPICAL_METHOD,
    TYPICAL_MIN_SAMPLE_SIZE,
    TYPICAL_WINDOW_DAYS,
)
from beyo_manager.domain.item_economics.typical_filters import (
    SelectedTypical,
    apply_business_fallback,
)
from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum


ALLOCATION_METHOD = "static_proportional_section_v2"
EXCLUDED_STEP_STATES = frozenset(
    {
        TaskStepStateEnum.SKIPPED,
        TaskStepStateEnum.CANCELLED,
        TaskStepStateEnum.FAILED,
    }
)


@dataclass(frozen=True)
class DivisionStep:
    """Small input shape used by tests and by the query services."""

    client_id: str
    state: TaskStepStateEnum | str
    working_section_id: str
    total_working_seconds: int = 0
    sequence_order: int | None = None
    working_section_name_snapshot: str | None = None
    is_deleted: bool = False
    created_at: datetime | None = None
    latest_state_record: Any = None


def _value(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
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


def _sort_key(step: Any) -> tuple[bool, int, str]:
    sequence_order = _value(step, "sequence_order")
    client_id = str(_value(step, "client_id", ""))
    return (sequence_order is None, sequence_order if sequence_order is not None else 0, client_id)


def _section_sort_key(section: Any) -> tuple[bool, int, str, str]:
    """M3.2 render order: NULL order values last, then name and id."""

    order_list = _value(section, "order_list")
    return (
        order_list is None,
        order_list if order_list is not None else 0,
        str(_value(section, "name", _value(section, "section_name", "")) or ""),
        str(_value(section, "working_section_id", "")),
    )


def _section_attributes(section_attributes: Mapping[str, Any] | None, section_id: str) -> Any:
    if not section_attributes:
        return None
    return section_attributes.get(section_id)


def _loaded_latest_state_record(step: Any) -> Any:
    if isinstance(step, Mapping):
        return step.get("latest_state_record")
    state = getattr(step, "__dict__", None)
    if isinstance(state, dict) and "latest_state_record" in state:
        return state["latest_state_record"]
    return None


def group_steps_by_section(
    steps: Sequence[Any],
    section_attributes: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Collapse non-deleted steps into the section units used by M3."""

    groups: dict[str, dict[str, Any]] = {}
    for step in steps:
        if bool(_value(step, "is_deleted", False)):
            continue
        section_id = str(_value(step, "working_section_id"))
        group = groups.setdefault(
            section_id,
            {
                "working_section_id": section_id,
                "steps": [],
                "step_ids": [],
                "step_count": 0,
                "worked_seconds": 0,
            },
        )
        group["steps"].append(step)
        group["step_ids"].append(_value(step, "client_id"))
        group["step_count"] += 1
        group["worked_seconds"] += int(_value(step, "total_working_seconds", 0) or 0)

    for section_id, group in groups.items():
        attributes = _section_attributes(section_attributes, section_id)
        if attributes is not None:
            group["section_name"] = _value(attributes, "name", _value(attributes, "section_name"))
            group["order_list"] = _value(attributes, "order_list")
        else:
            first = group["steps"][0]
            if section_attributes is not None:
                group["section_name"] = None
                group["order_list"] = None
            else:
                group["section_name"] = _value(first, "section_name")
                if group["section_name"] is None:
                    group["section_name"] = _value(first, "working_section_name_snapshot")
                group["order_list"] = _value(first, "order_list")
        governing = _governing_step(group["steps"])
        group["state"] = _state_value(_value(governing, "state"))
        entered_at = _value(_loaded_latest_state_record(governing), "entered_at")
        group["state_entered_at"] = entered_at
        group["section_name_snapshot"] = _value(governing, "working_section_name_snapshot")
        if group["section_name_snapshot"] is None:
            group["section_name_snapshot"] = next(
                (
                    _value(step, "working_section_name_snapshot")
                    for step in group["steps"]
                    if _value(step, "working_section_name_snapshot") is not None
                ),
                None,
            )
    return list(groups.values())


def _largest_remainder(
    raw_shares: Mapping[str, Fraction],
    tie_key,
    total: int,
) -> dict[str, int]:
    floors = {key: share.numerator // share.denominator for key, share in raw_shares.items()}
    remainders = {key: raw_shares[key] - floors[key] for key in raw_shares}
    remainder_units = total - sum(floors.values())
    ranked = sorted(raw_shares, key=lambda key: (-remainders[key], tie_key(key)))
    allowances = dict(floors)
    for key in ranked[:remainder_units]:
        allowances[key] += 1
    return allowances


def _governing_step(steps: Sequence[Any]) -> Any:
    def time_key(value: Any) -> tuple[bool, str]:
        if value is None:
            return (False, "")
        if hasattr(value, "isoformat"):
            return (True, value.isoformat())
        return (True, str(value))

    live_steps = [step for step in steps if not _step_state_is_terminal(step)]
    candidates = live_steps or list(steps)
    candidates.sort(key=lambda step: str(_value(step, "client_id", "")))
    candidates.sort(
        key=lambda step: time_key(_value(step, "created_at")),
        reverse=True,
    )
    candidates.sort(
        key=lambda step: time_key(_value(_loaded_latest_state_record(step), "entered_at")),
        reverse=True,
    )
    return candidates[0]


def _step_state_is_terminal(step: Any) -> bool:
    return _state_value(_value(step, "state")) in {state.value for state in TERMINAL_STEP_STATES}


def _step_state_is_excluded(step: Any) -> bool:
    return _state_value(_value(step, "state")) in {state.value for state in EXCLUDED_STEP_STATES}


def participating_sections(steps: Sequence[Any]) -> frozenset[str]:
    return frozenset(
        str(_value(step, "working_section_id"))
        for step in steps
        if not bool(_value(step, "is_deleted", False)) and not _step_state_is_excluded(step)
    )


def _step_state_is_open(step: Any) -> bool:
    return _state_value(_value(step, "state")) not in {state.value for state in TERMINAL_STEP_STATES}


def _section_step_allowances(group: Mapping[str, Any], section_allowance: int) -> dict[str, int]:
    steps = list(group["steps"])
    allocatable = [step for step in steps if not _step_state_is_excluded(step)]
    completed = [
        step
        for step in allocatable
        if _state_value(_value(step, "state")) == TaskStepStateEnum.COMPLETED.value
    ]
    open_steps = [step for step in allocatable if _step_state_is_open(step)]
    allowances = {
        str(_value(step, "client_id")): int(_value(step, "total_working_seconds", 0) or 0)
        for step in completed
    }
    residual = section_allowance - sum(allowances.values())
    if open_steps:
        raw = {
            str(_value(step, "client_id")): Fraction(residual, len(open_steps))
            for step in open_steps
        }
        allowances.update(
            _largest_remainder(
                raw,
                lambda client_id: _sort_key(
                    next(step for step in open_steps if str(_value(step, "client_id")) == client_id)
                ),
                residual,
            )
        )
    else:
        governing = _governing_step(completed)
        governing_id = str(_value(governing, "client_id"))
        allowances[governing_id] += residual
    return allowances


def _step_result(
    step: Any,
    allowance: int | None,
    left: int | None,
    share_state: str,
    typicals: Mapping[str, SelectedTypical],
) -> dict[str, Any]:
    section_id = _value(step, "working_section_id")
    selected = typicals.get(section_id)
    if selected is None:
        typical_worker_seconds = None
        typical_basis = "insufficient_sample"
        sample_count = 0
    else:
        typical_worker_seconds = selected.typical_worker_seconds
        typical_basis = selected.typical_basis
        sample_count = selected.sample_count
    return {
        "step_id": _value(step, "client_id"),
        "working_section_id": section_id,
        "section_name_snapshot": _value(step, "working_section_name_snapshot"),
        "typical_worker_seconds": typical_worker_seconds,
        "typical_basis": typical_basis,
        "sample_count": sample_count,
        "allowance_seconds": allowance,
        "worked_seconds": int(_value(step, "total_working_seconds", 0) or 0),
        "left_seconds": left,
        "share_state": share_state,
        "_sort_step": step,
    }


def divide_production_budget(
    allowed_worker_minutes: Decimal | int | str | None,
    steps: Sequence[Any],
    typicals_by_section: Mapping[str, SelectedTypical] | None = None,
    section_attributes: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Allocate one budget slice per section and split it back across its steps."""

    live_steps = [step for step in steps if not bool(_value(step, "is_deleted", False))]
    typicals = typicals_by_section or {}
    groups = group_steps_by_section(live_steps, section_attributes)

    if allowed_worker_minutes is None:
        step_rows = [_step_result(step, None, None, "no_budget", typicals) for step in live_steps]
        step_rows.sort(key=lambda row: _sort_key(row["_sort_step"]))
        for row in step_rows:
            row.pop("_sort_step", None)
        sections = [
            {
                **group,
                "allowance_seconds": None,
                "left_seconds": None,
                "share_state": "no_budget",
            }
            for group in sorted(groups, key=_section_sort_key)
        ]
        return {
            "budget_seconds": None,
            "charged_seconds": None,
            "distributable_seconds": None,
            "sections": sections,
            "steps": step_rows,
        }

    budget_seconds = _budget_seconds(allowed_worker_minutes)
    excluded = [step for step in live_steps if _step_state_is_excluded(step)]
    participating = participating_sections(live_steps)
    allocated_groups = [group for group in groups if group["working_section_id"] in participating]
    charged_seconds = sum(int(_value(step, "total_working_seconds", 0) or 0) for step in excluded)
    distributable_seconds = max(0, budget_seconds - charged_seconds)

    resolved_weights: dict[str, Fraction] = {}
    selected_values = []
    for group in allocated_groups:
        selected = typicals.get(group["working_section_id"])
        if isinstance(selected, SelectedTypical):
            selected_values.append(selected.typical_worker_seconds)
        else:
            selected_values.append(selected)
    resolved_values = apply_business_fallback(selected_values, terminal=Fraction(1, 1))
    for group, resolved in zip(allocated_groups, resolved_values):
        section_id = group["working_section_id"]
        resolved_weights[section_id] = resolved

    total_weight = sum(resolved_weights.values(), Fraction(0, 1))
    raw_shares = {
        group["working_section_id"]: Fraction(distributable_seconds, 1)
        * resolved_weights[group["working_section_id"]]
        / total_weight
        for group in allocated_groups
    }
    section_allowances = _largest_remainder(raw_shares, lambda section_id: section_id, distributable_seconds)

    section_rows: list[dict[str, Any]] = []
    step_rows: list[dict[str, Any]] = []
    for group in groups:
        section_id = group["working_section_id"]
        worked = group["worked_seconds"]
        if group not in allocated_groups:
            section_rows.append(
                {
                    **group,
                    "allowance_seconds": None,
                    "left_seconds": None,
                    "share_state": "excluded",
                }
            )
            step_rows.extend(_step_result(step, None, None, "excluded", typicals) for step in group["steps"])
            continue

        allowance = section_allowances[section_id]
        section_state = "over_share" if worked > allowance else "on_track"
        section_rows.append(
            {
                **group,
                "allowance_seconds": allowance,
                "left_seconds": allowance - worked,
                "share_state": section_state,
            }
        )
        split = _section_step_allowances(group, allowance)
        for step in group["steps"]:
            step_id = str(_value(step, "client_id"))
            if _step_state_is_excluded(step):
                step_rows.append(_step_result(step, None, None, "excluded", typicals))
            else:
                step_allowance = split[step_id]
                step_rows.append(
                    _step_result(
                        step,
                        step_allowance,
                        step_allowance - int(_value(step, "total_working_seconds", 0) or 0),
                        section_state,
                        typicals,
                    )
                )

    step_rows.sort(key=lambda row: _sort_key(row["_sort_step"]))
    for row in step_rows:
        row.pop("_sort_step", None)
    return {
        "budget_seconds": budget_seconds,
        "charged_seconds": charged_seconds,
        "distributable_seconds": distributable_seconds,
        "sections": sorted(section_rows, key=_section_sort_key),
        "steps": step_rows,
    }


__all__ = [
    "ALLOCATION_METHOD",
    "EXCLUDED_STEP_STATES",
    "TYPICAL_METHOD",
    "TYPICAL_MIN_SAMPLE_SIZE",
    "TYPICAL_WINDOW_DAYS",
    "DivisionStep",
    "divide_production_budget",
    "group_steps_by_section",
    "participating_sections",
]
