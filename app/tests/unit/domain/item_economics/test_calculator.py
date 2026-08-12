from decimal import Decimal, ROUND_CEILING, getcontext, localcontext
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from beyo_manager.domain.item_economics import calculator
from beyo_manager.domain.item_economics.calculator import (
    CALCULATION_VERSION,
    REDERIVE_MISMATCH,
    REDERIVE_SKIPPED,
    calculate_actual_worker_minutes,
    calculate_allowed_worker_minutes,
    calculate_consumed_cost_minor,
    calculate_cost_per_worker_minute,
    calculate_percent_consumed,
    calculate_percentage_term_amount,
    calculate_production_budget,
    calculate_remaining_worker_minutes,
    calculate_term_amount,
    calculate_term_amounts,
    calculate_variance_cost_minor,
    calculate_variance_worker_minutes,
    rederive,
    validate_currency_equality,
)
from beyo_manager.domain.item_economics.enums import (
    CostModelTermCalculationTypeEnum,
    ItemCostEvaluationKindEnum,
)
from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.domain.tasks.enums import TaskReturnSourceEnum, TaskTypeEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_cost_evaluation_term import ItemCostEvaluationTerm


def _term(
    calculation_type: CostModelTermCalculationTypeEnum,
    *,
    percent_value: Decimal | None = None,
    fixed_amount_minor: int | None = None,
    amount_minor: int = 0,
    name: str = "term",
) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        calculation_type=calculation_type,
        percent_value=percent_value,
        fixed_amount_minor=fixed_amount_minor,
        amount_minor=amount_minor,
    )


@pytest.mark.parametrize(
    ("calculation_type", "percent_value", "fixed_amount_minor", "expected"),
    [
        (
            CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE,
            Decimal("15.000"),
            None,
            600,
        ),
        (CostModelTermCalculationTypeEnum.FIXED_AMOUNT, None, 575, 575),
        (CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST, None, None, 1234),
        (
            CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE,
            None,
            None,
            None,
        ),
        (
            CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE,
            None,
            575,
            None,
        ),
        (
            CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE,
            Decimal("15.000"),
            575,
            None,
        ),
        (CostModelTermCalculationTypeEnum.FIXED_AMOUNT, None, None, None),
        (
            CostModelTermCalculationTypeEnum.FIXED_AMOUNT,
            Decimal("15.000"),
            None,
            None,
        ),
        (
            CostModelTermCalculationTypeEnum.FIXED_AMOUNT,
            Decimal("15.000"),
            575,
            None,
        ),
        (CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST, Decimal("15.000"), None, None),
        (CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST, None, 575, None),
        (
            CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST,
            Decimal("15.000"),
            575,
            None,
        ),
    ],
    ids=[
        "percentage-valid",
        "fixed-valid",
        "purchase-valid",
        "percentage-missing-percent",
        "percentage-fixed-only",
        "percentage-both-values",
        "fixed-missing-fixed",
        "fixed-percent-only",
        "fixed-both-values",
        "purchase-percent-only",
        "purchase-fixed-only",
        "purchase-both-values",
    ],
)
def test_term_shape_table_varies_only_the_term_value_columns(
    calculation_type: CostModelTermCalculationTypeEnum,
    percent_value: Decimal | None,
    fixed_amount_minor: int | None,
    expected: int | None,
) -> None:
    if expected is None:
        with pytest.raises(ValidationError, match="^ITEM_COST_TERM_SHAPE_INVALID:"):
            calculate_term_amount(
                calculation_type,
                4000,
                percent_value,
                fixed_amount_minor,
                1234,
            )
    else:
        assert (
            calculate_term_amount(
                calculation_type,
                4000,
                percent_value,
                fixed_amount_minor,
                1234,
            )
            == expected
        )


def test_purchase_term_missing_purchase_cost_varies_only_the_purchase_snapshot_field() -> None:
    with pytest.raises(ValidationError, match="^ITEM_COST_PURCHASE_COST_REQUIRED:"):
        calculate_term_amount(
            CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST,
            4000,
            None,
            None,
            None,
        )


