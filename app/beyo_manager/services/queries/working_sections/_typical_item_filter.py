"""Translate a canonical typical-time spec into the item-query predicate."""

from __future__ import annotations

from sqlalchemy import and_, false, func
from sqlalchemy.sql.elements import ColumnElement

from beyo_manager.domain.item_economics.typical_filters import TypicalFilterSpec
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory


def _range_predicate(column: ColumnElement, bounds: tuple[int | None, int | None]) -> ColumnElement[bool]:
    minimum, maximum = bounds
    conditions: list[ColumnElement[bool]] = [column.is_not(None)]
    if minimum is not None:
        conditions.append(column >= minimum)
    if maximum is not None:
        conditions.append(column <= maximum)
    return and_(*conditions)


def build_item_match(spec: TypicalFilterSpec) -> tuple[bool, ColumnElement[bool] | None]:
    """Return whether a category join is needed and a NULL-safe item predicate.

    An unbounded range ``(None, None)`` deliberately means that the dimension is
    recorded.  Its explicit ``IS NOT NULL`` conjunct is therefore load-bearing.
    """
    if not spec.is_narrowing:
        return False, None

    conditions: list[ColumnElement[bool]] = []
    if spec.item_category_ids is not None:
        conditions.append(Item.item_category_id.in_(spec.item_category_ids))
    if spec.major_categories is not None:
        conditions.append(ItemCategory.major_category.in_(spec.major_categories))
    if spec.width_cm is not None:
        conditions.append(_range_predicate(Item.width_in_cm, spec.width_cm))
    if spec.height_cm is not None:
        conditions.append(_range_predicate(Item.height_in_cm, spec.height_cm))
    if spec.depth_cm is not None:
        conditions.append(_range_predicate(Item.depth_in_cm, spec.depth_cm))
    if spec.can_have_upholstery is not None:
        conditions.append(Item.can_have_upholstery.is_(spec.can_have_upholstery))
    if spec.designers is not None:
        conditions.append(Item.designer.in_(spec.designers))

    predicate = func.coalesce(and_(*conditions), false())
    return spec.major_categories is not None, predicate


def build_item_properties_match(spec: TypicalFilterSpec) -> ColumnElement[bool] | None:
    """NULL-safe predicate for the most specific tier: the spec's item match AND the same signature.

    Mirrors the domain rule that a signature only refines an already-narrowing
    spec — a signature without narrowing dimensions yields no predicate.
    """
    if not spec.is_narrowing or spec.properties_signature is None:
        return None
    _, predicate = build_item_match(spec)
    return func.coalesce(
        and_(predicate, Item.properties_signature == spec.properties_signature), false()
    )


def build_item_facet_matches(spec: TypicalFilterSpec) -> list[ColumnElement[bool]]:
    """NULL-safe predicates for the spec's facet rungs, in ladder priority order.

    Each rung is the spec's item match AND JSONB containment of the facet's
    key/value pairs, so a history item qualifies whenever its snapshot carries
    those pairs — whatever else it carries. Facets ride only beside a
    signature (the spec enforces that), so a signature-less spec yields [].
    """
    if not spec.is_narrowing or not spec.properties_facets:
        return []
    _, predicate = build_item_match(spec)
    return [
        func.coalesce(and_(predicate, Item.properties.contains(facet.match_values())), false())
        for facet in spec.properties_facets
    ]


__all__ = ["build_item_facet_matches", "build_item_match", "build_item_properties_match"]
