"""Pure, canonical item-economics calculations.

This module is the sole owner of the formulas in intention §6A.  The
``CALCULATION_VERSION`` contract in §6A.10 must be bumped when a Q1–Q5
target or rounding mode, term formula, budget/allowance/consumption/variance
formula, currency rule, or §8A.1 bucket policy changes.  It must not be bumped
for renames, value-preserving storage widening, API shape, or documentation.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from typing import Iterable, Protocol, Sequence, TypeVar, cast

from beyo_manager.domain.item_economics.enums import CostModelTermCalculationTypeEnum
from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.errors.validation import ValidationError


CALCULATION_VERSION: int = 1
"""§6A.10: bump for formula, term-set, rounding, currency, or bucket changes;
never bump for renames, value-preserving storage widening, API shape, or docs.
"""

# D4: a version mismatch is an intentional skip, not a failed re-derivation.
REDERIVE_SKIPPED = "rederive_skipped_calculation_version"
REDERIVE_MISMATCH = "rederive_mismatch"

__all__ = [
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
]

_T = TypeVar("_T")
_DECIMAL_ZERO = Decimal("0")


class EvaluationSnapshot(Protocol):
    expected_sale_price_minor: int
    purchase_cost_minor: int | None
    monthly_paid_hours_snapshot: Decimal
    planning_utilization_percent_snapshot: Decimal
    fixed_monthly_cost_minor_snapshot: int
    cost_per_worker_minute_minor_snapshot: Decimal
    production_budget_minor: int
    allowed_worker_minutes: Decimal
    calculation_version: int


class TermSnapshot(Protocol):
    name: str
    calculation_type: CostModelTermCalculationTypeEnum
    percent_value: Decimal | None
    fixed_amount_minor: int | None
    amount_minor: int


def _type_error(field: str, expected: str, value: object) -> TypeError:
    return TypeError(f"{field} must be {expected}; received {type(value).__name__}")


def _guard_type(
    value: object,
    field: str,
    expected: type[object],
    expected_label: str,
    *,
    exact: bool = False,
) -> object:
    """Shared C6 entry guard; ``exact`` rejects bool for int inputs."""
    valid = type(value) is expected if exact else isinstance(value, expected)
    if not valid:
        raise _type_error(field, expected_label, value)
    return value


def _require_money(value: int | None, field: str, *, required_identity: str | None = None) -> int:
    if value is None:
        if required_identity is not None:
            raise ValidationError(f"{required_identity}: {field} is required")
        raise _type_error(field, "an int in minor units", value)
    return cast(
        int,
        _guard_type(value, field, int, "an int in minor units", exact=True),
    )


def _require_seconds(value: int, field: str = "actual_worker_seconds") -> int:
    return cast(int, _guard_type(value, field, int, "an int", exact=True))


def _require_rate(value: Decimal | None, field: str, *, required: bool = True) -> Decimal:
    if value is None:
        if required:
            raise _type_error(field, "a Decimal", value)
        return value
    return cast(Decimal, _guard_type(value, field, Decimal, "a Decimal"))


def _require_enum(value: object, enum_type: type[_T], field: str) -> _T:
    return cast(
        _T,
        _guard_type(value, field, enum_type, f"a {enum_type.__name__} member"),
    )


def _shape_error(calculation_type: object, field: str) -> ValidationError:
    # Deliberately duplicated at domain/item_economics/price_scenario.py:_shape_error.
    type_name = getattr(calculation_type, "value", calculation_type)
    return ValidationError(
        f"ITEM_COST_TERM_SHAPE_INVALID: {type_name} has an invalid {field} shape"
    )


def _term_shape(
    calculation_type: CostModelTermCalculationTypeEnum,
    percent_value: Decimal | None,
    fixed_amount_minor: int | None,
) -> None:
    """Validate the total type/presence contract before any arithmetic."""
    if percent_value is not None:
        _require_rate(percent_value, "percent_value")
    if fixed_amount_minor is not None:
        _require_money(fixed_amount_minor, "fixed_amount_minor")

    if calculation_type is CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE:
        if percent_value is None or fixed_amount_minor is not None:
            raise _shape_error(calculation_type, "percent_value/fixed_amount_minor")
    elif calculation_type is CostModelTermCalculationTypeEnum.FIXED_AMOUNT:
        if percent_value is not None or fixed_amount_minor is None:
            raise _shape_error(calculation_type, "percent_value/fixed_amount_minor")
    elif calculation_type is CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST:
        if percent_value is not None or fixed_amount_minor is not None:
            raise _shape_error(calculation_type, "percent_value/fixed_amount_minor")
    else:  # protected by _require_enum, retained for exhaustiveness.
        raise _shape_error(calculation_type, "calculation_type")

    if percent_value is not None and percent_value < _DECIMAL_ZERO:
        raise _shape_error(calculation_type, "percent_value")
    if fixed_amount_minor is not None and fixed_amount_minor < 0:
        raise _shape_error(calculation_type, "fixed_amount_minor")


def calculate_percentage_term_amount(
    expected_sale_price_minor: int,
    percent_value: Decimal,
) -> int:
    """Calculate Q1, the gross-price planning allocation in minor units."""
    price = _require_money(
        expected_sale_price_minor,
        "expected_sale_price_minor",
        required_identity="ITEM_COST_EXPECTED_PRICE_REQUIRED",
    )
    percent = _require_rate(percent_value, "percent_value")
    with localcontext() as context:
        context.prec = 50
        raw_amount = Decimal(price) * percent / Decimal(100)
        quantized_amount = raw_amount.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
        return int(quantized_amount)


def calculate_term_amount(
    calculation_type: CostModelTermCalculationTypeEnum,
    expected_sale_price_minor: int,
    percent_value: Decimal | None,
    fixed_amount_minor: int | None,
    purchase_cost_minor: int | None,
) -> int:
    """Calculate one snapshot term amount under §6A.4."""
    term_type = _require_enum(
        calculation_type,
        CostModelTermCalculationTypeEnum,
        "calculation_type",
    )
    price = _require_money(
        expected_sale_price_minor,
        "expected_sale_price_minor",
        required_identity="ITEM_COST_EXPECTED_PRICE_REQUIRED",
    )
    _term_shape(term_type, percent_value, fixed_amount_minor)

    if term_type is CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE:
        assert percent_value is not None
        return calculate_percentage_term_amount(price, percent_value)
    if term_type is CostModelTermCalculationTypeEnum.FIXED_AMOUNT:
        assert fixed_amount_minor is not None
        return fixed_amount_minor

    purchase_cost = _require_money(
        purchase_cost_minor,
        "purchase_cost_minor",
        required_identity="ITEM_COST_PURCHASE_COST_REQUIRED",
    )
    return purchase_cost


def calculate_term_amounts(
    term_rows: Sequence[TermSnapshot],
    expected_sale_price_minor: int,
    purchase_cost_minor: int | None,
) -> list[int]:
    """Calculate all snapshot term amounts and reject duplicate purchase terms."""
    amounts: list[int] = []
    purchase_term_count = 0
    for term_row in term_rows:
        term_type = _require_enum(
            term_row.calculation_type,
            CostModelTermCalculationTypeEnum,
            "calculation_type",
        )
        if term_type is CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST:
            purchase_term_count += 1
        amounts.append(
            calculate_term_amount(
                term_type,
                expected_sale_price_minor,
                term_row.percent_value,
                term_row.fixed_amount_minor,
                purchase_cost_minor,
            )
        )
    if purchase_term_count > 1:
        raise ValidationError(
            "ITEM_COST_TERM_SHAPE_INVALID: duplicate item_purchase_cost terms"
        )
    return amounts


def calculate_production_budget(
    expected_sale_price_minor: int,
    term_amounts: Iterable[int],
) -> int:
    """Calculate the exact integer budget from the snapshot term amounts."""
    price = _require_money(
        expected_sale_price_minor,
        "expected_sale_price_minor",
        required_identity="ITEM_COST_EXPECTED_PRICE_REQUIRED",
    )
    checked_amounts: list[int] = []
    for amount in term_amounts:
        checked_amounts.append(_require_money(amount, "amount_minor"))
    return price - sum(checked_amounts)


def calculate_cost_per_worker_minute(
    fixed_monthly_cost_minor: int,
    monthly_paid_hours: Decimal,
    planning_utilization_percent: Decimal,
) -> Decimal:
    """Calculate Q2, the persisted rate in minor units per worker-minute."""
    fixed_cost = _require_money(fixed_monthly_cost_minor, "fixed_monthly_cost_minor")
    hours = _require_rate(monthly_paid_hours, "monthly_paid_hours")
    utilization = _require_rate(
        planning_utilization_percent,
        "planning_utilization_percent",
    )
    with localcontext() as context:
        context.prec = 50
        denominator = hours * utilization / Decimal(100) * Decimal(60)
        raw_rate = Decimal(fixed_cost) / denominator
        quantized_rate = raw_rate.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
        if quantized_rate == _DECIMAL_ZERO:
            raise ValidationError(
                "ITEM_COST_RATE_UNDERFLOW: quantized cost per worker-minute is zero"
            )
        return quantized_rate


def calculate_allowed_worker_minutes(
    production_budget_minor: int,
    cost_per_worker_minute_minor: Decimal,
) -> Decimal:
    """Calculate Q3 from the persisted, already-quantized rate."""
    budget = _require_money(production_budget_minor, "production_budget_minor")
    rate = _require_rate(cost_per_worker_minute_minor, "cost_per_worker_minute_minor")
    if rate == _DECIMAL_ZERO:
        raise ValidationError(
            "ITEM_COST_RATE_UNDERFLOW: cannot calculate allowance with zero rate"
        )
    with localcontext() as context:
        context.prec = 50
        raw_allowance = Decimal(budget) / rate
        return raw_allowance.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def calculate_actual_worker_minutes(actual_worker_seconds: int) -> Decimal:
    """Calculate Q4 from actual seconds."""
    seconds = _require_seconds(actual_worker_seconds)
    with localcontext() as context:
        context.prec = 50
        raw_minutes = Decimal(seconds) / Decimal(60)
        return raw_minutes.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def calculate_consumed_cost_minor(
    actual_worker_seconds: int,
    cost_per_worker_minute_minor_snapshot: Decimal,
) -> int:
    """Calculate Q5 directly from seconds and the evaluation rate snapshot."""
    seconds = _require_seconds(actual_worker_seconds)
    rate = _require_rate(
        cost_per_worker_minute_minor_snapshot,
        "cost_per_worker_minute_minor_snapshot",
    )
    with localcontext() as context:
        context.prec = 50
        raw_cost = Decimal(seconds) / Decimal(60) * rate
        quantized_cost = raw_cost.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
        return int(quantized_cost)


def calculate_remaining_worker_minutes(
    allowed_worker_minutes: Decimal,
    actual_worker_minutes: Decimal,
) -> Decimal:
    """Subtract two already-quantized minute values exactly."""
    allowed = _require_rate(allowed_worker_minutes, "allowed_worker_minutes")
    actual = _require_rate(actual_worker_minutes, "actual_worker_minutes")
    with localcontext() as context:
        context.prec = 50
        return allowed - actual


def calculate_percent_consumed(
    allowed_worker_minutes: Decimal,
    actual_worker_minutes: Decimal,
) -> Decimal | None:
    """Return Q6's display percentage, or null for an infeasible allowance."""
    allowed = _require_rate(allowed_worker_minutes, "allowed_worker_minutes")
    actual = _require_rate(actual_worker_minutes, "actual_worker_minutes")
    if allowed <= _DECIMAL_ZERO:
        return None
    with localcontext() as context:
        context.prec = 50
        raw_percent = actual / allowed * Decimal(100)
        return raw_percent.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def calculate_variance_worker_minutes(
    allowed_worker_minutes: Decimal,
    actual_worker_minutes: Decimal,
) -> Decimal:
    """Calculate the exact two-decimal worker-minute variance."""
    with localcontext() as context:
        context.prec = 50
        return calculate_remaining_worker_minutes(allowed_worker_minutes, actual_worker_minutes)


