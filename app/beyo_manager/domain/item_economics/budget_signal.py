"""Pure task budget verdict and overrun calculations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final, Mapping, Sequence

from beyo_manager.domain.item_economics.calculator import calculate_consumed_cost_minor
from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES


NO_CURRENCY: Final[str] = "no_currency"
CURRENCY_VOCABULARY: Final[frozenset[str]] = frozenset(
    currency.value for currency in ItemCurrencyEnum
) | {NO_CURRENCY}

BUDGET_STATE_NO_BUDGET: Final[str] = "no_budget"
BUDGET_STATE_OVER: Final[str] = "over"
BUDGET_STATE_PROJECTED_OVER: Final[str] = "projected_over"
BUDGET_STATE_WITHIN_BUDGET: Final[str] = "within_budget"
BUDGET_STATES: Final[frozenset[str]] = frozenset(
    {
        BUDGET_STATE_NO_BUDGET,
        BUDGET_STATE_OVER,
        BUDGET_STATE_PROJECTED_OVER,
        BUDGET_STATE_WITHIN_BUDGET,
    }
)

PROJECTED_OVER_FLOOR_SECONDS: Final[int] = 60

_TERMINAL_STATE_VALUES: Final[frozenset[str]] = frozenset(
    state.value for state in TERMINAL_STEP_STATES
)


def contributes(section: Mapping[str, object]) -> bool:
    return (
        section["left_seconds"] is not None
        and section["state"] not in _TERMINAL_STATE_VALUES
    )


def remaining_commitment(sections: Sequence[Mapping[str, object]]) -> int:
    return sum(
        max(0, section["left_seconds"]) for section in sections if contributes(section)
    )


def has_work_ahead(sections: Sequence[Mapping[str, object]]) -> bool:
    return any(contributes(section) for section in sections)


@dataclass(frozen=True)
class BudgetSignal:
    budget_state: str
    over_seconds: int
    over_cost_minor: int
    projected_over_seconds: int
    projected_over_cost_minor: int
    allowed_seconds: int
    actual_worked_seconds: int
    cost_per_worker_minute_ten_thousandths: int


NO_BUDGET_SIGNAL: Final[BudgetSignal] = BudgetSignal(
    BUDGET_STATE_NO_BUDGET,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
)


def compute_budget_signal(
    *,
    sections: Sequence[Mapping[str, object]],
    allowed_seconds_raw: int,
    actual_worked_seconds: int,
    cost_per_worker_minute_minor_snapshot: Decimal,
) -> BudgetSignal:
    commitment = remaining_commitment(sections)
    remaining_pot_seconds = allowed_seconds_raw - actual_worked_seconds
    projected_over_seconds = max(0, commitment - remaining_pot_seconds)
    over_seconds = max(
        0,
        actual_worked_seconds - max(0, allowed_seconds_raw),
    )

    if over_seconds > 0:
        budget_state = BUDGET_STATE_OVER
    elif projected_over_seconds >= PROJECTED_OVER_FLOOR_SECONDS and has_work_ahead(
        sections
    ):
        budget_state = BUDGET_STATE_PROJECTED_OVER
    else:
        budget_state = BUDGET_STATE_WITHIN_BUDGET

    over_cost_minor = calculate_consumed_cost_minor(
        over_seconds,
        cost_per_worker_minute_minor_snapshot,
    )
    projected_over_cost_minor = calculate_consumed_cost_minor(
        projected_over_seconds,
        cost_per_worker_minute_minor_snapshot,
    )

    return BudgetSignal(
        budget_state=budget_state,
        over_seconds=over_seconds,
        over_cost_minor=over_cost_minor,
        projected_over_seconds=projected_over_seconds,
        projected_over_cost_minor=projected_over_cost_minor,
        allowed_seconds=max(0, allowed_seconds_raw),
        actual_worked_seconds=actual_worked_seconds,
        cost_per_worker_minute_ten_thousandths=int(
            cost_per_worker_minute_minor_snapshot.scaleb(4)
        ),
    )


__all__ = [
    "BUDGET_STATE_NO_BUDGET",
    "BUDGET_STATE_OVER",
    "BUDGET_STATE_PROJECTED_OVER",
    "BUDGET_STATE_WITHIN_BUDGET",
    "BUDGET_STATES",
    "BudgetSignal",
    "CURRENCY_VOCABULARY",
    "NO_BUDGET_SIGNAL",
    "NO_CURRENCY",
    "PROJECTED_OVER_FLOOR_SECONDS",
    "compute_budget_signal",
    "contributes",
    "has_work_ahead",
    "remaining_commitment",
]
