"""Pure helpers for item upholstery selection and deferred requirement behavior."""

from decimal import Decimal

from beyo_manager.domain.items.enums import ItemUpholsterySourceEnum


def has_positive_amount_meters(amount_meters: Decimal | None) -> bool:
    return amount_meters is not None and amount_meters > Decimal("0")


def is_internal_selection_missing(
    source: ItemUpholsterySourceEnum,
    upholstery_id: str | None,
) -> bool:
    return source == ItemUpholsterySourceEnum.INTERNAL and upholstery_id is None


def is_deferred_internal_upholstery(
    source: ItemUpholsterySourceEnum,
    upholstery_id: str | None,
    amount_meters: Decimal | None,
) -> bool:
    return is_internal_selection_missing(source, upholstery_id) and has_positive_amount_meters(amount_meters)


def should_defer_requirement_creation(
    source: ItemUpholsterySourceEnum,
    upholstery_id: str | None,
    amount_meters: Decimal | None,
) -> bool:
    return is_deferred_internal_upholstery(source, upholstery_id, amount_meters)
