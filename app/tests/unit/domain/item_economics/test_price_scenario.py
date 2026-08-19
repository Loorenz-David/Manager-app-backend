import ast
import inspect
from decimal import Decimal
from fractions import Fraction

import pytest

from beyo_manager.domain.item_economics import price_scenario
from beyo_manager.domain.item_economics.calculator import (
    calculate_production_budget,
    calculate_term_amounts,
)
from beyo_manager.domain.item_economics.enums import CostModelTermCalculationTypeEnum
from beyo_manager.domain.item_economics.price_scenario import (
    SEARCH_CAP_MINOR,
    PriceModel,
    SliderDomain,
    allowance_seconds,
    allowed_centimin,
    break_even_price_minor,
    budget_minor,
    ceil_to_step,
    collapse_terms,
    digits,
    floor_to_step,
    infeasible_at_or_below_minor,
    round_half_even,
    slider_domain,
    two_significant_digits,
)
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.item_economics.cost_model_term import CostModelTerm


PERCENTAGE = CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE
FIXED = CostModelTermCalculationTypeEnum.FIXED_AMOUNT
PURCHASE = CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST
MOCKUP_MODEL = PriceModel(
    residual_percent_milli=22_000,
    constant_deduction_minor=0,
    cost_per_worker_minute_ten_thousandths=13_000_000,
)


def _term(
    calculation_type: CostModelTermCalculationTypeEnum,
    *,
    percent_value: Decimal | None = None,
    fixed_amount_minor: int | None = None,
    is_deleted: bool | None = None,
    name: str = "term",
) -> CostModelTerm:
    term = CostModelTerm(
        workspace_id="ws_test",
        cost_model_version_id="cmv_test",
        name=name,
        calculation_type=calculation_type,
        percent_value=percent_value,
        fixed_amount_minor=fixed_amount_minor,
        created_by_id="usr_test",
    )
    if is_deleted is not None:
        term.is_deleted = is_deleted
    return term


def _percent(value: str, *, name: str = "percentage") -> CostModelTerm:
    return _term(PERCENTAGE, percent_value=Decimal(value), name=name)


def _fixed(value: int, *, name: str = "fixed") -> CostModelTerm:
    return _term(FIXED, fixed_amount_minor=value, name=name)


def _purchase(*, name: str = "purchase") -> CostModelTerm:
    return _term(PURCHASE, name=name)


@pytest.mark.parametrize(
    ("numerator", "denominator", "expected"),
    [(3, 2, 2), (5, 2, 2), (7, 2, 4), (1, 2, 0)],
    ids=["tie-up-to-even", "tie-down-to-even", "odd-up", "odd-down"],
)
def test_c1_round_half_even_positive_operands(
    numerator: int,
    denominator: int,
    expected: int,
) -> None:
    assert round_half_even(numerator, denominator) == expected


@pytest.mark.parametrize(
    ("numerator", "denominator", "expected"),
    [(-3, 2, -2), (-5, 2, -2), (-1, 2, 0), (-7, 2, -4)],
    ids=["negative-up-to-even", "negative-down-to-even", "near-zero", "lower"],
)
def test_c2_round_half_even_negative_operands_use_floor_semantics(
    numerator: int,
    denominator: int,
    expected: int,
) -> None:
    assert round_half_even(numerator, denominator) == expected


def test_c3_price_percentage_rounding_reaches_a_half_even_tie() -> None:
    model = PriceModel(50_000, 0, 1_000_000)
    assert budget_minor(3, model) == 2
    assert budget_minor(5, model) == 2


def test_c3_rate_division_reaches_a_half_even_tie() -> None:
    model = PriceModel(100_000, 0, 2_000_000)
    assert allowed_centimin(5, model) == 2
    assert allowed_centimin(7, model) == 4


