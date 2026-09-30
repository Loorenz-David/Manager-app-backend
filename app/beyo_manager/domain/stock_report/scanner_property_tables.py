from __future__ import annotations
import re

WOOD_TYPE_KEY = "wood_type"
WOOD_GROUP_KEY = "wood_group"
DRAWERS_QTY_KEY = "drawers_qty"
DRAWERS_RANGE_KEY = "drawers_range"
EXCLUDED_ITEM_PROPERTY_KEYS = frozenset(
    {"qty_extensions", "quantity", "wood_group", "drawers_range"}
)
SCANNER_SOURCE_COMMIT = "0d80bf2"
SCANNER_SOURCE_READ_ON = "2026-09-18"
WOOD_GROUPS = {
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
DRAWER_RANGES = [("1-2", 1, 2), ("3-5", 3, 5), ("6+", 6, None)]
# Manager-side, not read from Scanner: item spellings that mean a Scanner criterion
# value, per property key. Lower-case tokens on both sides.
ITEM_VALUE_ALIASES = {
    "shape": {"squared": "square"},
}
# Manager-side, not read from Scanner: item keys that stand in for a Scanner key the
# item does not carry itself, in order of preference. The purchase app stores some
# categories' wood as `material_type`. The Scanner key always wins when present.
ITEM_KEY_ALIASES = {
    WOOD_TYPE_KEY: ("material_type",),
}


def validate_wood_groups(groups) -> None:
    seen = set()
    for name, values in groups.items():
        if "," in name or "/" in name:
            raise ValueError("group names cannot contain criterion separators")
        for value in values:
            token = value.strip().lower()
            if token in seen:
                raise ValueError("wood token appears in more than one group")
            seen.add(token)


def validate_drawer_ranges(ranges) -> None:
    previous_max = None
    for _label, minimum, maximum in ranges:
        if maximum is not None and maximum < minimum:
            raise ValueError("invalid drawer range")
        if previous_max is not None and minimum <= previous_max:
            raise ValueError("drawer ranges overlap or are unordered")
        previous_max = maximum


def wood_group_of_token(token: str) -> str | None:
    normalized = token.strip().lower()
    for group, values in WOOD_GROUPS.items():
        if normalized in {value.lower() for value in values}:
            return group
    return None


def canonical_item_token(key: str, token: str) -> str:
    return ITEM_VALUE_ALIASES.get(key, {}).get(token, token)


def drawer_range_of(stored: str) -> str | None:
    value = stored.strip()
    if not re.fullmatch(r"[0-9]+", value):
        return None
    number = int(value)
    for label, minimum, maximum in DRAWER_RANGES:
        if number >= minimum and (maximum is None or number <= maximum):
            return label
    return None


validate_wood_groups(WOOD_GROUPS)
validate_drawer_ranges(DRAWER_RANGES)
