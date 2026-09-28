from types import SimpleNamespace
import pytest
from beyo_manager.domain.stock_report.criteria_matcher import (
    build_item_property_bag,
    evaluate_stock_criteria,
    matches_stock_criteria,
    serialize_criterion_failure,
)
from beyo_manager.domain.stock_report.enums import StockCriteriaMismatchReasonEnum
from beyo_manager.models.tables.items.item import Item


def item(properties=None, quantity=1):
    return SimpleNamespace(properties=properties, quantity=quantity)


@pytest.mark.unit
def test_matcher_derives_groups_and_uses_scanner_token_rules():
    subject = item(
        {"wood_type": "Elm", "drawers_qty": "4", "upholstery": "Up & Down"}, 4
    )
    assert matches_stock_criteria(
        subject,
        {
            "wood_group": ["light"],
            "drawers_range": ["3-5"],
            "upholstery": ["up & down"],
        },
    )


@pytest.mark.unit
def test_matcher_reports_all_sorted_failures():
    failures = evaluate_stock_criteria(
        item({}, 1), {"wood_group": ["dark"], "upholstery": ["x"], "quantity": ["2"]}
    )
    assert [(f.key, f.reason) for f in failures] == [
        ("quantity", StockCriteriaMismatchReasonEnum.VALUE_NOT_ACCEPTED),
        ("upholstery", StockCriteriaMismatchReasonEnum.MISSING_ON_ITEM),
        ("wood_group", StockCriteriaMismatchReasonEnum.MISSING_ON_ITEM),
    ]
    assert [serialize_criterion_failure(failure) for failure in failures] == [
        {
            "key": "quantity",
            "reason": "value_not_accepted",
            "accepted_values": ["2"],
            "item_values": ["1"],
        },
        {
            "key": "upholstery",
            "reason": "missing_on_item",
            "accepted_values": ["x"],
            "item_values": [],
        },
        {
            "key": "wood_group",
            "reason": "missing_on_item",
            "accepted_values": ["dark"],
            "item_values": [],
        },
    ]


@pytest.mark.unit
def test_empty_list_is_not_a_wildcard():
    failures = evaluate_stock_criteria(item({"upholstery": "blue"}), {"upholstery": []})
    assert len(failures) == 1
    assert (
        failures[0].reason is StockCriteriaMismatchReasonEnum.CRITERION_NOT_UNDERSTOOD
    )
    assert serialize_criterion_failure(failures[0]) == {
        "key": "upholstery",
        "reason": "criterion_not_understood",
        "accepted_values": [],
        "item_values": ["blue"],
    }


@pytest.mark.unit
def test_known_source_without_derived_group_reports_no_group():
    failure = evaluate_stock_criteria(
        item({"wood_type": "Other"}), {"wood_group": ["dark"]}
    )[0]
    assert failure.reason is StockCriteriaMismatchReasonEnum.NO_GROUP_FOR_VALUE
    assert serialize_criterion_failure(failure) == {
        "key": "wood_group",
        "reason": "no_group_for_value",
        "accepted_values": ["dark"],
        "item_values": ["other"],
    }


@pytest.mark.unit
def test_plain_rosewood_derives_the_dark_group():
    assert matches_stock_criteria(
        item({"wood_type": "Rosewood"}), {"wood_group": ["dark"]}
    )
    failure = evaluate_stock_criteria(
        item({"wood_type": "Rosewood"}), {"wood_group": ["light"]}
    )[0]
    assert failure.reason is StockCriteriaMismatchReasonEnum.VALUE_NOT_ACCEPTED
    assert failure.item_values == ("dark",)


