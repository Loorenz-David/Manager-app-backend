import pytest

from beyo_manager.domain.app_update_presentations.slide_order import (
    assert_contiguous_sequence,
    resequenced_orders,
)
from beyo_manager.domain.app_update_presentations.versioning import next_version_number
from beyo_manager.errors.validation import ValidationError


@pytest.mark.unit
def test_next_version_number():
    assert next_version_number([]) == 1
    assert next_version_number([1]) == 2
    assert next_version_number([1, 2, 5]) == 6


@pytest.mark.unit
def test_resequenced_orders_is_contiguous_by_position():
    assert resequenced_orders(["b", "a", "c"]) == {"b": 1, "a": 2, "c": 3}


@pytest.mark.unit
def test_resequenced_orders_rejects_duplicates():
    with pytest.raises(ValidationError):
        resequenced_orders(["a", "a"])


@pytest.mark.unit
def test_assert_contiguous_sequence():
    assert_contiguous_sequence([1, 2, 3])
    assert_contiguous_sequence([3, 1, 2])  # order-independent


@pytest.mark.unit
@pytest.mark.parametrize("bad", [[1, 3], [0, 1, 2], [1, 1, 2], [2, 3]])
def test_assert_contiguous_sequence_rejects_gaps(bad):
    with pytest.raises(ValidationError):
        assert_contiguous_sequence(bad)