def test_c3_seconds_conversion_is_tie_free_and_matches_half_up() -> None:
    def half_up(numerator: int, denominator: int) -> int:
        return (numerator + denominator // 2) // denominator

    for centiminutes in range(1_001):
        numerator = centiminutes * 3
        assert (2 * (numerator % 5)) != 5
        assert round_half_even(numerator, 5) == half_up(numerator, 5)


@pytest.mark.parametrize(
    ("terms", "purchase_cost_minor", "expected"),
    [
        ([_percent("22.000")], None, (78_000, 0)),
        (
            [_percent("22.000", name="first"), _percent("10.000", name="second")],
            None,
            (68_000, 0),
        ),
        (
            [_percent("22.000", name="first"), _percent("22.000", name="second")],
            None,
            (56_000, 0),
        ),
        ([_percent("22.000"), _fixed(150_000)], None, (78_000, 150_000)),
        ([_percent("22.000"), _purchase()], 42_000, (78_000, 42_000)),
        (
            [_percent("60.000", name="first"), _percent("40.000", name="second")],
            None,
            (0, 0),
        ),
        (
            [_percent("60.000", name="first"), _percent("50.000", name="second")],
            None,
            (-10_000, 0),
        ),
    ],
    ids=[
        "one-percentage",
        "two-distinct-percentages",
        "two-equal-percentages",
        "percentage-and-fixed",
        "percentage-and-purchase",
        "percentages-sum-to-one-hundred",
        "percentages-sum-above-one-hundred",
    ],
)
def test_c4_collapse_terms_enumerates_model_shapes_with_real_orm_instances(
    terms: list[CostModelTerm],
    purchase_cost_minor: int | None,
    expected: tuple[int, int],
) -> None:
    assert collapse_terms(terms, purchase_cost_minor) == expected


def test_c5_percentage_scale_above_three_is_a_named_shape_error() -> None:
    with pytest.raises(
        ValidationError,
        match=r"^ITEM_COST_TERM_SHAPE_INVALID:",
    ):
        collapse_terms([_percent("22.0001")], None)


def test_c5_numerically_equal_percentage_scale_is_accepted() -> None:
    assert collapse_terms([_percent("22.0")], None) == (78_000, 0)


def test_c6_purchase_term_with_missing_purchase_cost_returns_none() -> None:
    assert collapse_terms([_purchase()], None) is None


def test_c6_purchase_cost_without_purchase_term_is_ignored() -> None:
    assert collapse_terms([_percent("22.000")], 99_999) == (78_000, 0)


def test_c6_shape_error_raises_while_missing_purchase_cost_returns_none() -> None:
    assert collapse_terms([_purchase()], None) is None
    with pytest.raises(ValidationError, match=r"^ITEM_COST_TERM_SHAPE_INVALID:"):
        collapse_terms([_percent("22.0001")], None)


def _assert_c7_bound(delta: int, percentage_term_count: int) -> None:
    assert 2 * abs(delta) <= percentage_term_count + 1


@pytest.mark.parametrize(
    ("terms", "price_minor", "purchase_cost_minor"),
    [
        ([_percent("1.001")], 250_000, None),
        (
            [_percent("12.345", name="first"), _percent("23.456", name="second")],
            12_345,
            None,
        ),
        (
            [_percent("22.000", name="first"), _percent("22.000", name="second")],
            12_345,
            None,
        ),
        (
            [
                _percent("22.000"),
                _fixed(150_000),
                _term(
                    PERCENTAGE,
                    percent_value=Decimal("5.000"),
                    is_deleted=True,
                    name="deleted",
                ),
            ],
            25,
            None,
        ),
        ([_percent("22.000"), _purchase()], 12_345, 4_200),
        (
            [_percent("60.000", name="first"), _percent("40.000", name="second")],
            12_345,
            None,
        ),
        (
            [_percent("60.000", name="first"), _percent("50.000", name="second")],
            12_345,
            None,
        ),
    ],
    ids=[
        "one-percentage-float-mutation",
        "two-distinct-percentages",
        "two-equal-percentages",
        "percentage-and-fixed-bound-attained",
        "percentage-and-purchase",
        "percentages-sum-to-one-hundred",
        "percentages-sum-above-one-hundred",
    ],
)
def test_c7_collapsed_budget_stays_within_the_integer_error_bound(
    terms: list[CostModelTerm],
    price_minor: int,
    purchase_cost_minor: int | None,
) -> None:
    active_terms = [term for term in terms if term.is_deleted is not True]
    collapsed = collapse_terms(terms, purchase_cost_minor)
    assert collapsed is not None
    model = PriceModel(*collapsed, cost_per_worker_minute_ten_thousandths=1)
    persisted = calculate_production_budget(
        price_minor,
        calculate_term_amounts(active_terms, price_minor, purchase_cost_minor),
    )
    delta = budget_minor(price_minor, model) - persisted
    percentage_term_count = sum(
        term.calculation_type is PERCENTAGE for term in active_terms
    )
    _assert_c7_bound(delta, percentage_term_count)


def test_c8_seconds_conversion_keeps_the_two_step_rounding() -> None:
    model = PriceModel(100_000, 0, 13_000_000)
    direct_shortcut = round_half_even(7 * 600_000, 13_000_000)
    assert direct_shortcut == 0
    assert allowance_seconds(7, model) == 1


def test_c9_break_even_is_the_smallest_price_reaching_the_target() -> None:
    result = break_even_price_minor(MOCKUP_MODEL, 12_300)
    assert result is not None
    assert allowance_seconds(result, MOCKUP_MODEL) >= 12_300
    assert allowance_seconds(result - 1, MOCKUP_MODEL) < 12_300


def test_c9_mockup_break_even_uses_the_exact_integer_search_literal() -> None:
    assert break_even_price_minor(MOCKUP_MODEL, 12_300) == 1_211_335


def test_c10_break_even_search_is_independent_of_the_slider_band() -> None:
    model = PriceModel(1, 0, 13_000_000)
    assert break_even_price_minor(model, 12_300) == 26_649_350_000


def test_c11_search_that_reaches_the_cap_returns_none() -> None:
    model = PriceModel(1, 0, 10**30)
    assert break_even_price_minor(model, 1) is None


def test_c12_fixed_deduction_boundary_and_domain_floor_are_exact() -> None:
    model = PriceModel(22_000, 150_000, 13_000_000)
    break_even = break_even_price_minor(model, 12_300)
    infeasible = infeasible_at_or_below_minor(model)
    assert break_even == 1_893_153
    assert infeasible == 681_847
    domain = slider_domain(break_even, 6, infeasible)
    assert domain is not None
    assert domain.min_minor == 702_000
    assert domain.min_minor > infeasible


def test_c12_degenerate_model_publishes_the_exact_infeasibility_cap() -> None:
    model = PriceModel(0, 0, 13_000_000)
    assert infeasible_at_or_below_minor(model) == SEARCH_CAP_MINOR == 2**40


def test_c12_purely_proportional_mockup_still_runs_the_search() -> None:
    assert infeasible_at_or_below_minor(MOCKUP_MODEL) == 29


def test_c13_non_positive_residual_has_no_break_even_or_domain() -> None:
    model = PriceModel(0, 0, 13_000_000)
    break_even = break_even_price_minor(model, 12_300)
    assert break_even is None
    assert slider_domain(break_even, 6, infeasible_at_or_below_minor(model)) is None


def test_c14_step_helpers_apply_directly_to_an_exact_rational() -> None:
    exact = Fraction(149_998, 5)
    assert floor_to_step(exact, 30_000) == 0
    assert floor_to_step(round(exact), 30_000) == 30_000
    assert ceil_to_step(exact, 30_000) == 30_000


@pytest.mark.parametrize(
    ("value", "expected"),
    [(7, 7), (42, 42), (423, 420), (4_237, 4_200)],
    ids=["one-digit", "two-digits", "three-digits", "four-digits"],
)
def test_c15_two_significant_digits_enumerates_integer_lengths(
    value: int,
    expected: int,
) -> None:
    assert two_significant_digits(value, 1) == expected


def test_c15_two_significant_digits_is_floored_at_one() -> None:
    assert two_significant_digits(1, 2) == 1


def test_c15_digits_zero_is_exposed_and_asserted_directly() -> None:
    assert digits(0) == 1


def test_c16_mockup_slider_domain_is_exact() -> None:
    assert slider_domain(1_211_335, 6, 29) == SliderDomain(
        step_minor=15_000,
        min_minor=420_000,
        max_minor=1_650_000,
    )


def test_c17_quantity_seven_slider_domain_uses_per_piece_derivation() -> None:
    domain = slider_domain(1_211_335, 7, 29)
    assert domain == SliderDomain(
        step_minor=15_400,
        min_minor=415_800,
        max_minor=1_647_800,
    )
    assert domain is not None
    assert domain.step_minor % 7 == 0
    assert domain.min_minor % domain.step_minor == 0
    assert domain.max_minor % domain.step_minor == 0


def test_quantity_zero_falls_back_to_a_divisor_of_one() -> None:
    assert slider_domain(1_211_335, 0, 29) == SliderDomain(
        step_minor=15_000,
        min_minor=420_000,
        max_minor=1_650_000,
    )
    assert slider_domain(1_211_335, 0, 29) == slider_domain(1_211_335, 1, 29)


def test_c18_minimum_resolves_disagreeing_floor_constraints() -> None:
    model = PriceModel(22_000, 150_000, 13_000_000)
    break_even = break_even_price_minor(model, 12_300)
    infeasible = infeasible_at_or_below_minor(model)
    domain = slider_domain(break_even, 6, infeasible)
    assert domain is not None
    assert floor_to_step(Fraction(35 * break_even, 100), domain.step_minor) == 655_200
    assert ceil_to_step(infeasible + 1, domain.step_minor) == 702_000
    assert domain.min_minor == 702_000
    assert domain.min_minor > infeasible
    assert domain.min_minor % domain.step_minor == 0


def test_c19_domain_is_none_when_the_minimum_reaches_the_maximum() -> None:
    assert slider_domain(1, 1, SEARCH_CAP_MINOR) is None


def test_c20_zero_typical_has_no_break_even_or_domain() -> None:
    break_even = break_even_price_minor(MOCKUP_MODEL, 0)
    assert break_even is None
    assert slider_domain(break_even, 6, 29) is None


def test_c21_module_has_no_direct_import_from_forbidden_boundaries() -> None:
    forbidden_prefixes = (
        "sqlalchemy",
        "beyo_manager.models",
        "beyo_manager.services",
    )
    tree = ast.parse(inspect.getsource(price_scenario))
    direct_imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            direct_imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            direct_imports.append(node.module)

    assert not [
        imported
        for imported in direct_imports
        if imported.startswith(forbidden_prefixes)
    ]