@pytest.mark.unit
def test_matcher_failure_values_use_normalized_tokens_for_derived_and_raw_criteria():
    failures = evaluate_stock_criteria(
        item(
            {"wood_type": "Teak, Oak", "upholstery": "Down/Feather", "drawers_qty": "0"}
        ),
        {
            "drawers_range": ["3-5"],
            "upholstery": ["foam"],
            "wood_group": ["light"],
        },
    )
    assert [serialize_criterion_failure(failure) for failure in failures] == [
        {
            "key": "drawers_range",
            "reason": "no_group_for_value",
            "accepted_values": ["3-5"],
            "item_values": ["0"],
        },
        {
            "key": "upholstery",
            "reason": "value_not_accepted",
            "accepted_values": ["foam"],
            "item_values": ["down", "feather"],
        },
        {
            "key": "wood_group",
            "reason": "value_not_accepted",
            "accepted_values": ["light"],
            "item_values": ["teak"],
        },
    ]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("properties", "quantity", "expected"),
    [
        ({"k": "Teak"}, 4, {"k": "Teak", "quantity": "4"}),
        ({"k": True}, 4, {"k": "true", "quantity": "4"}),
        ({"k": False}, 4, {"k": "false", "quantity": "4"}),
        ({"k": 4}, 4, {"k": "4", "quantity": "4"}),
        ({"k": 4.0}, 4, {"k": "4", "quantity": "4"}),
        ({"k": 4.5}, 4, {"k": "4.5", "quantity": "4"}),
        ({"k": None}, 4, {"quantity": "4"}),
        ({"k": ["a", "b"]}, 4, {"k": '["a","b"]', "quantity": "4"}),
        ({"k": {"é": 1}}, 4, {"k": '{"é":1}', "quantity": "4"}),
        (
            {" wood_type ": " Teak "},
            4,
            {"wood_type": "Teak", "wood_group": "Teak", "quantity": "4"},
        ),
        ({" a": "first", "a": "second"}, 4, {"a": "second", "quantity": "4"}),
        (
            {"qty_extensions": "x", "shape": "Oval"},
            4,
            {"shape": "Oval", "quantity": "4"},
        ),
        ({"quantity": "9"}, 4, {"quantity": "4"}),
        (
            {"wood_group": "Dark", "wood_type": "Oak"},
            4,
            {"wood_type": "Oak", "wood_group": "Light", "quantity": "4"},
        ),
        (
            {"drawers_range": "6+", "drawers_qty": "2"},
            4,
            {"drawers_qty": "2", "drawers_range": "1-2", "quantity": "4"},
        ),
        (None, 4, {"quantity": "4"}),
    ],
)
def test_build_item_property_bag_scanner_table(properties, quantity, expected):
    assert build_item_property_bag(item(properties, quantity)) == expected


@pytest.mark.unit
def test_build_item_property_bag_drops_blank_values():
    assert build_item_property_bag(item({"blank": "   "}, 1)) == {"quantity": "1"}
    assert build_item_property_bag(item({"   ": "x"}, 1)) == {"quantity": "1"}


@pytest.mark.unit
def test_build_item_property_bag_discards_stored_derived_keys_without_sources():
    assert build_item_property_bag(
        item({"wood_group": "Dark", "drawers_range": "6+"}, 1)
    ) == {"quantity": "1"}


@pytest.mark.unit
@pytest.mark.parametrize(
    ("drawers", "expected"),
    [
        ("1", "1-2"),
        ("2", "1-2"),
        ("3", "3-5"),
        ("5", "3-5"),
        ("6", "6+"),
        ("0", None),
        ("4.0", None),
        ("abc", None),
        (4, "3-5"),
        ("٤", None),
        (" 6 ", "6+"),
    ],
)
def test_drawer_range_derivation_table(drawers, expected):
    bag = build_item_property_bag(item({"drawers_qty": drawers}, 1))
    assert bag.get("drawers_range") == expected


@pytest.mark.unit
def test_wildcard_and_token_matching_table():
    assert (
        evaluate_stock_criteria(item({"wood_type": "Elm"}), {"wood_type": None}) == []
    )
    assert (
        evaluate_stock_criteria(
            item({"shape": "Oval/Rectangular"}), {"shape": ["oval"]}
        )
        == []
    )
    assert (
        evaluate_stock_criteria(
            item({"upholstery": "Up & Down"}), {"upholstery": ["up & down"]}
        )
        == []
    )
    assert (
        evaluate_stock_criteria(
            item({"upholstery": "Up & Down"}), {"upholstery": ["up"]}
        )[0].reason
        is StockCriteriaMismatchReasonEnum.VALUE_NOT_ACCEPTED
    )
    assert (
        evaluate_stock_criteria(item({"shape": ", /"}), {"shape": ["oval"]})[0].reason
        is StockCriteriaMismatchReasonEnum.MISSING_ON_ITEM
    )
    assert (
        evaluate_stock_criteria(item({"wood_type": "Other"}), {"wood_group": None})[
            0
        ].reason
        is StockCriteriaMismatchReasonEnum.NO_GROUP_FOR_VALUE
    )
    assert (
        evaluate_stock_criteria(item({"shape": "Oval"}), {"drawers_range": ["3-5"]})[
            0
        ].reason
        is StockCriteriaMismatchReasonEnum.MISSING_ON_ITEM
    )
    assert evaluate_stock_criteria(item(None), {}) == []


@pytest.mark.unit
def test_matcher_accepts_an_unflushed_manager_item_instance():
    manager_item = Item(
        properties={"wood_type": "Teak", "upholstery": "Down"}, quantity=4
    )
    assert matches_stock_criteria(
        manager_item,
        {"wood_group": ["teak"], "upholstery": ["down"], "quantity": ["4"]},
    )


