from decimal import Decimal
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from beyo_manager.domain.item_economics.budget_division import (
    DivisionStep,
    _section_sort_key,
    divide_production_budget,
    group_steps_by_section,
)
from beyo_manager.domain.item_economics.typical_filters import SectionTypicalEvidence, SelectedTypical
from beyo_manager.domain.item_economics.typical_constants import TYPICAL_MIN_SAMPLE_SIZE


def selected(section, value, basis=None, count=None):
    if basis is None:
        basis = "insufficient_sample" if value is None else "section_wide"
    if count is None:
        count = 0 if basis == "insufficient_sample" else TYPICAL_MIN_SAMPLE_SIZE
    evidence = SectionTypicalEvidence(section, None, 0, value, count)
    return SelectedTypical(section, value, basis, evidence, True, count)


def step(client_id, state="pending", section="section", worked=0, sequence_order=None, deleted=False):
    return DivisionStep(
        client_id=client_id,
        state=state,
        working_section_id=section,
        total_working_seconds=worked,
        sequence_order=sequence_order,
        is_deleted=deleted,
    )


def allocated_rows(result):
    return [row for row in result["steps"] if row["share_state"] != "excluded"]


def test_largest_remainder_preserves_distributable_sum():
    result = divide_production_budget(
        Decimal("1.01"),
        [step("a"), step("b"), step("c")],
        {"section": selected("section", 1)},
    )
    rows = allocated_rows(result)
    assert sum(row["allowance_seconds"] for row in rows) == 61
    assert [row["allowance_seconds"] for row in rows] == [21, 20, 20]


def test_excluded_consumption_is_charged_before_division_and_clamped():
    result = divide_production_budget(
        Decimal("60.00"),
        [step("failed", "failed", worked=2400), step("live-a"), step("live-b")],
        {"section": selected("section", 1)},
    )
    assert result["distributable_seconds"] == 1200
    assert sum(row["allowance_seconds"] or 0 for row in allocated_rows(result)) == 1200
    assert next(row for row in result["steps"] if row["step_id"] == "failed")["share_state"] == "excluded"

    clamped = divide_production_budget(
        Decimal("1.00"),
        [step("failed", "failed", worked=100), step("live")],
        {"section": selected("section", 1)},
    )
    assert clamped["distributable_seconds"] == 0
    assert next(row for row in clamped["steps"] if row["step_id"] == "live")["allowance_seconds"] == 0
    assert next(row for row in clamped["steps"] if row["step_id"] == "live")["share_state"] == "over_share"


def test_typicals_proportionally_weight_and_missing_typicals_split_equally():
    proportional = divide_production_budget(
        Decimal("90.00"),
        [step("a", section="a"), step("b", section="b")],
        {"a": selected("a", 3600), "b": selected("b", 1800)},
    )
    rows = {row["step_id"]: row for row in allocated_rows(proportional)}
    assert rows["a"]["allowance_seconds"] == 3600
    assert rows["b"]["allowance_seconds"] == 1800

    equal = divide_production_budget(
        Decimal("1.00"), [step("a", section="a"), step("b", section="b")],
        {"a": selected("a", None), "b": selected("b", None)},
    )
    assert [row["allowance_seconds"] for row in allocated_rows(equal)] == [30, 30]


def test_tie_order_is_nulls_last_then_client_id():
    result = divide_production_budget(
        Decimal("0.05"),
        [step("b", sequence_order=None), step("a", sequence_order=None)],
        {"section": selected("section", 1)},
    )
    rows = {row["step_id"]: row for row in allocated_rows(result)}
    assert rows["a"]["allowance_seconds"] == 2
    assert rows["b"]["allowance_seconds"] == 1

    result = divide_production_budget(
        Decimal("0.05"),
        [step("a", sequence_order=None), step("z", sequence_order=1)],
        {"section": selected("section", 1)},
    )
    rows = {row["step_id"]: row for row in allocated_rows(result)}
    assert rows["a"]["allowance_seconds"] == 1
    assert rows["z"]["allowance_seconds"] == 2


def test_live_step_set_redivides_and_removed_steps_are_not_in_universe():
    base = [step("a"), step("b")]
    with_new = divide_production_budget(Decimal("1.00"), base + [step("c")], {"section": selected("section", 1)})
    assert sum(row["allowance_seconds"] for row in allocated_rows(with_new)) == 60
    after_skip = divide_production_budget(
        Decimal("1.00"), [base[0], step("b", "skipped", worked=10)], {"section": selected("section", 1)}
    )
    assert next(row for row in after_skip["steps"] if row["step_id"] == "a")["allowance_seconds"] == 50
    assert next(row for row in after_skip["steps"] if row["step_id"] == "b")["share_state"] == "excluded"
    deleted = divide_production_budget(Decimal("1.00"), [step("a", deleted=True), base[1]], {"section": selected("section", 1)})
    assert {row["step_id"] for row in deleted["steps"]} == {"b"}


