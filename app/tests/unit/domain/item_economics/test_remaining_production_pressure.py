from decimal import Decimal
from fractions import Fraction

from beyo_manager.domain.item_economics.budget_division import (
    DivisionStep,
    divide_production_budget,
)
from beyo_manager.domain.item_economics.remaining_production_pressure import (
    PRESSURE_METHOD,
    compute_remaining_pressure,
)
from beyo_manager.domain.item_economics.typical_filters import (
    SectionTypicalEvidence,
    SelectedTypical,
)


def _step(step_id, *, state="pending", allowance=10, worked=0, section="section"):
    return {
        "step_id": step_id,
        "state": state,
        "working_section_id": section,
        "allowance_seconds": allowance,
        "worked_seconds": worked,
        "left_seconds": allowance - worked,
        "share_state": "excluded"
        if state in {"skipped", "cancelled", "failed"}
        else "on_track",
    }


def _division(*steps, distributable=100):
    return {"distributable_seconds": distributable, "steps": list(steps)}


def _selected(section, seconds=1):
    evidence = SectionTypicalEvidence(section, None, 0, seconds, 5)
    return SelectedTypical(section, seconds, "section_wide", evidence, True, 5)


def test_pressure_is_an_exact_largest_remainder_allocation_and_not_a_countdown():
    division = _division(
        _step("settled", state="completed", allowance=50, worked=30, section="done"),
        _step("weaving", allowance=60, worked=0, section="weaving"),
        _step("photography", allowance=40, worked=0, section="photography"),
    )
    result = compute_remaining_pressure(division)
    assert result.pressure_ratio == Fraction(7, 10)
    assert result.pressure_share_seconds_by_step_id == {
        "settled": None,
        "weaving": 42,
        "photography": 28,
    }

    division["steps"][1]["worked_seconds"] = 42
    division["steps"][1]["left_seconds"] = 18
    assert compute_remaining_pressure(division) == result
    assert PRESSURE_METHOD == "open_share_proportional_v1"


def test_consuming_step_squeezes_peers_live_and_its_share_stays_zero():
    division = _division(
        _step("over", allowance=50, worked=51, section="over"),
        _step("next", allowance=50, section="next"),
    )
    first = compute_remaining_pressure(division)
    assert first.pressure_ratio == Fraction(49, 50)
    assert first.pressure_share_seconds_by_step_id == {"over": 0, "next": 49}

    division["steps"][0]["worked_seconds"] = 52
    division["steps"][0]["left_seconds"] = -2
    second = compute_remaining_pressure(division)
    assert second.pressure_ratio == Fraction(48, 50)
    assert second.pressure_share_seconds_by_step_id == {"over": 0, "next": 48}


def test_null_zero_and_unclamped_ratio_boundaries():
    positive = compute_remaining_pressure(
        _division(_step("a", allowance=10), distributable=20)
    )
    assert positive.pressure_ratio == Fraction(2)
    assert positive.pressure_share_seconds_by_step_id == {"a": 20}

    negative = compute_remaining_pressure(
        _division(
            _step("done", state="completed", worked=15),
            _step("a", allowance=10),
            distributable=10,
        )
    )
    assert negative.pressure_ratio == Fraction(-1, 2)
    assert negative.pressure_share_seconds_by_step_id == {"done": None, "a": 0}

    zero_allowance = compute_remaining_pressure(
        _division(_step("a", allowance=0), distributable=10)
    )
    assert zero_allowance.pressure_ratio is None
    assert zero_allowance.pressure_share_seconds_by_step_id == {"a": 0}

    no_open = compute_remaining_pressure(
        _division(_step("done", state="completed", worked=10))
    )
    assert no_open.pressure_ratio is None
    assert no_open.pressure_share_seconds_by_step_id == {"done": None}

    no_budget = compute_remaining_pressure(
        {"distributable_seconds": None, "steps": [_step("a", allowance=0)]}
    )
    assert no_budget.pressure_ratio is None
    assert no_budget.pressure_share_seconds_by_step_id == {"a": None}


def test_excluded_and_negative_residual_steps_are_not_allocatable():
    result = compute_remaining_pressure(
        _division(
            _step("excluded", state="skipped", allowance=0, worked=20),
            _step("negative", allowance=-5, worked=0),
            _step("next", allowance=10),
            distributable=20,
        )
    )
    assert result.pressure_ratio == Fraction(2)
    assert result.pressure_share_seconds_by_step_id == {
        "excluded": None,
        "negative": 0,
        "next": 20,
    }


def test_real_allocator_output_keeps_allowances_unchanged_and_drives_pressure():
    steps = [
        DivisionStep("done", "completed", "done", total_working_seconds=20),
        DivisionStep("open_a", "pending", "a", total_working_seconds=0),
        DivisionStep("open_b", "pending", "b", total_working_seconds=0),
    ]
    division = divide_production_budget(
        Decimal("2.00"),
        steps,
        {"done": _selected("done"), "a": _selected("a"), "b": _selected("b")},
    )
    before_allowances = {
        row["step_id"]: row["allowance_seconds"] for row in division["steps"]
    }
    result = compute_remaining_pressure(division)
    assert (
        sum(value or 0 for value in result.pressure_share_seconds_by_step_id.values())
        == 100
    )
    assert {
        row["step_id"]: row["allowance_seconds"] for row in division["steps"]
    } == before_allowances
