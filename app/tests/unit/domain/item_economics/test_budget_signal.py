import enum
import inspect
from dataclasses import FrozenInstanceError
from decimal import Decimal
from pathlib import Path
from typing import get_type_hints

import pytest

from beyo_manager.domain.item_economics import budget_signal
from beyo_manager.domain.item_economics.budget_division import (
    DivisionStep,
    divide_production_budget,
)
from beyo_manager.domain.item_economics.typical_constants import TYPICAL_MIN_SAMPLE_SIZE
from beyo_manager.domain.item_economics.typical_filters import (
    SectionTypicalEvidence,
    SelectedTypical,
)
from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum


RATE = Decimal("3.7500")
EQUAL_TYPICALS = {
    "A": 1800,
    "B": 1800,
}


def selected(section: str, value: int) -> SelectedTypical:
    evidence = SectionTypicalEvidence(
        section,
        None,
        0,
        value,
        TYPICAL_MIN_SAMPLE_SIZE,
    )
    return SelectedTypical(
        section,
        value,
        "section_wide",
        evidence,
        True,
        TYPICAL_MIN_SAMPLE_SIZE,
    )


def step(
    client_id: str,
    state: TaskStepStateEnum | str,
    section: str,
    worked: int,
    sequence_order: int,
) -> DivisionStep:
    return DivisionStep(
        client_id=client_id,
        state=state,
        working_section_id=section,
        total_working_seconds=worked,
        sequence_order=sequence_order,
    )


def rows(
    allowed: str,
    steps: list[DivisionStep],
    typicals: dict[str, SelectedTypical],
) -> dict[str, object]:
    return divide_production_budget(Decimal(allowed), steps, typicals)


def signal_for(
    allowed: str,
    steps: list[DivisionStep],
    typicals: dict[str, SelectedTypical],
    rate: Decimal = RATE,
) -> budget_signal.BudgetSignal:
    division = rows(allowed, steps, typicals)
    return budget_signal.compute_budget_signal(
        sections=division["sections"],
        allowed_seconds_raw=division["budget_seconds"],
        actual_worked_seconds=sum(step.total_working_seconds for step in steps),
        cost_per_worker_minute_minor_snapshot=rate,
    )


