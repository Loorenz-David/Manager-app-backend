"""Unit contract for the phase-2 spec-to-item predicate boundary."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from sqlalchemy.dialects import postgresql

from beyo_manager.domain.item_economics.typical_filters import TypicalFilterSpec
from beyo_manager.domain.items.enums import ItemMajorCategoryEnum


def _build_item_match(spec: TypicalFilterSpec):
    try:
        module = importlib.import_module(
            "beyo_manager.services.queries.working_sections._typical_item_filter"
        )
    except ModuleNotFoundError:
        pytest.fail("build_item_match is missing")
    target = getattr(module, "build_item_match", None)
    assert callable(target), "build_item_match is missing"
    return target(spec)


def _compiled(predicate) -> str:
    assert predicate is not None
    return str(predicate.compile(dialect=postgresql.dialect()))


def test_build_item_match_returns_the_declared_tuple_for_empty_spec():
    result = _build_item_match(TypicalFilterSpec())

    assert result == (False, None)


@pytest.mark.parametrize(
    "spec",
    [
        TypicalFilterSpec(item_category_ids=frozenset({"chair"})),
        TypicalFilterSpec(major_categories=frozenset({ItemMajorCategoryEnum.SEAT})),
        TypicalFilterSpec(width_cm=(60, 80)),
        TypicalFilterSpec(height_cm=(60, 80)),
        TypicalFilterSpec(depth_cm=(60, 80)),
        TypicalFilterSpec(can_have_upholstery=False),
        TypicalFilterSpec(designers=frozenset({"Aalto"})),
        TypicalFilterSpec(width_cm=(None, None)),
        TypicalFilterSpec(
            item_category_ids=frozenset({"chair", "stool"}), width_cm=(60, 80)
        ),
    ],
    ids=["category", "major-category", "width", "height", "depth", "upholstery-false", "designer", "recorded-width", "and-fields"],
)
def test_narrowing_spec_returns_a_predicate_and_coalesces_unknowns(spec):
    needs_category_join, predicate = _build_item_match(spec)

    assert needs_category_join is (spec.major_categories is not None)
    assert "coalesce" in _compiled(predicate).lower()


def test_recorded_dimension_range_requires_a_non_null_dimension():
    _needs_join, predicate = _build_item_match(TypicalFilterSpec(width_cm=(None, None)))

    assert "width_in_cm IS NOT NULL" in _compiled(predicate)


def test_spec_index_has_no_fingerprint_or_digest_path():
    root = Path(__file__).parents[5]
    source = "\n".join(
        [
            (root / "beyo_manager/services/queries/working_sections/_typical_item_filter.py").read_text(),
            (root / "beyo_manager/services/queries/working_sections/get_working_section_typical_times.py").read_text(),
        ]
    ).lower()
    for term in ("hashlib", "sha1", "sha256", "md5", "fingerprint", "digest"):
        assert term not in source
