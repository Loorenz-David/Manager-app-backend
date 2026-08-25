"""Pure remaining-production-pressure calculation for budget division output."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from typing import Final

from beyo_manager.domain.item_economics.budget_division import (
    _largest_remainder,
)
from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES


PRESSURE_METHOD: Final[str] = "open_share_proportional_v1"
_TERMINAL_STATE_VALUES: Final[frozenset[str]] = frozenset(
    state.value for state in TERMINAL_STEP_STATES
)


@dataclass(frozen=True)
class PressureResult:
    """Pressure values derived from one unchanged budget-division result."""

    pressure_ratio: Fraction | None
    pressure_share_seconds_by_step_id: dict[str, int | None]


def _is_excluded(step: Mapping[str, object]) -> bool:
    return step["share_state"] == "excluded"


def _is_open(step: Mapping[str, object]) -> bool:
    return step["state"] not in _TERMINAL_STATE_VALUES


def _is_consuming(step: Mapping[str, object]) -> bool:
    return (
        _is_open(step)
        and step["left_seconds"] is not None
        and int(step["left_seconds"]) < 0
    )


def compute_remaining_pressure(division: Mapping[str, object]) -> PressureResult:
    """Allocate the distributable budget left after settled and consuming steps.

    The allocation is intentionally based only on the allocator's existing step rows.
    Work on an allocatable step therefore leaves its own pressure target unchanged
    until it crosses its served allowance and becomes consuming.
    """

    steps = tuple(division["steps"])
    no_pressure = {str(step["step_id"]): None for step in steps}
    distributable_seconds = division["distributable_seconds"]
    if distributable_seconds is None:
        return PressureResult(None, no_pressure)

    participating = [step for step in steps if not _is_excluded(step)]
    open_steps = [step for step in participating if _is_open(step)]
    consuming = [step for step in open_steps if _is_consuming(step)]
    allocatable = [step for step in open_steps if not _is_consuming(step)]
    shares = dict(no_pressure)
    for step in consuming:
        shares[str(step["step_id"])] = 0

    if not allocatable:
        return PressureResult(None, shares)

    charged = [step for step in participating if not _is_open(step)] + consuming
    remaining_distributable = int(distributable_seconds) - sum(
        int(step["worked_seconds"]) for step in charged
    )
    total_open_allowance = sum(
        max(0, int(step["allowance_seconds"])) for step in allocatable
    )
    if total_open_allowance == 0:
        for step in allocatable:
            shares[str(step["step_id"])] = 0
        return PressureResult(None, shares)

    ratio = Fraction(remaining_distributable, total_open_allowance)
    if remaining_distributable <= 0:
        for step in allocatable:
            shares[str(step["step_id"])] = 0
        return PressureResult(ratio, shares)

    raw_shares = {
        str(step["step_id"]): Fraction(int(step["allowance_seconds"])) * ratio
        for step in allocatable
    }
    allocation_order = {str(step["step_id"]): index for index, step in enumerate(steps)}
    shares.update(
        _largest_remainder(
            raw_shares, allocation_order.__getitem__, remaining_distributable
        )
    )
    return PressureResult(ratio, shares)


__all__ = ["PRESSURE_METHOD", "PressureResult", "compute_remaining_pressure"]
