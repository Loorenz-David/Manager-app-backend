"""Pure arithmetic for the expected-sold-price scenario."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Iterable, Protocol

from beyo_manager.domain.item_economics.enums import CostModelTermCalculationTypeEnum
from beyo_manager.errors.validation import ValidationError


SEARCH_CAP_MINOR = 2**40
_PERCENT_SCALE = Decimal("0.001")


class CostModelTermInput(Protocol):
    calculation_type: CostModelTermCalculationTypeEnum
    percent_value: Decimal | None
    fixed_amount_minor: int | None
    is_deleted: bool | None


@dataclass(frozen=True)
class PriceModel:
    """Collapsed price-to-allowance inputs, all in their integer wire scales."""

    residual_percent_milli: int
    constant_deduction_minor: int
    cost_per_worker_minute_ten_thousandths: int
    budget_cap_percent_milli: int = 25_000


@dataclass(frozen=True)
class SliderDomain:
    step_minor: int
    min_minor: int
    max_minor: int


def round_half_even(a: int, b: int) -> int:
    """Return ``a / b`` rounded to the nearest integer, with ties to even."""

    if b <= 0:
        raise ValueError("b must be positive")
    quotient, remainder = divmod(a, b)
    twice_remainder = 2 * remainder
    if twice_remainder > b or (twice_remainder == b and quotient % 2 != 0):
        return quotient + 1
    return quotient


def _shape_error(calculation_type: object, field: str) -> ValidationError:
    # Deliberately duplicated at domain/item_economics/calculator.py:_shape_error.
    type_name = getattr(calculation_type, "value", calculation_type)
    return ValidationError(
        f"ITEM_COST_TERM_SHAPE_INVALID: {type_name} has an invalid {field} shape"
    )


def collapse_terms(
    terms: Iterable[CostModelTermInput],
    purchase_cost_minor: int | None,
) -> tuple[int, int] | None:
    """Collapse active cost terms into the affine display-model coefficients."""

    residual_percent_milli = 100_000
    constant_deduction_minor = 0

    for term in terms:
        if term.is_deleted is True:
            continue

        calculation_type = term.calculation_type
        if (
            calculation_type
            is CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE
        ):
            if term.percent_value is None or term.fixed_amount_minor is not None:
                raise _shape_error(calculation_type, "percent_value/fixed_amount_minor")
            if term.percent_value != term.percent_value.quantize(_PERCENT_SCALE):
                raise _shape_error(calculation_type, "percent_value scale")
            residual_percent_milli -= int(term.percent_value.scaleb(3))
        elif calculation_type is CostModelTermCalculationTypeEnum.FIXED_AMOUNT:
            if term.percent_value is not None or term.fixed_amount_minor is None:
                raise _shape_error(calculation_type, "percent_value/fixed_amount_minor")
            constant_deduction_minor += term.fixed_amount_minor
        elif calculation_type is CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST:
            if term.percent_value is not None or term.fixed_amount_minor is not None:
                raise _shape_error(calculation_type, "percent_value/fixed_amount_minor")
            if purchase_cost_minor is None:
                return None
            constant_deduction_minor += purchase_cost_minor
        else:
            raise _shape_error(calculation_type, "calculation_type")

    return residual_percent_milli, constant_deduction_minor


def budget_minor(price_minor: int, model: PriceModel) -> int:
    residual = (
        round_half_even(
            price_minor * model.residual_percent_milli,
            100_000,
        )
        - model.constant_deduction_minor
    )
    cap = round_half_even(
        price_minor * model.budget_cap_percent_milli,
        100_000,
    )
    return min(residual, cap)


def allowed_centimin(price_minor: int, model: PriceModel) -> int:
    return round_half_even(
        budget_minor(price_minor, model) * 1_000_000,
        model.cost_per_worker_minute_ten_thousandths,
    )


def allowance_seconds(price_minor: int, model: PriceModel) -> int:
    return round_half_even(allowed_centimin(price_minor, model) * 3, 5)


def _least_price_for_seconds(model: PriceModel, target_seconds: int) -> int | None:
    if allowance_seconds(0, model) >= target_seconds:
        return 0

    high = 1
    while high <= SEARCH_CAP_MINOR and allowance_seconds(high, model) < target_seconds:
        high *= 2
    if high > SEARCH_CAP_MINOR:
        return None

    low = 0
    while low + 1 < high:
        middle = (low + high) // 2
        if allowance_seconds(middle, model) >= target_seconds:
            high = middle
        else:
            low = middle
    return high


def break_even_price_minor(
    model: PriceModel,
    typical_total_seconds: int,
) -> int | None:
    if (
        model.residual_percent_milli <= 0
        or model.budget_cap_percent_milli <= 0
        or typical_total_seconds == 0
    ):
        return None
    return _least_price_for_seconds(model, typical_total_seconds)


def infeasible_at_or_below_minor(model: PriceModel) -> int:
    least_feasible = _least_price_for_seconds(model, 1)
    if least_feasible is None:
        return SEARCH_CAP_MINOR
    return least_feasible - 1


def floor_to_step(value: int | Fraction, step: int) -> int:
    if step <= 0:
        raise ValueError("step must be positive")
    exact_value = Fraction(value)
    return (exact_value // step) * step


def ceil_to_step(value: int | Fraction, step: int) -> int:
    if step <= 0:
        raise ValueError("step must be positive")
    exact_value = Fraction(value)
    return -((-exact_value) // step) * step


def digits(value: int) -> int:
    return 1 if value == 0 else len(str(abs(value)))


def two_significant_digits(a: int, b: int) -> int:
    if b <= 0:
        raise ValueError("b must be positive")
    integer_part = a // b
    scale = 10 ** max(0, digits(integer_part) - 2)
    return max(1, round_half_even(a, b * scale) * scale)


def slider_domain(
    break_even_minor: int | None,
    quantity: int,
    infeasible_minor: int,
) -> SliderDomain | None:
    if break_even_minor is None:
        return None

    # Intention §§2.7/9.4: storage has no quantity CHECK; legacy zero must
    # clamp to one before this value becomes a divisor.
    divisor = max(1, quantity)
    step_per_piece = two_significant_digits(
        break_even_minor,
        80 * divisor,
    )
    step_minor = divisor * step_per_piece
    raw_low = Fraction(35 * break_even_minor, 100)
    raw_high = Fraction(135 * break_even_minor, 100)
    min_minor = max(
        floor_to_step(raw_low, step_minor),
        ceil_to_step(infeasible_minor + 1, step_minor),
    )
    max_minor = ceil_to_step(raw_high, step_minor)
    if min_minor >= max_minor:
        return None
    return SliderDomain(
        step_minor=step_minor,
        min_minor=min_minor,
        max_minor=max_minor,
    )


__all__ = [
    "CostModelTermInput",
    "PriceModel",
    "SEARCH_CAP_MINOR",
    "SliderDomain",
    "allowance_seconds",
    "allowed_centimin",
    "break_even_price_minor",
    "budget_minor",
    "ceil_to_step",
    "collapse_terms",
    "digits",
    "floor_to_step",
    "infeasible_at_or_below_minor",
    "round_half_even",
    "slider_domain",
    "two_significant_digits",
]
