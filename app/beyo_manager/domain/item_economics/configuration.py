"""Pure configuration-chain resolution rules for item economics."""

from __future__ import annotations

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
    """Classify the first configuration failure using the §7C.2 order.

    The caller supplies already-loaded rows.  This function performs no I/O and
    never chooses an arbitrary group when more than one active group exists.
    """
    if major_category is None:
        return CONFIGURATION_FAILURE_PRECEDENCE[0]

    active_groups = [
        group
        for group in groups
        if not getattr(group, "is_deleted", False)
        and getattr(group, "major_category", None) == major_category
    ]
    if not active_groups:
        return CONFIGURATION_FAILURE_PRECEDENCE[1]
    if len(active_groups) >= 2:
        return CONFIGURATION_FAILURE_PRECEDENCE[2]

    group_id = active_groups[0].client_id
    applicable_basis = [
        version
        for version in basis_versions
        if getattr(version, "production_cost_group_id", None) == group_id
        and is_applicable(version, on_date)
    ]
    if not applicable_basis:
        return CONFIGURATION_FAILURE_PRECEDENCE[3]

    if not any(is_applicable(version, on_date) for version in cost_model_versions):
        return CONFIGURATION_FAILURE_PRECEDENCE[4]
    return EconomicsStatusEnum.OK