def test_live_partition_includes_working_paused_and_completed_steps():
    live = [
        step("pending", "pending"),
        step("working", "working"),
        step("paused", "paused"),
        step("completed", "completed"),
    ]
    base = divide_production_budget(Decimal("1.00"), live, {"section": selected("section", 1)})
    assert {row["step_id"]: row["allowance_seconds"] for row in allocated_rows(base)} == {
        "pending": 20,
        "working": 20,
        "paused": 20,
        "completed": 0,
    }

    with_new = divide_production_budget(
        Decimal("1.00"),
        [*live, step("new", "pending")],
        {"section": selected("section", 1)},
    )
    assert {row["step_id"]: row["allowance_seconds"] for row in allocated_rows(with_new)} == {
        "pending": 15,
        "working": 15,
        "paused": 15,
        "completed": 0,
        "new": 15,
    }

    after_skip = divide_production_budget(
        Decimal("1.00"),
        [live[0], live[1], live[2], step("completed", "skipped")],
        {"section": selected("section", 1)},
    )
    rows = {row["step_id"]: row for row in after_skip["steps"]}
    assert {step_id: rows[step_id]["allowance_seconds"] for step_id in ("pending", "working", "paused")} == {
        "pending": 20,
        "working": 20,
        "paused": 20,
    }
    assert rows["completed"]["share_state"] == "excluded"


def test_fallback_median_interpolates_even_values():
    result = divide_production_budget(
        Decimal("100.00"),
        [step("missing", section="missing"), step("one", section="one"), step("two", section="two"), step("three", section="three")],
        {"missing": selected("missing", None), "one": selected("one", 600), "two": selected("two", 1200), "three": selected("three", 6000)},
    )
    rows = {row["step_id"]: row for row in allocated_rows(result)}
    assert rows["missing"]["typical_worker_seconds"] is None
    # The fallback is (600 + 1200 + 6000) median = 1200, so it is not the mean.
    assert rows["missing"]["allowance_seconds"] == 800

    even = divide_production_budget(
        Decimal("100.00"),
        [step("missing", section="missing"), step("a", section="a"), step("b", section="b"), step("c", section="c"), step("d", section="d")],
        {"missing": selected("missing", None), "a": selected("a", 600), "b": selected("b", 1200), "c": selected("c", 1800), "d": selected("d", 6000)},
    )
    assert next(row for row in allocated_rows(even) if row["step_id"] == "missing")["allowance_seconds"] == 811


def test_no_budget_and_zero_typicals():
    no_budget = divide_production_budget(None, [step("a")], {"section": selected("section", 3600)})
    assert no_budget["steps"][0]["share_state"] == "no_budget"
    assert no_budget["steps"][0]["allowance_seconds"] is None

    zero = divide_production_budget(
        Decimal("1.00"), [step("a"), step("b")], {"section": selected("section", 0)},
    )
    assert sum(row["allowance_seconds"] for row in allocated_rows(zero)) == 60


def test_all_excluded_steps_return_task_figures_without_division():
    result = divide_production_budget(
        Decimal("10.00"),
        [step("skipped", "skipped", worked=120), step("failed", "failed", worked=60)],
        {"section": selected("section", 1)},
    )
    assert result["budget_seconds"] == 600
    assert result["charged_seconds"] == 180
    assert result["distributable_seconds"] == 420
    assert [row["share_state"] for row in result["steps"]] == ["excluded", "excluded"]
    assert all(row["allowance_seconds"] is None for row in result["steps"])


def test_deleted_skipped_step_is_outside_budget_universe_but_live_skipped_is_charged():
    result = divide_production_budget(
        Decimal("10.00"),
        [
            step("deleted", "skipped", worked=300, deleted=True),
            step("live-skipped", "skipped", worked=120),
            step("working", "working"),
        ],
        {"section": selected("section", 1)},
    )
    rows = {row["step_id"]: row for row in result["steps"]}
    assert result["charged_seconds"] == 120
    assert result["distributable_seconds"] == 480
    assert set(rows) == {"live-skipped", "working"}
    assert rows["live-skipped"]["share_state"] == "excluded"
    assert rows["working"]["allowance_seconds"] == 480