def test_duplicate_purchase_terms_vary_only_the_snapshot_term_rows() -> None:
    rows = [
        _term(CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST, name="purchase-a"),
        _term(CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST, name="purchase-b"),
    ]
    with pytest.raises(ValidationError, match="^ITEM_COST_TERM_SHAPE_INVALID:"):
        calculate_term_amounts(rows, 4000, 1234)


@pytest.mark.parametrize(
    ("site", "actual", "expected"),
    [
        ("Q1", calculate_percentage_term_amount(4000, Decimal("15.000")), 600),
        ("Q2", calculate_cost_per_worker_minute(5_760_000, Decimal("320.00"), Decimal("75.00")), Decimal("400.0000")),
        ("Q3", calculate_allowed_worker_minutes(40_000_000, Decimal("400.0000")), Decimal("100000.00")),
        ("Q4-100s", calculate_actual_worker_minutes(100), Decimal("1.67")),
        ("Q4-20s", calculate_actual_worker_minutes(20), Decimal("0.33")),
        ("Q5", calculate_consumed_cost_minor(20, Decimal("400.0000")), 133),
    ],
)
def test_quantization_exactness_table(site: str, actual: object, expected: object) -> None:
    assert actual == expected, site


@pytest.mark.parametrize(
    ("site", "actual", "expected"),
    [
        ("Q1", calculate_percentage_term_amount(4900, Decimal("0.500")), 24),
        ("Q2", calculate_cost_per_worker_minute(24_000_003, Decimal("1000.00"), Decimal("100.00")), Decimal("400.0000")),
        ("Q3", calculate_allowed_worker_minutes(1, Decimal("0.0128")), Decimal("78.12")),
        ("Q5", calculate_consumed_cost_minor(60, Decimal("24.5000")), 24),
    ],
)
def test_quantization_tie_table_uses_half_even(site: str, actual: object, expected: object) -> None:
    assert actual == expected, site


def test_budget_varies_only_the_snapshot_term_amounts_and_is_order_insensitive() -> None:
    assert calculate_production_budget(10_000, []) == 10_000
    assert calculate_production_budget(10_000, [600, 575, 1234]) == 7591
    assert calculate_production_budget(10_000, [600, 11_000]) == -1600
    assert calculate_production_budget(10_000, [600, 575, 1234]) == calculate_production_budget(
        10_000, [1234, 600, 575]
    )


def test_rate_underflow_varies_only_the_fixed_cost_snapshot() -> None:
    with pytest.raises(ValidationError, match="^ITEM_COST_RATE_UNDERFLOW:"):
        calculate_cost_per_worker_minute(1, Decimal("1000.00"), Decimal("100.00"))
    assert calculate_cost_per_worker_minute(6, Decimal("1000.00"), Decimal("100.00")) == Decimal("0.0001")


def test_allowance_preserves_a_negative_budget_varied_only_in_the_budget() -> None:
    assert calculate_allowed_worker_minutes(-1000, Decimal("400.0000")) == Decimal("-2.50")


def test_percent_consumed_varies_only_the_allowed_and_actual_minute_snapshots() -> None:
    assert calculate_percent_consumed(Decimal("995.02"), Decimal("0")) == Decimal("0.00")
    assert calculate_percent_consumed(Decimal("995.02"), Decimal("203.02")) == Decimal("20.40")
    assert calculate_percent_consumed(Decimal("0.00"), Decimal("1.00")) is None
    assert calculate_percent_consumed(Decimal("-1.00"), Decimal("1.00")) is None
    assert calculate_remaining_worker_minutes(Decimal("995.02"), Decimal("203.02")) == Decimal("792.00")


def test_variance_triple_keeps_minutes_and_money_independent() -> None:
    allowed = calculate_allowed_worker_minutes(100_000, Decimal("100.5000"))
    actual = calculate_actual_worker_minutes(12_181)
    consumed = calculate_consumed_cost_minor(12_181, Decimal("100.5000"))
    assert allowed == Decimal("995.02")
    assert actual == Decimal("203.02")
    assert consumed == 20_403
    assert calculate_variance_worker_minutes(allowed, actual) == Decimal("792.00")
    assert calculate_variance_cost_minor(100_000, consumed) == 79_597
    assert Decimal("792.00") * Decimal("100.5000") == Decimal("79596.000000")


