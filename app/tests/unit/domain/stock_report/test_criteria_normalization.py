import hashlib
import json
import pytest
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
    normalize_stock_criteria,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ({"k": None}, {"k": None}),
        ({"k": "  Teak "}, {"k": ["teak"]}),
        ({"k": ""}, {"k": ""}),
        ({"k": "  "}, {"k": "  "}),
        ({"k": ["Teak", "Dark", " teak "]}, {"k": ["dark", "teak"]}),
        ({"k": ["", "  "]}, {"k": ["", "  "]}),
        ({"k": ["Teak", 1]}, {"k": ["Teak", 1]}),
        ({"k": []}, {"k": []}),
        ({"k": 1}, {"k": 1}),
        ({"k": 1.0}, {"k": 1.0}),
        ({"k": True}, {"k": True}),
        ({"k": {"a": 1}}, {"k": {"a": 1}}),
        ({"k": "Straße"}, {"k": ["straße"]}),
    ],
)
def test_normalization_value_table(raw, expected):
    assert normalize_stock_criteria(raw) == expected


@pytest.mark.unit
def test_normalization_preserves_keys_and_is_idempotent():
    raw = {"Wood_Type": ["x"], "wood_type": ["x"], " wood_type": ["x"]}
    assert set(normalize_stock_criteria(raw)) == set(raw)
    assert normalize_stock_criteria(
        normalize_stock_criteria(raw)
    ) == normalize_stock_criteria(raw)


@pytest.mark.unit
def test_normalization_preserves_string_property_key_spelling():
    assert normalize_stock_criteria({"Wood_Type": "Teak", " wood_type": "Oak"}) == {
        "Wood_Type": ["teak"],
        " wood_type": ["oak"],
    }


@pytest.mark.unit
def test_signature_uses_normalized_golden_vector():
    expected = {"k": ["dark", "teak"]}
    assert (
        compute_stock_criteria_signature({"k": ["Teak", " dark "]})
        == hashlib.sha256(
            json.dumps(
                expected, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
        ).hexdigest()
    )


@pytest.mark.unit
def test_signature_separates_ununderstood_values_but_sorts_object_keys():
    assert compute_stock_criteria_signature(
        {"k": 1}
    ) != compute_stock_criteria_signature({"k": 1.0})
    assert compute_stock_criteria_signature(
        {"k": True}
    ) != compute_stock_criteria_signature({"k": 1})
    assert compute_stock_criteria_signature(
        {"k": [1, 2]}
    ) != compute_stock_criteria_signature({"k": [2, 1]})
    assert compute_stock_criteria_signature(
        {"a": {"x": 1, "y": 2}}
    ) == compute_stock_criteria_signature({"a": {"y": 2, "x": 1}})