def calculate_variance_cost_minor(
    production_budget_minor: int,
    consumed_cost_minor: int,
) -> int:
    """Calculate the independent integer money variance."""
    budget = _require_money(production_budget_minor, "production_budget_minor")
    consumed = _require_money(consumed_cost_minor, "consumed_cost_minor")
    return budget - consumed


def validate_currency_equality(
    valuation_currency: ItemCurrencyEnum,
    basis_currency: ItemCurrencyEnum,
    model_currency: ItemCurrencyEnum,
) -> None:
    """Enforce the three-way currency equality from §6A.9."""
    valuation = _require_enum(valuation_currency, ItemCurrencyEnum, "valuation_currency")
    basis = _require_enum(basis_currency, ItemCurrencyEnum, "basis_currency")
    model = _require_enum(model_currency, ItemCurrencyEnum, "model_currency")
    pairs = (
        (valuation, basis, "valuation", "basis"),
        (valuation, model, "valuation", "model"),
        (basis, model, "basis", "model"),
    )
    mismatches = [
            f"{left_name}={left.value} differs from {right_name}={right.value}"
        for left, right, left_name, right_name in pairs
        if left != right
    ]
    if mismatches:
        raise ValidationError("ITEM_COST_CURRENCY_MISMATCH: " + "; ".join(mismatches))


