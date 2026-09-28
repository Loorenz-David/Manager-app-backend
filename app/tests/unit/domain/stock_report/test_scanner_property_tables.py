import pytest
from beyo_manager.domain.stock_report.scanner_property_tables import (
    DRAWER_RANGES,
    WOOD_GROUPS,
    drawer_range_of,
    validate_drawer_ranges,
    validate_wood_groups,
)


@pytest.mark.unit
def test_scanner_tables_and_drawer_ascii_rules():
    assert WOOD_GROUPS == {
        "Dark": [
            "Mahogany",
            "Santos Rosewood",
            "Rosewood",
            "Dark Oak",
            "Dark Teak",
            "Walnut",
        ],
        "Teak": ["Teak", "Cherry"],
        "Light": ["Oak", "Beech", "Pine", "Birch", "Elm"],
    }
    assert DRAWER_RANGES == [("1-2", 1, 2), ("3-5", 3, 5), ("6+", 6, None)]
    assert drawer_range_of("4") == "3-5"
    assert drawer_range_of("٤") is None


@pytest.mark.unit
def test_scanner_table_validators_reject_ambiguous_definitions():
    with pytest.raises(ValueError):
        validate_wood_groups({"A": ["Oak"], "B": ["oak"]})
    with pytest.raises(ValueError):
        validate_wood_groups({"A/B": ["Oak"]})
    with pytest.raises(ValueError):
        validate_drawer_ranges([("1-3", 1, 3), ("3-5", 3, 5)])
    with pytest.raises(ValueError):
        validate_drawer_ranges([("4-2", 4, 2)])