@pytest.mark.unit
def test_matcher_accepts_any_of_multiple_criterion_values_and_rejects_a_miss():
    subject = item({"wood_type": "Teak"}, 4)
    assert evaluate_stock_criteria(subject, {"wood_group": ["dark", "teak"]}) == []
    failures = evaluate_stock_criteria(subject, {"wood_group": ["dark", "light"]})
    assert [(failure.key, failure.reason) for failure in failures] == [
        ("wood_group", StockCriteriaMismatchReasonEnum.VALUE_NOT_ACCEPTED)
    ]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("case", "properties", "quantity", "criteria", "expected_failures"),
    [
        (
            "H9-oval",
            {"wood_type": "Oak", "shape": "Oval"},
            1,
            {"shape": ["oval"], "wood_group": ["light"]},
            [],
        ),
        ("H1", {"wood_type": "Walnut"}, 4, {"wood_group": ["dark"]}, []),
        ("H2", {"wood_type": "Elm, Beech"}, 1, {"wood_group": ["light"]}, []),
        ("H3-teak", {"wood_type": "Teak, Oak"}, 1, {"wood_group": ["teak"]}, []),
        (
            "H3-light",
            {"wood_type": "Teak, Oak"},
            1,
            {"wood_group": ["light"]},
            [("wood_group", StockCriteriaMismatchReasonEnum.VALUE_NOT_ACCEPTED)],
        ),
        (
            "H4",
            {"wood_type": "Teak", "upholstery": "Down"},
            4,
            {"quantity": ["4"], "upholstery": ["down"], "wood_group": ["teak"]},
            [],
        ),
        (
            "H4prime",
            {"wood_type": "Teak"},
            4,
            {"quantity": ["4"], "upholstery": ["down"], "wood_group": ["teak"]},
            [("upholstery", StockCriteriaMismatchReasonEnum.MISSING_ON_ITEM)],
        ),
        (
            "H5",
            {"wood_type": "Oak", "upholstery": "Up & Down"},
            4,
            {"quantity": ["4"], "upholstery": ["up & down"], "wood_group": ["light"]},
            [],
        ),
        (
            "H6",
            {"wood_type": "Teak", "upholstery": "Up & Down"},
            8,
            {"quantity": ["8"], "upholstery": ["up & down"], "wood_group": ["teak"]},
            [],
        ),
        (
            "H7",
            {"wood_type": "Teak, Beech", "upholstery": "Down"},
            2,
            {"quantity": ["4"], "upholstery": ["down"], "wood_group": ["teak"]},
            [("quantity", StockCriteriaMismatchReasonEnum.VALUE_NOT_ACCEPTED)],
        ),
        (
            "H8",
            {},
            1,
            {"quantity": ["4"], "upholstery": ["down"], "wood_group": ["teak"]},
            [
                ("quantity", StockCriteriaMismatchReasonEnum.VALUE_NOT_ACCEPTED),
                ("upholstery", StockCriteriaMismatchReasonEnum.MISSING_ON_ITEM),
                ("wood_group", StockCriteriaMismatchReasonEnum.MISSING_ON_ITEM),
            ],
        ),
        (
            "H9",
            {"wood_type": "Oak", "shape": "Oval/Rectangular"},
            1,
            {"shape": ["oval"], "wood_group": ["light"]},
            [],
        ),
        (
            "H10",
            {"wood_type": "Santos Rosewood", "shape": "Round"},
            1,
            {"shape": ["round"], "wood_group": ["dark"]},
            [],
        ),
        ("H11-present", {"wood_type": "Elm"}, 1, {"wood_type": None}, []),
        (
            "H11-absent",
            {},
            1,
            {"wood_type": None},
            [("wood_type", StockCriteriaMismatchReasonEnum.MISSING_ON_ITEM)],
        ),
        (
            "H12",
            {"wood_type": "Other"},
            1,
            {"wood_group": ["dark"]},
            [("wood_group", StockCriteriaMismatchReasonEnum.NO_GROUP_FOR_VALUE)],
        ),
        ("H13", {"drawers_qty": 4}, 1, {"drawers_range": ["3-5"]}, []),
        (
            "H14-zero",
            {"drawers_qty": "0"},
            1,
            {"drawers_range": ["3-5"]},
            [("drawers_range", StockCriteriaMismatchReasonEnum.NO_GROUP_FOR_VALUE)],
        ),
        (
            "H14-float-string",
            {"drawers_qty": "4.0"},
            1,
            {"drawers_range": ["3-5"]},
            [("drawers_range", StockCriteriaMismatchReasonEnum.NO_GROUP_FOR_VALUE)],
        ),
        ("H14-float", {"drawers_qty": 4.0}, 1, {"drawers_range": ["3-5"]}, []),
        (
            "H15",
            {},
            1,
            {"wood_group": []},
            [("wood_group", StockCriteriaMismatchReasonEnum.CRITERION_NOT_UNDERSTOOD)],
        ),
        ("H16", None, 4, {"quantity": ["4"]}, []),
    ],
)
def test_scanner_hand_walk_golden_cases(
    case, properties, quantity, criteria, expected_failures
):
    subject = Item(properties=properties, quantity=quantity)
    failures = evaluate_stock_criteria(subject, criteria)
    assert [(failure.key, failure.reason) for failure in failures] == expected_failures
    assert matches_stock_criteria(subject, criteria) is (not expected_failures)