def rederive(
    evaluation_row: EvaluationSnapshot,
    term_rows: Sequence[TermSnapshot],
) -> tuple[Decimal, int, Decimal] | str | dict[str, object]:
    """Reproduce the HC-7 closed-set values without dereferencing any FK.

    A row from a future calculation version returns ``REDERIVE_SKIPPED`` before
    reading any other field.  A same-version snapshot that no longer agrees
    with its stored derived values returns a ``REDERIVE_MISMATCH`` marker and
    the disagreeing fields.
    """
    def marker(
        mismatches: list[dict[str, object]],
        field: str,
        error: Exception,
        *,
        stored_value: object = None,
        rederived_value: object = None,
    ) -> dict[str, object]:
        mismatches.append(
            {
                "field": field,
                "rederived_value": rederived_value,
                "stored_value": stored_value,
                "error": str(error),
            }
        )
        return {"marker": REDERIVE_MISMATCH, "mismatches": mismatches}

    mismatches: list[dict[str, object]] = []
    try:
        version = evaluation_row.calculation_version
        if type(version) is not int:
            raise _type_error("calculation_version", "an int", version)
    except (AttributeError, TypeError, ValidationError, ArithmeticError) as error:
        return marker(mismatches, "evaluation_snapshot", error)
    if version != CALCULATION_VERSION:
        return REDERIVE_SKIPPED

    try:
        rate = calculate_cost_per_worker_minute(
            evaluation_row.fixed_monthly_cost_minor_snapshot,
            evaluation_row.monthly_paid_hours_snapshot,
            evaluation_row.planning_utilization_percent_snapshot,
        )
        stored_rate = _require_rate(
            evaluation_row.cost_per_worker_minute_minor_snapshot,
            "cost_per_worker_minute_minor_snapshot",
        )
    except (AttributeError, TypeError, ValidationError, ArithmeticError) as error:
        return marker(mismatches, "evaluation_snapshot", error)
    if rate != stored_rate:
        mismatches.append(
            {
                "field": "cost_per_worker_minute_minor_snapshot",
                "rederived_value": rate,
                "stored_value": stored_rate,
                "error": None,
            }
        )

    try:
        expected_price = _require_money(
            evaluation_row.expected_sale_price_minor,
            "expected_sale_price_minor",
            required_identity="ITEM_COST_EXPECTED_PRICE_REQUIRED",
        )
    except (AttributeError, TypeError, ValidationError, ArithmeticError) as error:
        return marker(mismatches, "evaluation_snapshot", error)

    try:
        amounts = calculate_term_amounts(
            term_rows,
            expected_price,
            evaluation_row.purchase_cost_minor,
        )
    except (AttributeError, TypeError, ValidationError, ArithmeticError) as error:
        if str(error).startswith("ITEM_COST_PURCHASE_COST_REQUIRED:"):
            return marker(mismatches, "term_snapshot", error)
        if str(error).startswith("ITEM_COST_TERM_SHAPE_INVALID:"):
            return marker(mismatches, "term_snapshot", error)
        return marker(mismatches, "term_snapshot", error)
    for term_row, amount in zip(term_rows, amounts):
        try:
            stored_amount = _require_money(term_row.amount_minor, "amount_minor")
        except (AttributeError, TypeError, ValidationError, ArithmeticError) as error:
            return marker(mismatches, "term_snapshot", error)
        if amount != stored_amount:
            mismatches.append(
                {
                    "field": f"term[{term_row.name}].amount_minor",
                    "rederived_value": amount,
                    "stored_value": stored_amount,
                    "error": None,
                }
            )

    try:
        budget = calculate_production_budget(expected_price, amounts)
        stored_budget_value = evaluation_row.production_budget_minor
        stored_budget = _require_money(stored_budget_value, "production_budget_minor")
    except (AttributeError, TypeError, ValidationError, ArithmeticError) as error:
        return marker(mismatches, "evaluation_snapshot", error)
    if budget != stored_budget:
        mismatches.append(
            {
                "field": "production_budget_minor",
                "rederived_value": budget,
                "stored_value": stored_budget,
                "error": None,
            }
        )
    stored_allowed_value: object = None
    try:
        stored_allowed_value = evaluation_row.allowed_worker_minutes
        stored_allowed = _require_rate(
            stored_allowed_value,
            "allowed_worker_minutes",
        )
    except (AttributeError, TypeError, ValidationError, ArithmeticError) as error:
        if rate != stored_rate:
            return marker(
                mismatches,
                "allowed_worker_minutes",
                error,
                stored_value=stored_allowed_value,
            )
        return marker(mismatches, "evaluation_snapshot", error)

    try:
        allowed = calculate_allowed_worker_minutes(budget, stored_rate)
    except (AttributeError, TypeError, ValidationError, ArithmeticError) as error:
        return marker(
            mismatches,
            "allowed_worker_minutes",
            error,
            stored_value=stored_allowed,
        )
    if allowed != stored_allowed or rate != stored_rate:
        mismatches.append(
            {
                "field": "allowed_worker_minutes",
                "rederived_value": allowed,
                "stored_value": stored_allowed,
                "error": None,
            }
        )
    if mismatches:
        return {"marker": REDERIVE_MISMATCH, "mismatches": mismatches}
    return rate, budget, allowed