def test_half_even_budget_seconds_quantization():
    result = divide_production_budget(
        Decimal("195.01"), [step("a"), step("b"), step("c")], {"section": selected("section", 1)},
    )
    assert result["budget_seconds"] == 11701
    assert sum(row["allowance_seconds"] for row in allocated_rows(result)) == 11701


def test_c3_section_sort_key_uses_id_as_final_backstop():
    assert _section_sort_key({"order_list": 2, "name": "Same", "working_section_id": "a"}) < _section_sort_key(
        {"order_list": 2, "name": "Same", "working_section_id": "b"}
    )


def test_c5_section_unit_weights_a_reassigned_section_once():
    result = divide_production_budget(
        Decimal("180.00"),
        [
            step("structural", section="structural"),
            step("sanding", section="sanding"),
            step("upholstery-a", section="upholstery"),
            step("upholstery-b", section="upholstery"),
        ],
        {"structural": selected("structural", 3600), "sanding": selected("sanding", 1800), "upholstery": selected("upholstery", 3600)},
    )
    allowances = {row["working_section_id"]: row["allowance_seconds"] for row in result["sections"]}
    assert allowances == {"structural": 4320, "sanding": 2160, "upholstery": 4320}
    assert [row["allowance_seconds"] for row in result["sections"]] != [3086, 1543, 6171]


def test_c7_multi_open_governing_step_and_equal_remainder_tie_are_deterministic():
    now = datetime.now(timezone.utc)
    first = DivisionStep(
        client_id="first", state="pending", working_section_id="section",
        created_at=now - timedelta(minutes=2),
        latest_state_record=SimpleNamespace(entered_at=now - timedelta(minutes=2)),
    )
    second = DivisionStep(
        client_id="second", state="pending", working_section_id="section",
        created_at=now - timedelta(minutes=1),
        latest_state_record=SimpleNamespace(entered_at=now - timedelta(minutes=1)),
    )
    result = divide_production_budget(Decimal("0.05"), [second, first], {"section": selected("section", 1)})
    rows = {row["step_id"]: row for row in result["steps"]}
    assert rows["first"]["allowance_seconds"] == 2
    assert rows["second"]["allowance_seconds"] == 1
    assert result["sections"][0]["state"] == "pending"


def test_c6c_multi_open_governing_precedence_is_entered_created_then_client_id():
    now = datetime.now(timezone.utc)
    entered_winner = DivisionStep(
        client_id="z-winner", state="pending", working_section_id="section",
        created_at=now - timedelta(minutes=3),
        latest_state_record=SimpleNamespace(entered_at=now - timedelta(minutes=1)),
    )
    created_winner = DivisionStep(
        client_id="b-created", state="working", working_section_id="section",
        created_at=now - timedelta(minutes=1),
        latest_state_record=SimpleNamespace(entered_at=now - timedelta(minutes=2)),
    )
    client_id_winner = DivisionStep(
        client_id="a-client", state="paused", working_section_id="section",
        created_at=now - timedelta(minutes=2),
        latest_state_record=SimpleNamespace(entered_at=now - timedelta(minutes=3)),
    )
    result = divide_production_budget(
        Decimal("1.00"),
        [created_winner, client_id_winner, entered_winner],
        {"section": selected("section", 1)},
    )
    assert result["sections"][0]["state"] == "pending"


def test_c6_later_live_step_governs_section_state():
    now = datetime.now(timezone.utc)
    pending = DivisionStep(
        client_id="pending", state="pending", working_section_id="section", created_at=now - timedelta(minutes=2),
        latest_state_record=SimpleNamespace(entered_at=now - timedelta(minutes=2)),
    )
    completed = DivisionStep(
        client_id="completed", state="completed", working_section_id="section", created_at=now - timedelta(minutes=1),
        latest_state_record=SimpleNamespace(entered_at=now - timedelta(minutes=1)),
    )
    assert group_steps_by_section([completed, pending])[0]["state"] == "pending"


def test_c10_section_allowances_sum_exactly_on_indivisible_budget():
    result = divide_production_budget(
        Decimal("1.01"),
        [step("a", section="a"), step("b", section="b"), step("c", section="c")],
        {"a": selected("a", 1), "b": selected("b", 1), "c": selected("c", 1)},
    )
    assert sum(row["allowance_seconds"] for row in result["sections"]) == result["distributable_seconds"] == 61
