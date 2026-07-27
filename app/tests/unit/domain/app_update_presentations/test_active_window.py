from datetime import datetime, timedelta, timezone

import pytest

from beyo_manager.domain.app_update_presentations.active_window import (
    is_within_active_window,
)

NOW = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)


@pytest.mark.unit
def test_null_bounds_are_always_active():
    assert is_within_active_window(None, None, NOW) is True


@pytest.mark.unit
def test_future_start_is_inactive():
    assert is_within_active_window(NOW + timedelta(hours=1), None, NOW) is False


@pytest.mark.unit
def test_past_expiry_is_inactive():
    assert is_within_active_window(None, NOW - timedelta(seconds=1), NOW) is False


@pytest.mark.unit
def test_start_boundary_is_inclusive():
    assert is_within_active_window(NOW, None, NOW) is True


@pytest.mark.unit
def test_expiry_boundary_is_exclusive():
    assert is_within_active_window(None, NOW, NOW) is False


@pytest.mark.unit
def test_inside_window_is_active():
    assert is_within_active_window(
        NOW - timedelta(hours=1), NOW + timedelta(hours=1), NOW
    ) is True