@pytest.mark.parametrize(
    "value",
    [1.0, True, Decimal("1"), "1", None],
    ids=["float", "bool", "decimal", "string", "none"],
)
def test_money_guard_excludes_non_int_arrivals(value: object) -> None:
    if value is None:
        with pytest.raises(ValidationError, match="^ITEM_COST_EXPECTED_PRICE_REQUIRED:"):
            calculate_production_budget(value, [])  # type: ignore[arg-type]
    else:
        with pytest.raises(TypeError, match="^expected_sale_price_minor must be"):
            calculate_production_budget(value, [])  # type: ignore[arg-type]


def test_system_supplied_money_none_is_a_type_error() -> None:
    with pytest.raises(TypeError, match="^production_budget_minor must be"):
        calculate_variance_cost_minor(None, 100)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [1.0, True, 1, "1", None])
def test_rate_guard_excludes_every_non_decimal_arrival(value: object) -> None:
    with pytest.raises(TypeError, match="^monthly_paid_hours must be"):
        calculate_cost_per_worker_minute(100, value, Decimal("75.00"))  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [1.0, True, Decimal("1"), "1", None])
def test_seconds_guard_excludes_every_non_int_arrival(value: object) -> None:
    with pytest.raises(TypeError, match="^actual_worker_seconds must be"):
        calculate_actual_worker_minutes(value)  # type: ignore[arg-type]


def test_purchase_cost_none_is_a_named_user_input_error() -> None:
    with pytest.raises(ValidationError, match="^ITEM_COST_PURCHASE_COST_REQUIRED:"):
        calculate_term_amount(
            CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST,
            4000,
            None,
            None,
            None,
        )


def test_negative_percentage_term_value_is_a_shape_error() -> None:
    with pytest.raises(ValidationError, match="^ITEM_COST_TERM_SHAPE_INVALID:"):
        calculate_term_amount(
            CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE,
            4000,
            Decimal("-1.000"),
            None,
            1234,
        )


def test_negative_fixed_term_value_is_a_shape_error() -> None:
    with pytest.raises(ValidationError, match="^ITEM_COST_TERM_SHAPE_INVALID:"):
        calculate_term_amount(
            CostModelTermCalculationTypeEnum.FIXED_AMOUNT,
            4000,
            None,
            -1,
            1234,
        )


def test_zero_rate_reaching_allowance_is_rate_underflow() -> None:
    with pytest.raises(ValidationError, match="^ITEM_COST_RATE_UNDERFLOW:"):
        calculate_allowed_worker_minutes(100, Decimal("0"))


def test_enum_guard_accepts_members_but_rejects_values_and_none() -> None:
    validate_currency_equality(
        ItemCurrencyEnum.SWEDISH_KRONA,
        ItemCurrencyEnum.SWEDISH_KRONA,
        ItemCurrencyEnum.SWEDISH_KRONA,
    )
    for value in ("swedish_krona", None):
        with pytest.raises(TypeError, match="^valuation_currency must be"):
            validate_currency_equality(value, ItemCurrencyEnum.SWEDISH_KRONA, ItemCurrencyEnum.SWEDISH_KRONA)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("valuation", "basis", "model", "pair"),
    [
        (ItemCurrencyEnum.EURO, ItemCurrencyEnum.SWEDISH_KRONA, ItemCurrencyEnum.SWEDISH_KRONA, "valuation"),
        (ItemCurrencyEnum.SWEDISH_KRONA, ItemCurrencyEnum.EURO, ItemCurrencyEnum.SWEDISH_KRONA, "valuation"),
        (ItemCurrencyEnum.SWEDISH_KRONA, ItemCurrencyEnum.SWEDISH_KRONA, ItemCurrencyEnum.EURO, "basis"),
    ],
)
def test_currency_mismatch_names_the_failing_pair_and_both_values(
    valuation: ItemCurrencyEnum,
    basis: ItemCurrencyEnum,
    model: ItemCurrencyEnum,
    pair: str,
) -> None:
    with pytest.raises(ValidationError) as caught:
        validate_currency_equality(valuation, basis, model)
    message = str(caught.value)
    assert message.startswith("ITEM_COST_CURRENCY_MISMATCH:")
    assert pair in message
    assert valuation.value in message
    assert basis.value in message
    assert model.value in message