def test_c1a_contributes_partitions_all_step_states():
    expected = {
        TaskStepStateEnum.PENDING: (True, 1700, "on_track"),
        TaskStepStateEnum.WORKING: (True, 1700, "on_track"),
        TaskStepStateEnum.PAUSED: (True, 1700, "on_track"),
        TaskStepStateEnum.BLOCKED: (True, 1700, "on_track"),
        TaskStepStateEnum.COMPLETED: (False, 1700, "on_track"),
        TaskStepStateEnum.SKIPPED: (False, None, "excluded"),
        TaskStepStateEnum.FAILED: (False, None, "excluded"),
        TaskStepStateEnum.CANCELLED: (False, None, "excluded"),
    }
    for state, result in expected.items():
        division = rows(
            "60.00",
            [
                step("x", state, "A", 100, 1),
                step("y", TaskStepStateEnum.PENDING, "B", 0, 2),
            ],
            {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
        )
        section = next(
            item for item in division["sections"] if item["working_section_id"] == "A"
        )
        assert (
            budget_signal.contributes(section),
            section["left_seconds"],
            section["share_state"],
        ) == result


def test_c1b_has_work_ahead_uses_the_contributing_set():
    terminal = {
        TaskStepStateEnum.COMPLETED,
        TaskStepStateEnum.SKIPPED,
        TaskStepStateEnum.FAILED,
        TaskStepStateEnum.CANCELLED,
    }
    for state in TaskStepStateEnum:
        with_peer = rows(
            "60.00",
            [
                step("x", state, "A", 100, 1),
                step("y", TaskStepStateEnum.PENDING, "B", 0, 2),
            ],
            {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
        )
        without_peer = rows(
            "60.00",
            [step("x", state, "A", 100, 1)],
            {"A": selected("A", 1800)},
        )
        assert budget_signal.has_work_ahead(with_peer["sections"]) is True
        assert budget_signal.has_work_ahead(without_peer["sections"]) is (
            state not in terminal
        )


def test_c1c_terminal_values_are_derived_strings():
    assert budget_signal._TERMINAL_STATE_VALUES == frozenset(
        state.value for state in TERMINAL_STEP_STATES
    )
    assert all(type(value) is str for value in budget_signal._TERMINAL_STATE_VALUES)


def test_c1d_module_does_not_spell_step_state_values():
    source = inspect.getsource(budget_signal)
    for state in TaskStepStateEnum:
        assert f'"{state.value}"' not in source
        assert f"'{state.value}'" not in source


def test_c2a_remaining_commitment_clamps_each_section_before_summing():
    division = rows(
        "60.00",
        [
            step("a", TaskStepStateEnum.WORKING, "A", 2400, 1),
            step("b", TaskStepStateEnum.PAUSED, "B", 1200, 2),
        ],
        {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
    )
    assert budget_signal.remaining_commitment(division["sections"]) == 600


def test_c2b_projection_uses_clamped_commitment():
    signal = signal_for(
        "60.00",
        [
            step("a", TaskStepStateEnum.WORKING, "A", 2400, 1),
            step("b", TaskStepStateEnum.PAUSED, "B", 1200, 2),
        ],
        {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
    )
    assert signal.projected_over_seconds == 600
    assert signal.projected_over_cost_minor == 38


def test_c2c_projection_is_signalled_after_the_clamp():
    signal = signal_for(
        "60.00",
        [
            step("a", TaskStepStateEnum.WORKING, "A", 2400, 1),
            step("b", TaskStepStateEnum.PAUSED, "B", 1200, 2),
        ],
        {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
    )
    assert signal.budget_state == "projected_over"


def test_c3a_negative_pot_is_forecast_but_not_incurred():
    signal = signal_for(
        "-12.50",
        [step("a", TaskStepStateEnum.PENDING, "A", 0, 1)],
        {"A": selected("A", 1800)},
    )
    assert (
        signal.over_seconds,
        signal.projected_over_seconds,
        signal.allowed_seconds,
        signal.budget_state,
    ) == (0, 750, 0, "projected_over")
    assert signal.projected_over_cost_minor == 47


def test_c3b_first_logged_seconds_on_negative_pot_are_incurred():
    signal = signal_for(
        "-12.50",
        [
            step("a", TaskStepStateEnum.WORKING, "A", 60, 1),
            step("b", TaskStepStateEnum.PENDING, "B", 0, 2),
        ],
        {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
    )
    assert (
        signal.over_seconds,
        signal.over_cost_minor,
        signal.projected_over_seconds,
        signal.budget_state,
    ) == (60, 4, 810, "over")


def test_c3c_projection_uses_the_task_pot_operand():
    signal = signal_for(
        "60.00",
        [
            step("a1", TaskStepStateEnum.COMPLETED, "A", 1000, 1),
            step("a2", TaskStepStateEnum.SKIPPED, "A", 300, 2),
            step("b", TaskStepStateEnum.WORKING, "B", 500, 3),
        ],
        {"A": selected("A", 1000), "B": selected("B", 2000)},
    )
    assert (signal.projected_over_seconds, signal.budget_state) == (0, "within_budget")


def test_c3d_numeric_signal_fields_are_exact_ints():
    signals = [
        signal_for(
            "-12.50",
            [step("a", TaskStepStateEnum.PENDING, "A", 0, 1)],
            {"A": selected("A", 1800)},
        ),
        signal_for(
            "-12.50",
            [
                step("a", TaskStepStateEnum.WORKING, "A", 60, 1),
                step("b", TaskStepStateEnum.PENDING, "B", 0, 2),
            ],
            {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
        ),
        signal_for(
            "60.00",
            [
                step("a1", TaskStepStateEnum.COMPLETED, "A", 1000, 1),
                step("a2", TaskStepStateEnum.SKIPPED, "A", 300, 2),
                step("b", TaskStepStateEnum.WORKING, "B", 500, 3),
            ],
            {"A": selected("A", 1000), "B": selected("B", 2000)},
        ),
    ]
    for signal in signals:
        for name, value in vars(signal).items():
            if name != "budget_state":
                assert type(value) is int


def test_c4a_projection_below_the_floor_is_served_not_signalled():
    signal = signal_for(
        "60.00",
        [
            step("a", TaskStepStateEnum.COMPLETED, "A", 1859, 1),
            step("b", TaskStepStateEnum.PENDING, "B", 0, 2),
        ],
        {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
    )
    assert (signal.projected_over_seconds, signal.budget_state) == (59, "within_budget")


def test_c4b_projection_at_the_floor_is_signalled():
    signal = signal_for(
        "60.00",
        [
            step("a", TaskStepStateEnum.COMPLETED, "A", 1860, 1),
            step("b", TaskStepStateEnum.PENDING, "B", 0, 2),
        ],
        {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
    )
    assert (signal.projected_over_seconds, signal.budget_state) == (
        60,
        "projected_over",
    )


def test_c4c_infeasible_all_excluded_has_no_forecast():
    division = rows(
        "-12.50",
        [
            step("a", TaskStepStateEnum.SKIPPED, "A", 0, 1),
            step("b", TaskStepStateEnum.SKIPPED, "B", 0, 2),
        ],
        {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
    )
    signal = budget_signal.compute_budget_signal(
        sections=division["sections"],
        allowed_seconds_raw=division["budget_seconds"],
        actual_worked_seconds=0,
        cost_per_worker_minute_minor_snapshot=RATE,
    )
    assert (
        budget_signal.has_work_ahead(division["sections"]),
        budget_signal.remaining_commitment(division["sections"]),
        signal.projected_over_seconds,
        signal.budget_state,
    ) == (False, 0, 750, "within_budget")


def test_c4d_infeasible_without_steps_has_no_forecast():
    division = rows("-12.50", [], {})
    signal = budget_signal.compute_budget_signal(
        sections=division["sections"],
        allowed_seconds_raw=division["budget_seconds"],
        actual_worked_seconds=0,
        cost_per_worker_minute_minor_snapshot=RATE,
    )
    assert (
        budget_signal.has_work_ahead(division["sections"]),
        budget_signal.remaining_commitment(division["sections"]),
        signal.projected_over_seconds,
        signal.budget_state,
    ) == (False, 0, 750, "within_budget")


def test_c4e_excluded_allocator_rows_have_no_commitment_or_work_ahead():
    division = rows(
        "60.00",
        [
            step("a", TaskStepStateEnum.SKIPPED, "A", 600, 1),
            step("b", TaskStepStateEnum.CANCELLED, "B", 300, 2),
        ],
        {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
    )
    assert budget_signal.remaining_commitment(division["sections"]) == 0
    assert budget_signal.has_work_ahead(division["sections"]) is False


@pytest.mark.parametrize(
    ("worked", "expected_cost"),
    [(3736, 9), (3752, 9)],
)
def test_c5ab_money_call_matches_shipped_rounding(worked, expected_cost):
    signal = signal_for(
        "60.00",
        [step("a", TaskStepStateEnum.COMPLETED, "A", worked, 1)],
        {"A": selected("A", 1800)},
    )
    assert (
        signal.over_seconds,
        signal.over_cost_minor,
        signal.projected_over_seconds,
        signal.projected_over_cost_minor,
    ) == (worked - 3600, expected_cost, worked - 3600, expected_cost)


def test_c5c_money_call_is_not_the_two_step_inverse():
    signal = signal_for(
        "60.00",
        [step("a", TaskStepStateEnum.COMPLETED, "A", 3640, 1)],
        {"A": selected("A", 1800)},
    )
    assert (
        signal.over_seconds,
        signal.over_cost_minor,
        signal.projected_over_seconds,
        signal.projected_over_cost_minor,
    ) == (40, 2, 40, 2)


def test_c5d_nonzero_overrun_may_cost_zero():
    for worked, cost in ((3608, 0), (3609, 1)):
        signal = signal_for(
            "60.00",
            [step("a", TaskStepStateEnum.COMPLETED, "A", worked, 1)],
            {"A": selected("A", 1800)},
        )
        assert (signal.over_seconds, signal.over_cost_minor, signal.budget_state) == (
            worked - 3600,
            cost,
            "over",
        )


def test_c5e_incurred_money_never_goes_negative():
    signal = signal_for(
        "60.00",
        [
            step("a", TaskStepStateEnum.WORKING, "A", 600, 1),
            step("b", TaskStepStateEnum.PENDING, "B", 0, 2),
        ],
        {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
    )
    assert signal.over_seconds == 0
    assert signal.over_cost_minor == 0
    assert signal.over_cost_minor >= 0


@pytest.mark.parametrize(
    ("rate", "expected"),
    [
        (Decimal("3.7500"), 37500),
        (Decimal("0.0001"), 1),
        (Decimal("99999999.9999"), 999999999999),
    ],
)
def test_c5f_rate_scaling_is_exact(rate, expected):
    signal = signal_for(
        "60.00",
        [step("a", TaskStepStateEnum.PENDING, "A", 0, 1)],
        {"A": selected("A", 1800)},
        rate,
    )
    assert signal.cost_per_worker_minute_ten_thousandths == expected


def test_c5g_money_calls_receive_ordered_exact_arguments(monkeypatch):
    calls = []
    real_calculator = budget_signal.calculate_consumed_cost_minor

    def recording_calculator(seconds, rate):
        assert type(seconds) is int
        assert seconds >= 0
        assert type(rate) is Decimal
        calls.append((seconds, rate))
        return real_calculator(seconds, rate)

    monkeypatch.setattr(
        budget_signal, "calculate_consumed_cost_minor", recording_calculator
    )
    signal = signal_for(
        "60.00",
        [
            step("a", TaskStepStateEnum.COMPLETED, "A", 3700, 1),
            step("b", TaskStepStateEnum.PENDING, "B", 0, 2),
        ],
        {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
    )
    assert calls == [(100, RATE), (1900, RATE)]
    assert (
        signal.over_seconds,
        signal.over_cost_minor,
        signal.projected_over_seconds,
        signal.projected_over_cost_minor,
        signal.budget_state,
    ) == (100, 6, 1900, 119, "over")


def test_c6a_no_budget_signal_is_the_constructed_zero_row():
    assert budget_signal.NO_BUDGET_SIGNAL.budget_state == "no_budget"
    for name, value in vars(budget_signal.NO_BUDGET_SIGNAL).items():
        if name != "budget_state":
            assert type(value) is int
            assert value == 0


def test_c6b_over_state_keeps_both_pairs():
    signal = signal_for(
        "60.00",
        [
            step("a", TaskStepStateEnum.COMPLETED, "A", 3700, 1),
            step("b", TaskStepStateEnum.PENDING, "B", 0, 2),
        ],
        {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
    )
    assert (
        signal.over_seconds,
        signal.over_cost_minor,
        signal.projected_over_seconds,
        signal.projected_over_cost_minor,
        signal.budget_state,
    ) == (100, 6, 1900, 119, "over")


def test_c6c_over_state_keeps_sub_floor_projection_pair():
    signal = signal_for(
        "60.00",
        [
            step("a", TaskStepStateEnum.COMPLETED, "A", 1830, 1),
            step("b", TaskStepStateEnum.PAUSED, "B", 1790, 2),
        ],
        {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
    )
    assert (
        signal.over_seconds,
        signal.over_cost_minor,
        signal.projected_over_seconds,
        signal.projected_over_cost_minor,
        signal.budget_state,
    ) == (20, 1, 30, 2, "over")


def test_c6d_projected_over_state_requires_the_floor():
    signal = signal_for(
        "60.00",
        [
            step("a", TaskStepStateEnum.COMPLETED, "A", 1860, 1),
            step("b", TaskStepStateEnum.PENDING, "B", 0, 2),
        ],
        {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
    )
    assert (
        signal.over_seconds,
        signal.over_cost_minor,
        signal.projected_over_seconds,
        signal.projected_over_cost_minor,
        signal.budget_state,
    ) == (0, 0, 60, 4, "projected_over")


def test_c6e_within_budget_can_serve_a_sub_floor_projection_pair():
    signal = signal_for(
        "60.00",
        [
            step("a", TaskStepStateEnum.COMPLETED, "A", 1830, 1),
            step("b", TaskStepStateEnum.PENDING, "B", 0, 2),
        ],
        {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
    )
    assert (
        signal.over_seconds,
        signal.over_cost_minor,
        signal.projected_over_seconds,
        signal.projected_over_cost_minor,
        signal.budget_state,
    ) == (0, 0, 30, 2, "within_budget")


def test_c6f_within_budget_has_zero_overrun_figures_when_not_heading_over():
    signal = signal_for(
        "60.00",
        [
            step("a", TaskStepStateEnum.WORKING, "A", 600, 1),
            step("b", TaskStepStateEnum.PENDING, "B", 0, 2),
        ],
        {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
    )
    assert (
        signal.over_seconds,
        signal.over_cost_minor,
        signal.projected_over_seconds,
        signal.projected_over_cost_minor,
        signal.budget_state,
        signal.allowed_seconds,
        signal.actual_worked_seconds,
    ) == (0, 0, 0, 0, "within_budget", 3600, 600)


def test_c6g_over_precedes_competing_projection():
    signal = signal_for(
        "-12.50",
        [
            step("a", TaskStepStateEnum.WORKING, "A", 60, 1),
            step("b", TaskStepStateEnum.PENDING, "B", 0, 2),
        ],
        {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
    )
    assert signal.budget_state == "over"
    assert signal.projected_over_seconds >= 60
    assert (
        budget_signal.has_work_ahead(
            rows(
                "-12.50",
                [
                    step("a", TaskStepStateEnum.WORKING, "A", 60, 1),
                    step("b", TaskStepStateEnum.PENDING, "B", 0, 2),
                ],
                {key: selected(key, value) for key, value in EQUAL_TYPICALS.items()},
            )["sections"]
        )
        is True
    )


def test_c6h_over_implies_projection_is_at_least_the_incurred_seconds():
    fixtures = [
        (
            "60.00",
            [
                step("a", TaskStepStateEnum.COMPLETED, "A", 3700, 1),
                step("b", TaskStepStateEnum.PENDING, "B", 0, 2),
            ],
            EQUAL_TYPICALS,
        ),
        (
            "60.00",
            [
                step("a", TaskStepStateEnum.COMPLETED, "A", 1830, 1),
                step("b", TaskStepStateEnum.PAUSED, "B", 1790, 2),
            ],
            EQUAL_TYPICALS,
        ),
        (
            "-12.50",
            [
                step("a", TaskStepStateEnum.WORKING, "A", 60, 1),
                step("b", TaskStepStateEnum.PENDING, "B", 0, 2),
            ],
            EQUAL_TYPICALS,
        ),
        (
            "60.00",
            [
                step("a", TaskStepStateEnum.COMPLETED, "A", 1800, 1),
                step("b", TaskStepStateEnum.COMPLETED, "B", 1801, 2),
            ],
            EQUAL_TYPICALS,
        ),
    ]
    for allowed, task_steps, typical_values in fixtures:
        signal = signal_for(
            allowed,
            task_steps,
            {key: selected(key, value) for key, value in typical_values.items()},
        )
        assert signal.over_seconds > 0
        assert signal.projected_over_seconds >= signal.over_seconds
    assert (
        signal.over_seconds,
        signal.over_cost_minor,
        signal.projected_over_seconds,
        signal.projected_over_cost_minor,
        signal.budget_state,
    ) == (1, 0, 1, 0, "over")


def test_c7a_currency_sentinel_and_derived_vocabulary():
    assert type(budget_signal.NO_CURRENCY) is str
    assert budget_signal.NO_CURRENCY == "no_currency"
    assert budget_signal.CURRENCY_VOCABULARY == frozenset(
        {
            "swedish_krona",
            "danish_krona",
            "euro",
            budget_signal.NO_CURRENCY,
        }
    )
    assert all(type(value) is str for value in budget_signal.CURRENCY_VOCABULARY)


def _assert_persisted_currency_enum_untouched(enum_cls):
    assert len(enum_cls) == 3
    assert all(member.value != budget_signal.NO_CURRENCY for member in enum_cls)


def test_c7b_currency_sentinel_is_not_persisted():
    _assert_persisted_currency_enum_untouched(ItemCurrencyEnum)

    class FourCurrencyValues(enum.Enum):
        SWEDISH_KRONA = "swedish_krona"
        DANISH_KRONA = "danish_krona"
        EURO = "euro"
        NO_CURRENCY = "no_currency"

    with pytest.raises(AssertionError):
        _assert_persisted_currency_enum_untouched(FourCurrencyValues)


def test_c7c_currency_sentinel_literal_occurs_once_in_application_sources():
    package_root = Path(__file__).parents[4] / "beyo_manager"
    occurrences = sum(
        source.count('"no_currency"') + source.count("'no_currency'")
        for source_file in package_root.rglob("*.py")
        for source in [source_file.read_text()]
        if ".venv" not in source_file.parts
    )
    assert occurrences == 1


def test_c7d_currency_values_are_not_quoted_in_the_domain_module():
    source = inspect.getsource(budget_signal)
    for currency in ItemCurrencyEnum:
        assert f'"{currency.value}"' not in source
        assert f"'{currency.value}'" not in source


def test_c8a_budget_state_public_constants_are_closed():
    assert budget_signal.BUDGET_STATE_NO_BUDGET == "no_budget"
    assert budget_signal.BUDGET_STATE_OVER == "over"
    assert budget_signal.BUDGET_STATE_PROJECTED_OVER == "projected_over"
    assert budget_signal.BUDGET_STATE_WITHIN_BUDGET == "within_budget"
    assert budget_signal.BUDGET_STATES == frozenset(
        {
            budget_signal.BUDGET_STATE_NO_BUDGET,
            budget_signal.BUDGET_STATE_OVER,
            budget_signal.BUDGET_STATE_PROJECTED_OVER,
            budget_signal.BUDGET_STATE_WITHIN_BUDGET,
        }
    )


def test_c8b_projection_floor_is_an_int():
    assert type(budget_signal.PROJECTED_OVER_FLOOR_SECONDS) is int
    assert budget_signal.PROJECTED_OVER_FLOOR_SECONDS == 60


def test_c8c_budget_signal_dataclass_surface_is_exact():
    assert tuple(budget_signal.BudgetSignal.__dataclass_fields__) == (
        "budget_state",
        "over_seconds",
        "over_cost_minor",
        "projected_over_seconds",
        "projected_over_cost_minor",
        "allowed_seconds",
        "actual_worked_seconds",
        "cost_per_worker_minute_ten_thousandths",
    )


def test_c8d_budget_signal_is_frozen():
    signal = budget_signal.BudgetSignal("within_budget", 0, 0, 0, 0, 1, 2, 3)
    with pytest.raises(FrozenInstanceError):
        signal.allowed_seconds = 4
    assert budget_signal.BudgetSignal.__dataclass_params__.frozen is True


def test_c8e_public_callable_signatures_are_closed():
    contributes_signature = inspect.signature(budget_signal.contributes)
    remaining_signature = inspect.signature(budget_signal.remaining_commitment)
    ahead_signature = inspect.signature(budget_signal.has_work_ahead)
    compute_signature = inspect.signature(budget_signal.compute_budget_signal)
    contributes_hints = get_type_hints(budget_signal.contributes)
    remaining_hints = get_type_hints(budget_signal.remaining_commitment)
    ahead_hints = get_type_hints(budget_signal.has_work_ahead)
    compute_hints = get_type_hints(budget_signal.compute_budget_signal)

    assert tuple(contributes_signature.parameters) == ("section",)
    assert contributes_hints == {
        "section": budget_signal.Mapping[str, object],
        "return": bool,
    }
    assert tuple(remaining_signature.parameters) == ("sections",)
    assert remaining_hints == {
        "sections": budget_signal.Sequence[budget_signal.Mapping[str, object]],
        "return": int,
    }
    assert tuple(ahead_signature.parameters) == ("sections",)
    assert ahead_hints == {
        "sections": budget_signal.Sequence[budget_signal.Mapping[str, object]],
        "return": bool,
    }
    assert tuple(compute_signature.parameters) == (
        "sections",
        "allowed_seconds_raw",
        "actual_worked_seconds",
        "cost_per_worker_minute_minor_snapshot",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in compute_signature.parameters.values()
    )
    assert compute_hints == {
        "sections": budget_signal.Sequence[budget_signal.Mapping[str, object]],
        "allowed_seconds_raw": int,
        "actual_worked_seconds": int,
        "cost_per_worker_minute_minor_snapshot": Decimal,
        "return": budget_signal.BudgetSignal,
    }
