"""The pure snapshot rules (`domain/stock_report/snapshot_rules.py`, 2026-09-26)."""

from types import SimpleNamespace

import pytest

from beyo_manager.domain.stock_report.enums import StockReportPriorityEnum as P
from beyo_manager.domain.stock_report.snapshot_rules import (
    PROGRESS_KEYS,
    empty_version_progress,
    fold_version_progress,
    is_snapshot_active,
    merge_priority_orders,
    missing_quantity_ceiling,
    outstanding_quantity,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("requested", "counters", "expected"),
    [
        (10, (0, 0, 0, 0), 10),
        (10, (2, 3, 1, 0), 4),
        (10, (4, 4, 2, 0), 0),
        # Covered beyond the frozen demand (Scanner raised it since): never negative.
        (10, (6, 6, 0, 0), 0),
        (0, (0, 0, 0, 0), 0),
        # Units Scanner already processed against this demand are covered too
        # (addendum 2026-09-26): the row's awaiting fell to 0 when they resolved,
        # yet only the unprocessed remainder can be missing.
        (10, (0, 0, 0, 4), 6),
        (10, (2, 0, 1, 7), 0),
    ],
)
def test_ceiling_is_the_uncovered_remainder_floored_at_zero(requested, counters, expected):
    in_queue, in_progress, awaiting, resolved = counters
    assert (
        missing_quantity_ceiling(
            quantity_requested=requested,
            quantity_in_queue=in_queue,
            quantity_in_progress=in_progress,
            quantity_awaiting=awaiting,
            quantity_resolved=resolved,
        )
        == expected
    )


def test_active_and_outstanding_read_the_snapshot_only():
    snapshot = SimpleNamespace(closed_at=None, quantity_requested=5, quantity_missing=2)
    assert is_snapshot_active(snapshot) is True
    assert outstanding_quantity(snapshot) == 3
    assert is_snapshot_active(SimpleNamespace(closed_at="x")) is False


def _snap(client_id, row, priority, order):
    return SimpleNamespace(
        client_id=client_id, stock_report_item_id=row, priority=priority, priority_order=order
    )


def test_merge_source_members_first_kept_members_after_dense():
    """Active: a(high 1) b(high 2) c(none) d(low 1). Source: b(high 1) c(high 2)
    e(high 3, row gone). Result: high = b1 c2 a3 (source members in source order,
    then a kept as it was); d untouched; nothing for the vanished row."""
    active = [
        _snap("sa", "ra", P.HIGH, 1),
        _snap("sb", "rb", P.HIGH, 2),
        _snap("sc", "rc", None, None),
        _snap("sd", "rd", P.LOW, 1),
    ]
    source = [
        _snap("xb", "rb", P.HIGH, 1),
        _snap("xc", "rc", P.HIGH, 2),
        _snap("xe", "re", P.HIGH, 3),
    ]
    assert merge_priority_orders(active, source) == {
        "sa": (P.HIGH, 3),
        "sb": (P.HIGH, 1),
        "sc": (P.HIGH, 2),
    }


def test_merge_source_null_clears_a_kept_priority_and_reports_only_changes():
    """A row unprioritised in the source becomes unprioritised (null pairs with
    null); an active snapshot already at its merged position is not reported."""
    active = [_snap("sa", "ra", P.HIGH, 1), _snap("sb", "rb", P.MEDIUM, 1)]
    source = [_snap("xa", "ra", None, None), _snap("xb", "rb", P.MEDIUM, 4)]
    assert merge_priority_orders(active, source) == {"sa": (None, None)}


def test_merge_with_an_empty_source_changes_nothing():
    active = [_snap("sa", "ra", P.HIGH, 1), _snap("sb", "rb", None, None)]
    assert merge_priority_orders(active, []) == {}


def test_merge_renumbers_a_sparse_current_group_when_a_source_member_joins():
    """Kept members keep their relative order but are renumbered densely after the
    source members: current high = a1 c3 (sparse); source puts b at high 1."""
    active = [
        _snap("sa", "ra", P.HIGH, 1),
        _snap("sc", "rc", P.HIGH, 3),
        _snap("sb", "rb", None, None),
    ]
    source = [_snap("xb", "rb", P.HIGH, 1)]
    assert merge_priority_orders(active, source) == {
        "sb": (P.HIGH, 1),
        "sa": (P.HIGH, 2),
    }


# ---------------------------------------------------------------------------
# Version progress (addendum 2026-09-26)
# ---------------------------------------------------------------------------


def _group(priority, **values):
    group = {key: 0 for key in PROGRESS_KEYS}
    group.update(values)
    group["priority"] = priority
    return group


def test_empty_progress_carries_every_key_and_every_priority_at_zero():
    progress = empty_version_progress()
    assert set(progress) == set(PROGRESS_KEYS) | {"by_priority"}
    assert set(progress["by_priority"]) == {"high", "medium", "low", "unset"}
    assert all(progress[key] == 0 for key in PROGRESS_KEYS)
    for slot in progress["by_priority"].values():
        assert set(slot) == set(PROGRESS_KEYS)
        assert all(value == 0 for value in slot.values())


def test_fold_sums_groups_into_totals_and_slots_each_under_its_priority():
    progress = fold_version_progress(
        [
            _group(P.HIGH, items_total=2, quantity_requested=10, quantity_target=8,
                   quantity_awaiting=5, quantity_completed=5, items_completed=1),
            _group("low", items_total=1, quantity_requested=3, quantity_target=3,
                   quantity_awaiting=7, quantity_completed=3, items_completed=1),
        ]
    )
    assert progress["items_total"] == 3
    assert progress["quantity_requested"] == 13
    assert progress["quantity_target"] == 11
    assert progress["quantity_awaiting"] == 12
    assert progress["quantity_completed"] == 8
    assert progress["items_completed"] == 2
    assert progress["by_priority"]["high"]["quantity_target"] == 8
    assert progress["by_priority"]["low"]["quantity_awaiting"] == 7
    # A priority with no group is present, at zero — the frontend never branches
    # on absence.
    assert progress["by_priority"]["medium"] == {key: 0 for key in PROGRESS_KEYS}


def test_fold_slots_the_null_priority_group_under_unset_and_counts_it_in_totals():
    # `priority=all` / omitted select null-priority snapshots too (2026-09-26); the
    # totals stay the sum of the four slots.
    progress = fold_version_progress(
        [
            _group(None, items_total=2, quantity_requested=9, quantity_target=9),
            _group(P.MEDIUM, items_total=1, quantity_requested=4, quantity_target=4),
        ]
    )
    assert progress["by_priority"]["unset"]["items_total"] == 2
    assert progress["by_priority"]["unset"]["quantity_target"] == 9
    assert progress["by_priority"]["medium"]["quantity_requested"] == 4
    assert progress["items_total"] == 3
    assert progress["quantity_requested"] == 13
    assert progress["by_priority"]["high"] == {key: 0 for key in PROGRESS_KEYS}


def test_fold_of_nothing_is_the_empty_progress():
    assert fold_version_progress([]) == empty_version_progress()