def _evaluation_for_rederive(**overrides: object) -> ItemCostEvaluation:
    values: dict[str, object] = {
        "workspace_id": "ws_test",
        "task_id": "tsk_test",
        "item_id": "itm_test",
        "kind": ItemCostEvaluationKindEnum.PROJECTION,
        "task_type_snapshot": TaskTypeEnum.RETURN,
        "return_source_snapshot": TaskReturnSourceEnum.AFTER_PURCHASE,
        "expected_sale_price_minor": 4000,
        "purchase_cost_minor": 1234,
        "currency": ItemCurrencyEnum.SWEDISH_KRONA,
        "cost_model_version_id": "cmv_test",
        "production_cost_group_id": "pcg_test",
        "production_cost_basis_version_id": "pcbv_test",
        "monthly_paid_hours_snapshot": Decimal("320.00"),
        "planning_utilization_percent_snapshot": Decimal("75.00"),
        "fixed_monthly_cost_minor_snapshot": 5_760_000,
        "cost_per_worker_minute_minor_snapshot": Decimal("400.0000"),
        "production_budget_minor": 2166,
        "allowed_worker_minutes": Decimal("5.42"),
        "calculation_version": CALCULATION_VERSION,
        "created_by_id": "usr_test",
    }
    values.update(overrides)
    return ItemCostEvaluation(**values)


def test_rederive_uses_unsaved_orm_instances_and_only_the_closed_snapshot_fields() -> None:
    evaluation = _evaluation_for_rederive()
    terms = [
        ItemCostEvaluationTerm(
            workspace_id="ws_test",
            evaluation_id="ice_test",
            name="percentage allocation",
            calculation_type=CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE,
            percent_value=Decimal("15.000"),
            fixed_amount_minor=None,
            amount_minor=600,
        ),
        ItemCostEvaluationTerm(
            workspace_id="ws_test",
            evaluation_id="ice_test",
            name="fixed allocation",
            calculation_type=CostModelTermCalculationTypeEnum.FIXED_AMOUNT,
            percent_value=None,
            fixed_amount_minor=1234,
            amount_minor=1234,
        ),
    ]

    def raising_property(_: object) -> object:
        raise AssertionError("rederive read a closed-set-excluded field")

    with (
        patch.object(ItemCostEvaluation, "cost_model_version_id", property(raising_property)),
        patch.object(ItemCostEvaluation, "production_cost_group_id", property(raising_property)),
        patch.object(ItemCostEvaluation, "production_cost_basis_version_id", property(raising_property)),
        patch.object(ItemCostEvaluation, "task_type_snapshot", property(raising_property)),
        patch.object(ItemCostEvaluation, "return_source_snapshot", property(raising_property)),
    ):
        assert rederive(evaluation, terms) == (Decimal("400.0000"), 2166, Decimal("5.42"))


def test_rederive_version_mismatch_returns_named_skip_marker_before_reading_snapshots() -> None:
    evaluation = _evaluation_for_rederive(calculation_version=2)
    assert rederive(evaluation, []) == REDERIVE_SKIPPED


