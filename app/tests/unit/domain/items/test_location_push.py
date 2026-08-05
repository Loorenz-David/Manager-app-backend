import pytest

from beyo_manager.domain.items.location_push import (
    has_zone_changed,
    needs_fixing_for_task_type,
    normalize_zone,
)
from beyo_manager.domain.tasks.enums import TaskTypeEnum


@pytest.mark.unit
@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, ""), ("", ""), ("   ", ""), (" Shelf A ", "Shelf A")],
)
def test_normalize_zone_strips_to_a_comparable_value(value, expected):
    assert normalize_zone(value) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        ("Shelf A", "Shelf A", False),
        ("Shelf A", "  Shelf A  ", False),
        (None, "", False),
        ("   ", None, False),
        ("Shelf A", "Shelf B", True),
        (None, "Shelf A", True),
        ("Shelf A", None, True),
    ],
)
def test_has_zone_changed_ignores_whitespace_only_differences(old, new, expected):
    assert has_zone_changed(old, new) is expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("task_type", "expected"),
    [
        (TaskTypeEnum.RETURN, True),
        (TaskTypeEnum.PRE_ORDER, False),
        (TaskTypeEnum.INTERNAL, False),
        (None, False),
    ],
)
def test_needs_fixing_only_for_return_tasks(task_type, expected):
    assert needs_fixing_for_task_type(task_type) is expected
