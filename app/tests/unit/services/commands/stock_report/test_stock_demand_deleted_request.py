"""Plan 13A — `parse_stock_demand_deleted_body` (master plan §6.5; intention §8B
MC-8, §14E E2/U7).

The delete webhook's body parser: the demand entry rules for `itemCategory` and
`properties`, **`quantityRequested` ignored as an unknown key**, every defect
collected before raising, duplicates by `(item_category_key, properties_signature)`.

Rows exercised here are the ones whose whole outcome is the 422 (C1(d)–C1(h)) plus
the parse half of C1(i). C1(j) and C1(k) also assert that no live row was touched,
so they live in the integration file with the command.
"""

from __future__ import annotations

import json

import pytest

from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
    normalize_stock_criteria,
)
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.stock_report.stock_demand_deleted_request import (
    parse_stock_demand_deleted_body,
)

pytestmark = pytest.mark.unit

_ARRAY_MESSAGE = "body must be a JSON array with at least one entry"


def _body(payload) -> bytes:
    return json.dumps(payload).encode("utf-8")


def test_c1d_an_empty_array_is_refused(  # C1(d)
):
    """C1(d): `b"[]"` → 422. The mutant drops the `len(payload) == 0` term, which
    makes an empty array parse to zero entries and the request answer 200."""
    with pytest.raises(ValidationError) as excinfo:
        parse_stock_demand_deleted_body(b"[]")
    assert _ARRAY_MESSAGE in str(excinfo.value)


def test_c1e_one_entry_sent_unwrapped_is_refused_as_a_shape_defect():
    """C1(e): a **non-empty** JSON object where an array is required — the realistic
    sender mistake.

    The assertion names the *shape* message, not merely the 422: dropping the
    `isinstance(payload, list)` term makes the object iterate as its key list, and
    every key is a `str`, so the entry loop produces per-entry defects and a 422
    comes back either way. Asserting which 422 is what makes the term load-bearing
    (reported as a plan-cell correction: the cell predicted a 200).
    """
    raw = b'{"itemCategory": "Dining Chairs", "properties": {"wood_group": ["teak"]}}'
    with pytest.raises(ValidationError) as excinfo:
        parse_stock_demand_deleted_body(raw)
    assert _ARRAY_MESSAGE in str(excinfo.value)


def test_c1f_an_entry_without_properties_is_refused():
    """C1(f): a missing `properties` key is a defect, never a default `{}`."""
    with pytest.raises(ValidationError) as excinfo:
        parse_stock_demand_deleted_body(_body([{"itemCategory": "Dining Chairs"}]))
    assert "entry 0: properties must be an object" in str(excinfo.value)


def test_c1g_properties_null_is_refused():
    """C1(g): explicit `null` is not an object and is not treated as `{}`."""
    with pytest.raises(ValidationError) as excinfo:
        parse_stock_demand_deleted_body(
            _body([{"itemCategory": "Dining Chairs", "properties": None}])
        )
    assert "entry 0: properties must be an object" in str(excinfo.value)


def test_c1h_a_blank_item_category_is_refused():
    """C1(h): `"  "` is blank. Dropping `.strip()` lets it through the shape, and the
    request then answers 200 `category_not_found` instead of 422."""
    with pytest.raises(ValidationError) as excinfo:
        parse_stock_demand_deleted_body(
            _body([{"itemCategory": "  ", "properties": {"wood_group": ["teak"]}}])
        )
    assert "entry 0: itemCategory must be a non-blank string" in str(excinfo.value)


def test_c1i_quantity_requested_is_ignored_and_the_entry_shape_is_the_registered_one():
    """C1(i), parse half (§14E E2/U7, Scanner v2 §4A.1 "sent anyway, it is ignored"),
    and master plan §9 rule 18 — the registered `DemandDeleteEntry` shape pinned at
    its own boundary: `DemandEntry` **without** `quantity_requested`.
    """
    raw_properties = {"wood_group": ["teak"]}
    entries = parse_stock_demand_deleted_body(
        _body(
            [
                {
                    "itemCategory": " Dining Chairs ",
                    "properties": raw_properties,
                    "quantityRequested": 5,
                    "somethingElse": {"nested": True},
                }
            ]
        )
    )

    assert len(entries) == 1
    entry = entries[0]
    assert entry.index == 0
    assert entry.item_category_raw == " Dining Chairs "
    assert entry.item_category_key == "dining chairs"
    assert entry.properties_raw == raw_properties
    assert entry.properties_normalized == normalize_stock_criteria(raw_properties)
    assert entry.properties_signature == compute_stock_criteria_signature(
        raw_properties
    )
    assert not hasattr(entry, "quantity_requested")