def test_rederive_detects_a_changed_term_amount_on_the_same_orm_shape() -> None:
    evaluation = _evaluation_for_rederive()
    terms = [
        ItemCostEvaluationTerm(
            workspace_id="ws_test",
            evaluation_id="ice_test",
            name="percentage allocation",
            calculation_type=CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE,
            percent_value=Decimal("15.000"),
            amount_minor=600,
        ),
        ItemCostEvaluationTerm(
            workspace_id="ws_test",
            evaluation_id="ice_test",
            name="fixed allocation",
            calculation_type=CostModelTermCalculationTypeEnum.FIXED_AMOUNT,
            fixed_amount_minor=1234,
            amount_minor=1235,
        ),
    ]
    result = rederive(evaluation, terms)
    assert result["marker"] == REDERIVE_MISMATCH  # type: ignore[index]
    assert result["mismatches"] == [  # type: ignore[index]
        {
            "field": "term[fixed allocation].amount_minor",
            "rederived_value": 1234,
            "stored_value": 1235,
            "error": None,
        }
    ]


def _valid_rederive_terms() -> list[ItemCostEvaluationTerm]:
    return [
        ItemCostEvaluationTerm(
            workspace_id="ws_test",
            evaluation_id="ice_test",
            name="percentage allocation",
            calculation_type=CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE,
            percent_value=Decimal("15.000"),
            fixed_amount_minor=None,
            amount_minor=600,
        ),
        ItemCostEvaluationTerm(
            workspace_id="ws_test",
            evaluation_id="ice_test",
            name="fixed allocation",
            calculation_type=CostModelTermCalculationTypeEnum.FIXED_AMOUNT,
            percent_value=None,
            fixed_amount_minor=1234,
            amount_minor=1234,
        ),
    ]


def test_rederive_malformed_evaluation_rate_returns_integrity_marker_and_cascade() -> None:
    result = rederive(
        _evaluation_for_rederive(cost_per_worker_minute_minor_snapshot=Decimal("0")),
        _valid_rederive_terms(),
    )

    assert result == {
        "marker": REDERIVE_MISMATCH,
        "mismatches": [
            {
                "field": "cost_per_worker_minute_minor_snapshot",
                "rederived_value": Decimal("400.0000"),
                "stored_value": Decimal("0"),
                "error": None,
            },
            {
                "field": "allowed_worker_minutes",
                "rederived_value": None,
                "stored_value": Decimal("5.42"),
                "error": "ITEM_COST_RATE_UNDERFLOW: cannot calculate allowance with zero rate",
            },
        ],
    }


def test_rederive_malformed_term_shape_returns_integrity_marker() -> None:
    terms = _valid_rederive_terms()
    terms[0].percent_value = None

    result = rederive(_evaluation_for_rederive(), terms)

    assert result == {
        "marker": REDERIVE_MISMATCH,
        "mismatches": [
            {
                "field": "term_snapshot",
                "rederived_value": None,
                "stored_value": None,
                "error": "ITEM_COST_TERM_SHAPE_INVALID: percentage_of_expected_sale_price has an invalid percent_value/fixed_amount_minor shape",
            }
        ],
    }


def test_rederive_malformed_purchase_snapshot_returns_integrity_marker() -> None:
    result = rederive(
        _evaluation_for_rederive(purchase_cost_minor=None),
        [
            ItemCostEvaluationTerm(
                workspace_id="ws_test",
                evaluation_id="ice_test",
                calculation_type=CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST,
                percent_value=None,
                fixed_amount_minor=None,
                amount_minor=1234,
                name="purchase allocation",
            )
        ],
    )

    assert result == {
        "marker": REDERIVE_MISMATCH,
        "mismatches": [
            {
                "field": "term_snapshot",
                "rederived_value": None,
                "stored_value": None,
                "error": "ITEM_COST_PURCHASE_COST_REQUIRED: purchase_cost_minor is required",
            }
        ],
    }


def test_rederive_reports_production_budget_mismatch_payload() -> None:
    result = rederive(
        _evaluation_for_rederive(production_budget_minor=2165),
        _valid_rederive_terms(),
    )

    assert result == {
        "marker": REDERIVE_MISMATCH,
        "mismatches": [
            {
                "field": "production_budget_minor",
                "rederived_value": 2166,
                "stored_value": 2165,
                "error": None,
            }
        ],
    }


