from decimal import Decimal

from beyo_manager.domain.item_economics.budget_division import (
    DivisionStep,
    divide_production_budget,
)


def step(client_id, state="pending", section="section", worked=0, sequence_order=None, typical=None, deleted=False):
    return DivisionStep(
        client_id=client_id,
        state=state,
        working_section_id=section,
        total_working_seconds=worked,
        sequence_order=sequence_order,
        typical_worker_seconds=typical,
        is_deleted=deleted,
    )


def allocated_rows(result):
    return [row for row in result["steps"] if row["share_state"] != "excluded"]


def test_largest_remainder_preserves_distributable_sum():
    result = divide_production_budget(
        Decimal("1.01"),
        [step("a", typical=1), step("b", typical=1), step("c", typical=1)],
        {"section": 1},
    )
    rows = allocated_rows(result)
    assert sum(row["allowance_seconds"] for row in rows) == 61
    assert [row["allowance_seconds"] for row in rows] == [21, 20, 20]


def test_excluded_consumption_is_charged_before_division_and_clamped():
    result = divide_production_budget(
        Decimal("60.00"),
        [step("failed", "failed", worked=2400), step("live-a", typical=1), step("live-b", typical=1)],
        {"section": 1},
    )
    assert result["distributable_seconds"] == 1200
    assert sum(row["allowance_seconds"] or 0 for row in allocated_rows(result)) == 1200
    assert next(row for row in result["steps"] if row["step_id"] == "failed")["share_state"] == "excluded"

    clamped = divide_production_budget(
        Decimal("1.00"),
        [step("failed", "failed", worked=100), step("live", typical=1)],
        {"section": 1},
    )
    assert clamped["distributable_seconds"] == 0
    assert next(row for row in clamped["steps"] if row["step_id"] == "live")["allowance_seconds"] == 0


def test_typicals_proportionally_weight_and_missing_typicals_split_equally():
    proportional = divide_production_budget(
        Decimal("90.00"),
        [step("a", section="a", typical=3600), step("b", section="b", typical=1800)],
        {"a": 3600, "b": 1800},
    )
    rows = {row["step_id"]: row for row in allocated_rows(proportional)}
    assert rows["a"]["allowance_seconds"] == 3600
    assert rows["b"]["allowance_seconds"] == 1800

    equal = divide_production_budget(
        Decimal("1.00"), [step("a", section="a"), step("b", section="b")], {"a": None, "b": None}
    )
    assert [row["allowance_seconds"] for row in allocated_rows(equal)] == [30, 30]


def test_tie_order_is_nulls_last_then_client_id():
    result = divide_production_budget(
        Decimal("0.05"),
        [step("b", sequence_order=None, typical=1), step("a", sequence_order=None, typical=1)],
        {"section": 1},
    )
    rows = {row["step_id"]: row for row in allocated_rows(result)}
    assert rows["a"]["allowance_seconds"] == 2
    assert rows["b"]["allowance_seconds"] == 1

    result = divide_production_budget(
        Decimal("0.05"),
        [step("a", sequence_order=None, typical=1), step("z", sequence_order=1, typical=1)],
        {"section": 1},
    )
    rows = {row["step_id"]: row for row in allocated_rows(result)}
    assert rows["z"]["allowance_seconds"] == 2


def test_live_step_set_redivides_and_removed_steps_are_not_in_universe():
    base = [step("a", typical=1), step("b", typical=1)]
    with_new = divide_production_budget(Decimal("1.00"), base + [step("c", typical=1)], {"section": 1})
    assert sum(row["allowance_seconds"] for row in allocated_rows(with_new)) == 60
    after_skip = divide_production_budget(
        Decimal("1.00"), [base[0], step("b", "skipped", worked=10)], {"section": 1}
    )
    assert next(row for row in after_skip["steps"] if row["step_id"] == "a")["allowance_seconds"] == 50
    assert next(row for row in after_skip["steps"] if row["step_id"] == "b")["share_state"] == "excluded"
    deleted = divide_production_budget(Decimal("1.00"), [step("a", deleted=True), base[1]], {"section": 1})
    assert {row["step_id"] for row in deleted["steps"]} == {"b"}


def test_fallback_median_interpolates_even_values():
    result = divide_production_budget(
        Decimal("100.00"),
        [step("missing", section="missing"), step("one", section="one"), step("two", section="two"), step("three", section="three")],
        {"missing": None, "one": 600, "two": 1200, "three": 6000},
    )
    rows = {row["step_id"]: row for row in allocated_rows(result)}
    assert rows["missing"]["typical_worker_seconds"] is None
    # The fallback is (600 + 1200 + 6000) median = 1200, so it is not the mean.
    assert rows["missing"]["allowance_seconds"] == 800

    even = divide_production_budget(
        Decimal("100.00"),
        [step("missing", section="missing"), step("a", section="a"), step("b", section="b"), step("c", section="c"), step("d", section="d")],
        {"missing": None, "a": 600, "b": 1200, "c": 1800, "d": 6000},
    )
    assert next(row for row in allocated_rows(even) if row["step_id"] == "missing")["allowance_seconds"] == 811


def test_no_budget_and_zero_typicals():
    no_budget = divide_production_budget(None, [step("a", typical=3600)], {"section": 3600})
    assert no_budget["steps"][0]["share_state"] == "no_budget"
    assert no_budget["steps"][0]["allowance_seconds"] is None

    zero = divide_production_budget(
        Decimal("1.00"), [step("a", typical=0), step("b", typical=0)], {"section": 0}
    )
    assert sum(row["allowance_seconds"] for row in allocated_rows(zero)) == 60


def test_all_excluded_steps_return_task_figures_without_division():
    result = divide_production_budget(
        Decimal("10.00"),
        [step("skipped", "skipped", worked=120), step("failed", "failed", worked=60)],
        {"section": 1},
    )
    assert result["budget_seconds"] == 600
    assert result["charged_seconds"] == 180
    assert result["distributable_seconds"] == 420
    assert [row["share_state"] for row in result["steps"]] == ["excluded", "excluded"]
    assert all(row["allowance_seconds"] is None for row in result["steps"])


def test_half_even_budget_seconds_quantization():
    result = divide_production_budget(
        Decimal("195.01"), [step("a", typical=1), step("b", typical=1), step("c", typical=1)], {"section": 1}
    )
    assert result["budget_seconds"] == 11701
    assert sum(row["allowance_seconds"] for row in allocated_rows(result)) == 11701
