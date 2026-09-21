"""Plan 7 — C2, C3, C4: `parse_stock_demand_body` (master plan §6.5; intention §8B
MC-8 demand entry defect table; §4A MC-3 invariant).

Pure unit tests: the parser never reaches a database (the fold's correction on
C2(w)). Each parametrized C2 id names its row letter (plan 7 note).
"""

import json

import pytest

from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.stock_report.stock_demand_request import (
    parse_stock_demand_body,
)

pytestmark = pytest.mark.unit

_VALID_ENTRY = {"itemCategory": "Dining Chairs", "properties": {}, "quantityRequested": 1}


def _body(entries) -> bytes:
    return json.dumps(entries).encode("utf-8")


def _assert_malformed(raw: bytes, *expected_fragments: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        parse_stock_demand_body(raw)
    assert excinfo.value.http_status == 422
    assert excinfo.value.message.startswith("Malformed request: ")
    for fragment in expected_fragments:
        assert fragment in excinfo.value.message


# ---------------------------------------------------------------------------
# C2 — demand entry defect table
# ---------------------------------------------------------------------------


def test_c2a_invalid_utf8_bytes():
    _assert_malformed(b"\xff\xfe")


def test_c2b_invalid_json():
    _assert_malformed(b"{not json")


def test_c2c_top_level_object_not_array():
    _assert_malformed(b"{}")


def test_c2d_empty_array():
    _assert_malformed(b"[]")


@pytest.mark.parametrize(
    "row_id, entries",
    [
        ("C2(e)", ["x"]),
        ("C2(f)", [1]),
        ("C2(g)", [None]),
        ("C2(h)", [[]]),
    ],
)
def test_c2_whole_entry_defects(row_id, entries):
    _assert_malformed(_body(entries), "entry 0", "must be an object")


@pytest.mark.parametrize(
    "row_id, entry",
    [
        ("C2(i)", {"properties": {}, "quantityRequested": 1}),
        ("C2(j)", {"itemCategory": 5, "properties": {}, "quantityRequested": 1}),
        ("C2(k)", {"itemCategory": "  ", "properties": {}, "quantityRequested": 1}),
    ],
)
def test_c2_item_category_defects(row_id, entry):
    _assert_malformed(_body([entry]), "entry 0")


@pytest.mark.parametrize(
    "row_id, entry",
    [
        ("C2(l)", {"itemCategory": "K", "quantityRequested": 1}),
        ("C2(m)", {"itemCategory": "K", "properties": None, "quantityRequested": 1}),
        ("C2(n)", {"itemCategory": "K", "properties": [], "quantityRequested": 1}),
        ("C2(o)", {"itemCategory": "K", "properties": "x", "quantityRequested": 1}),
        ("C2(p)", {"itemCategory": "K", "properties": 1, "quantityRequested": 1}),
        ("C2(q)", {"itemCategory": "K", "properties": True, "quantityRequested": 1}),
    ],
)
def test_c2_properties_defects(row_id, entry):
    _assert_malformed(_body([entry]), "entry 0")


@pytest.mark.parametrize(
    "row_id, entry",
    [
        ("C2(r)", {"itemCategory": "K", "properties": {}}),
        ("C2(s)", {"itemCategory": "K", "properties": {}, "quantityRequested": "5"}),
        ("C2(t)", {"itemCategory": "K", "properties": {}, "quantityRequested": 5.0}),
        ("C2(u)", {"itemCategory": "K", "properties": {}, "quantityRequested": True}),
        ("C2(v)", {"itemCategory": "K", "properties": {}, "quantityRequested": -1}),
    ],
)
def test_c2_quantity_requested_defects(row_id, entry):
    _assert_malformed(_body([entry]), "entry 0")


def test_c2w_quantity_requested_above_int32_max():
    _assert_malformed(
        _body([{"itemCategory": "K", "properties": {}, "quantityRequested": 2147483648}]),
        "entry 0",
    )


def test_c2x_names_every_offending_entry_and_nothing_else_applied():
    entries = [
        {"itemCategory": "", "properties": {}, "quantityRequested": 1},
        dict(_VALID_ENTRY),
        {"itemCategory": "K", "properties": {}, "quantityRequested": -1},
    ]
    with pytest.raises(ValidationError) as excinfo:
        parse_stock_demand_body(_body(entries))
    assert "entry 0" in excinfo.value.message
    assert "entry 2" in excinfo.value.message
    assert "entry 1" not in excinfo.value.message


def test_c2y_unknown_key_is_ignored():
    entries = [{**_VALID_ENTRY, "location": "LC1"}]
    parsed = parse_stock_demand_body(_body(entries))
    assert len(parsed) == 1
    assert parsed[0].item_category_raw == "Dining Chairs"


# ---------------------------------------------------------------------------
# C3 — duplicate-identity rule (MC-8 step 7)
# ---------------------------------------------------------------------------


def test_c3a_two_entries_same_category_same_properties_are_a_duplicate():
    entries = [dict(_VALID_ENTRY), dict(_VALID_ENTRY)]
    _assert_malformed(_body(entries), "entries 0 and 1")


def test_c3b_duplicate_after_normalization_of_properties():
    entries = [
        {"itemCategory": "K", "properties": {"wood_group": ["Teak", "Dark"]}, "quantityRequested": 1},
        {"itemCategory": "K", "properties": {"wood_group": ["dark", "teak"]}, "quantityRequested": 2},
    ]
    _assert_malformed(_body(entries), "entries 0 and 1")


def test_c3c_same_properties_different_categories_is_not_a_duplicate():
    entries = [
        {"itemCategory": "K", "properties": {}, "quantityRequested": 1},
        {"itemCategory": "K2", "properties": {}, "quantityRequested": 2},
    ]
    parsed = parse_stock_demand_body(_body(entries))
    assert len(parsed) == 2


def test_c3d_category_names_differing_only_in_case_are_a_duplicate():
    entries = [
        {"itemCategory": "Sofas", "properties": {}, "quantityRequested": 1},
        {"itemCategory": "sofas", "properties": {}, "quantityRequested": 2},
    ]
    _assert_malformed(_body(entries), "entries 0 and 1")


# ---------------------------------------------------------------------------
# C4 — MC-3 identity invariant, proven through the parser over real JSON bytes
# ---------------------------------------------------------------------------


def _signature_of(entries) -> str:
    parsed = parse_stock_demand_body(_body(entries))
    assert len(parsed) == 1
    return parsed[0].properties_signature


def test_c4a_key_order_does_not_affect_the_signature():
    a = _signature_of([{"itemCategory": "K", "properties": {"a": ["x"], "b": ["y"]}, "quantityRequested": 1}])
    b = _signature_of([{"itemCategory": "K", "properties": {"b": ["y"], "a": ["x"]}, "quantityRequested": 1}])
    assert a == b


def test_c4b_list_element_order_does_not_affect_the_signature():
    a = _signature_of([{"itemCategory": "K", "properties": {"wood_group": ["teak", "dark"]}, "quantityRequested": 1}])
    b = _signature_of([{"itemCategory": "K", "properties": {"wood_group": ["dark", "teak"]}, "quantityRequested": 1}])
    assert a == b


def test_c4c_list_element_case_and_whitespace_do_not_affect_the_signature():
    a = _signature_of([{"itemCategory": "K", "properties": {"wood_group": ["Teak"]}, "quantityRequested": 1}])
    b = _signature_of([{"itemCategory": "K", "properties": {"wood_group": [" teak "]}, "quantityRequested": 1}])
    assert a == b


def test_c4d_duplicate_list_elements_do_not_affect_the_signature():
    a = _signature_of([{"itemCategory": "K", "properties": {"wood_group": ["teak", "teak"]}, "quantityRequested": 1}])
    b = _signature_of([{"itemCategory": "K", "properties": {"wood_group": ["teak"]}, "quantityRequested": 1}])
    assert a == b


def test_c4e_bare_string_and_one_element_list_are_the_same_signature():
    a = _signature_of([{"itemCategory": "K", "properties": {"wood_group": "teak"}, "quantityRequested": 1}])
    b = _signature_of([{"itemCategory": "K", "properties": {"wood_group": ["teak"]}, "quantityRequested": 1}])
    assert a == b


def test_c4f_key_case_produces_two_rows():
    a = _signature_of([{"itemCategory": "K", "properties": {"Wood_Group": ["teak"]}, "quantityRequested": 1}])
    b = _signature_of([{"itemCategory": "K", "properties": {"wood_group": ["teak"]}, "quantityRequested": 1}])
    assert a != b


def test_c4g_key_whitespace_produces_two_rows():
    a = _signature_of([{"itemCategory": "K", "properties": {" wood_group": ["teak"]}, "quantityRequested": 1}])
    b = _signature_of([{"itemCategory": "K", "properties": {"wood_group": ["teak"]}, "quantityRequested": 1}])
    assert a != b


def test_c4h_not_understood_number_forms_produce_two_rows():
    a = _signature_of([{"itemCategory": "K", "properties": {"n": 1}, "quantityRequested": 1}])
    b = _signature_of([{"itemCategory": "K", "properties": {"n": 1.0}, "quantityRequested": 1}])
    assert a != b
    # cross-check against the domain function directly, so this row does not depend
    # only on inequality (which a broken signature could also produce by accident).
    assert a == compute_stock_criteria_signature({"n": 1})
    assert b == compute_stock_criteria_signature({"n": 1.0})