def test_rederive_reports_allowed_worker_minutes_mismatch_payload() -> None:
    result = rederive(
        _evaluation_for_rederive(allowed_worker_minutes=Decimal("5.41")),
        _valid_rederive_terms(),
    )

    assert result == {
        "marker": REDERIVE_MISMATCH,
        "mismatches": [
            {
                "field": "allowed_worker_minutes",
                "rederived_value": Decimal("5.42"),
                "stored_value": Decimal("5.41"),
                "error": None,
            }
        ],
    }


def test_rederive_rate_mismatch_reports_rate_and_allowed_cascade_payload() -> None:
    result = rederive(
        _evaluation_for_rederive(
            cost_per_worker_minute_minor_snapshot=Decimal("399.5000")
        ),
        _valid_rederive_terms(),
    )

    assert result == {
        "marker": REDERIVE_MISMATCH,
        "mismatches": [
            {
                "field": "cost_per_worker_minute_minor_snapshot",
                "rederived_value": Decimal("400.0000"),
                "stored_value": Decimal("399.5000"),
                "error": None,
            },
            {
                "field": "allowed_worker_minutes",
                "rederived_value": Decimal("5.42"),
                "stored_value": Decimal("5.42"),
                "error": None,
            },
        ],
    }


def test_calculation_version_constant_and_docstring_pin_the_bump_lists() -> None:
    assert CALCULATION_VERSION == 1
    assert "§6A.10" in (calculator.__doc__ or "")
    assert "term formula" in (calculator.__doc__ or "").lower()
    assert "renames" in (calculator.__doc__ or "").lower()


def test_public_surface_is_exactly_the_registered_calculator_api() -> None:
    assert set(calculator.__all__) == {
        "CALCULATION_VERSION",
        "REDERIVE_SKIPPED",
        "REDERIVE_MISMATCH",
        "EvaluationSnapshot",
        "TermSnapshot",
        "calculate_percentage_term_amount",
        "calculate_term_amount",
        "calculate_term_amounts",
        "calculate_production_budget",
        "calculate_cost_per_worker_minute",
        "calculate_allowed_worker_minutes",
        "calculate_actual_worker_minutes",
        "calculate_consumed_cost_minor",
        "calculate_remaining_worker_minutes",
        "calculate_percent_consumed",
        "calculate_variance_worker_minutes",
        "calculate_variance_cost_minor",
        "validate_currency_equality",
        "rederive",
    }


def test_all_quantization_sites_ignore_ambient_rounding_and_precision() -> None:
    original_context = (getcontext().rounding, getcontext().prec)
    baseline = (
        calculate_percentage_term_amount(4900, Decimal("0.500")),
        calculate_cost_per_worker_minute(24_000_003, Decimal("1000.00"), Decimal("100.00")),
        calculate_allowed_worker_minutes(40_000_000, Decimal("400.0000")),
        calculate_actual_worker_minutes(100),
        calculate_consumed_cost_minor(60, Decimal("24.5000")),
        calculate_remaining_worker_minutes(Decimal("100000.00"), Decimal("0.33")),
        calculate_variance_worker_minutes(Decimal("100000.00"), Decimal("0.33")),
        calculate_percent_consumed(Decimal("0.01"), Decimal("100000.00")),
    )
    with localcontext() as ambient:
        ambient.rounding = ROUND_CEILING
        ambient.prec = 6
        assert (
            calculate_percentage_term_amount(4900, Decimal("0.500")),
            calculate_cost_per_worker_minute(24_000_003, Decimal("1000.00"), Decimal("100.00")),
            calculate_allowed_worker_minutes(40_000_000, Decimal("400.0000")),
            calculate_actual_worker_minutes(100),
            calculate_consumed_cost_minor(60, Decimal("24.5000")),
            calculate_remaining_worker_minutes(Decimal("100000.00"), Decimal("0.33")),
            calculate_variance_worker_minutes(Decimal("100000.00"), Decimal("0.33")),
            calculate_percent_consumed(Decimal("0.01"), Decimal("100000.00")),
        ) == baseline
    assert (getcontext().rounding, getcontext().prec) == original_context
