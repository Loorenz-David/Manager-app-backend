"""Pure configuration-chain resolution rules for item economics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from beyo_manager.domain.item_economics.enums import EconomicsStatusEnum
from beyo_manager.domain.items.enums import ItemMajorCategoryEnum


# This is deliberately independent of EconomicsStatusEnum declaration order.
CONFIGURATION_FAILURE_PRECEDENCE = (
    EconomicsStatusEnum.ITEM_MISSING_MAJOR_CATEGORY,
    EconomicsStatusEnum.NOT_CONFIGURED_NO_COST_GROUP,
    EconomicsStatusEnum.NOT_CONFIGURED_AMBIGUOUS_COST_GROUP,
    EconomicsStatusEnum.NOT_CONFIGURED_NO_BASIS_VERSION,
    EconomicsStatusEnum.NOT_CONFIGURED_NO_COST_MODEL_VERSION,
)


@dataclass(frozen=True)
class EconomicsSelection:
    """The selected configuration rows and the first configuration failure."""

    status: EconomicsStatusEnum
    selected_group: object | None
    basis_version: object | None
    cost_model_version: object | None


ITEM_READINESS_PRECEDENCE = (
    EconomicsStatusEnum.ITEM_UNVALUED,
    EconomicsStatusEnum.ITEM_MISSING_EXPECTED_PRICE,
    EconomicsStatusEnum.ITEM_MISSING_PURCHASE_COST,
    EconomicsStatusEnum.CURRENCY_MISMATCH,
    EconomicsStatusEnum.NOT_EVALUATED,
)


def resolve_major_category(snapshot: str | None) -> ItemMajorCategoryEnum | None:
    """Resolve an item snapshot only when it contains a known category value."""
    if snapshot is None:
        return None
    try:
        return ItemMajorCategoryEnum(snapshot)
    except (TypeError, ValueError):
        return None


def is_applicable(version: object, on_date: date) -> bool:
    """Return whether a persisted version covers ``on_date``."""
    if getattr(version, "is_deleted", False):
        return False
    effective_from = getattr(version, "effective_from", None)
    effective_to = getattr(version, "effective_to", None)
    return (
        (effective_from is None or effective_from <= on_date)
        and (effective_to is None or effective_to > on_date)
    )


def resolve_economics_configuration(
    major_category: ItemMajorCategoryEnum | None,
    groups: Iterable[object],
    basis_versions: Iterable[object],
    cost_model_versions: Iterable[object],
    on_date: date,
) -> EconomicsStatusEnum:
    return resolve_economics_selection(
        major_category,
        groups,
        basis_versions,
        cost_model_versions,
        on_date,
    ).status


def resolve_economics_selection(
    major_category: ItemMajorCategoryEnum | None,
    groups: Iterable[object],
    basis_versions: Iterable[object],
    cost_model_versions: Iterable[object],
    on_date: date,
) -> EconomicsSelection:
    """Select the category's group, basis and applicable model without I/O."""
    group_rows = list(groups)
    basis_rows = list(basis_versions)
    model_rows = list(cost_model_versions)

    if major_category is None:
        return EconomicsSelection(CONFIGURATION_FAILURE_PRECEDENCE[0], None, None, None)

    active_groups = [
        group
        for group in group_rows
        if not getattr(group, "is_deleted", False)
        and getattr(group, "major_category", None) == major_category
    ]
    if not active_groups:
        return EconomicsSelection(CONFIGURATION_FAILURE_PRECEDENCE[1], None, None, None)
    if len(active_groups) >= 2:
        return EconomicsSelection(CONFIGURATION_FAILURE_PRECEDENCE[2], None, None, None)

    selected_group = active_groups[0]
    group_id = selected_group.client_id
    applicable_basis = [
        version
        for version in basis_rows
        if getattr(version, "production_cost_group_id", None) == group_id
        and is_applicable(version, on_date)
    ]
    if not applicable_basis:
        return EconomicsSelection(CONFIGURATION_FAILURE_PRECEDENCE[3], selected_group, None, None)

    selected_basis = applicable_basis[0]
    applicable_models = [version for version in model_rows if is_applicable(version, on_date)]
    if not applicable_models:
        return EconomicsSelection(CONFIGURATION_FAILURE_PRECEDENCE[4], selected_group, selected_basis, None)
    return EconomicsSelection(
        EconomicsStatusEnum.OK,
        selected_group,
        selected_basis,
        applicable_models[0],
    )


def resolve_item_economics_status(
    valuation: object | None,
    selection: EconomicsSelection,
    model_terms: Iterable[object],
) -> EconomicsStatusEnum:
    """Resolve item readiness after configuration selection using explicit precedence."""
    if selection.status is not EconomicsStatusEnum.OK:
        return selection.status

    terms = list(model_terms)
    has_purchase_term = any(
        getattr(getattr(term, "calculation_type", None), "value", getattr(term, "calculation_type", None))
        == "item_purchase_cost"
        for term in terms
    )
    checks = {
        EconomicsStatusEnum.ITEM_UNVALUED: valuation is None,
        EconomicsStatusEnum.ITEM_MISSING_EXPECTED_PRICE: (
            valuation is not None and getattr(valuation, "expected_sale_price_minor", None) is None
        ),
        EconomicsStatusEnum.ITEM_MISSING_PURCHASE_COST: (
            valuation is not None
            and has_purchase_term
            and getattr(valuation, "purchase_cost_minor", None) is None
        ),
        EconomicsStatusEnum.CURRENCY_MISMATCH: (
            valuation is not None
            and selection.basis_version is not None
            and selection.cost_model_version is not None
            and (
                getattr(valuation, "currency", None) != getattr(selection.basis_version, "currency", None)
                or getattr(selection.basis_version, "currency", None)
                != getattr(selection.cost_model_version, "currency", None)
            )
        ),
        EconomicsStatusEnum.NOT_EVALUATED: True,
    }
    for status in ITEM_READINESS_PRECEDENCE:
        if checks[status]:
            return status
    raise AssertionError("ITEM_READINESS_PRECEDENCE must include a terminal status")
