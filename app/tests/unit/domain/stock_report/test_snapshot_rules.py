"""The pure snapshot rules (`domain/stock_report/snapshot_rules.py`, 2026-09-26;
draft versions 2026-09-28)."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from beyo_manager.domain.stock_report.enums import (
    StockReportPriorityEnum as P,
    StockReportQuantityMissingSourceEnum as MissingSource,
    StockReportQuantityRequestedSourceEnum as RequestedSource,
    StockReportSnapshotVersionStateEnum as State,
)
from beyo_manager.domain.stock_report.snapshot_rules import (
    PROGRESS_KEYS,
    effective_quantity_missing,
    effective_quantity_requested,
    empty_version_progress,
    fold_version_progress,
    is_snapshot_active,
    is_snapshot_open,
    is_version_active,
    is_version_draft,
    merge_priority_orders,
    missing_quantity_ceiling,
    outstanding_quantity,
    quantity_missing_source,
    quantity_requested_source,
    scanner_quantity_requested,
    version_state,
)

pytestmark = pytest.mark.unit

NOW = datetime(2026, 9, 28, 12, 0, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)


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


# ---------------------------------------------------------------------------
# State (draft versions, 2026-09-28)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("active_at", "closed_at", "state"),
    [
        (None, None, State.DRAFT),
        (NOW, None, State.ACTIVE),
        (NOW, LATER, State.CLOSED),
    ],
)
def test_version_state_is_derived_from_the_two_dates(active_at, closed_at, state):
    version = SimpleNamespace(active_at=active_at, closed_at=closed_at)
    assert version_state(version) is state
    assert is_version_draft(version) is (state is State.DRAFT)
    assert is_version_active(version) is (state is State.ACTIVE)


def test_the_unstorable_pair_raises_rather_than_reading_as_a_state():
    with pytest.raises(ValueError):
        version_state(SimpleNamespace(active_at=None, closed_at=LATER))


@pytest.mark.parametrize(
    ("active_at", "closed_at", "open_", "active"),
    [
        (None, None, True, False),  # a draft's snapshot: open, not the board
        (NOW, None, True, True),  # the board
        (NOW, LATER, False, False),  # closed
        (None, LATER, False, False),  # unstorable; still never "active"
    ],
)
def test_open_and_active_are_two_predicates(active_at, closed_at, open_, active):
    snapshot = SimpleNamespace(active_at=active_at, closed_at=closed_at)
    assert is_snapshot_open(snapshot) is open_
    assert is_snapshot_active(snapshot) is active


# ---------------------------------------------------------------------------
# The requested quantity — the three rows of the plan's §3.3 table
# ---------------------------------------------------------------------------


def _snapshot(*, active_at, scanner, manual, missing=None, closed_at=None):
    return SimpleNamespace(
        active_at=active_at,
        closed_at=closed_at,
        quantity_requested_scanner=scanner,
        quantity_requested_manual=manual,
        quantity_missing=missing,
    )


ROW = SimpleNamespace(quantity_requested=10)


def test_a_draft_with_no_override_reads_the_live_row():
    snapshot = _snapshot(active_at=None, scanner=None, manual=None)
    assert scanner_quantity_requested(snapshot, row=ROW) == 10
    assert effective_quantity_requested(snapshot, row=ROW) == 10
    assert quantity_requested_source(snapshot) is RequestedSource.SCANNER
    # Scanner moves → the draft moves with it.
    assert effective_quantity_requested(snapshot, row=SimpleNamespace(quantity_requested=12)) == 12


def test_a_draft_with_an_override_reads_the_override_and_still_shows_scanner_live():
    snapshot = _snapshot(active_at=None, scanner=None, manual=7)
    assert effective_quantity_requested(snapshot, row=ROW) == 7
    assert scanner_quantity_requested(snapshot, row=ROW) == 10
    assert quantity_requested_source(snapshot) is RequestedSource.MANUAL


def test_an_activated_snapshot_reads_the_frozen_column_and_keeps_its_override():
    snapshot = _snapshot(active_at=NOW, scanner=12, manual=7)
    assert effective_quantity_requested(snapshot, row=ROW) == 7
    assert scanner_quantity_requested(snapshot, row=ROW) == 12
    snapshot.quantity_requested_manual = None  # revert
    assert effective_quantity_requested(snapshot, row=ROW) == 12
    assert quantity_requested_source(snapshot) is RequestedSource.SCANNER


def test_a_closed_snapshot_never_reads_the_row():
    """The row may be gone (a deleted row's closed snapshot); the frozen column
    is the answer whatever the row says."""
    snapshot = _snapshot(active_at=NOW, closed_at=LATER, scanner=12, manual=None)
    assert effective_quantity_requested(snapshot, row=None) == 12
    assert scanner_quantity_requested(snapshot, row=None) == 12


def test_a_pinned_value_equal_to_scanners_is_manual():
    """Card 6: typing the value Scanner shows stores it; the source says so."""
    snapshot = _snapshot(active_at=None, scanner=None, manual=10)
    assert effective_quantity_requested(snapshot, row=ROW) == 10
    assert quantity_requested_source(snapshot) is RequestedSource.MANUAL


# ---------------------------------------------------------------------------
# The missing quantity — the four rows of the plan's §3.4b table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("own", "active_missing", "expected", "source"),
    [
        (None, 5, 5, MissingSource.ACTIVE),  # nothing typed: borrowed
        (2, 5, 2, MissingSource.OWN),  # typed 2
        (0, 5, 0, MissingSource.OWN),  # typed 0 hides the board's 5
        (None, None, 0, MissingSource.NONE),  # nothing typed, no active version
    ],
)
def test_a_draft_borrows_the_active_missing_unless_typed(
    own, active_missing, expected, source
):
    snapshot = _snapshot(active_at=None, scanner=None, manual=None, missing=own)
    assert (
        effective_quantity_missing(snapshot, active_quantity_missing=active_missing)
        == expected
    )
    assert (
        quantity_missing_source(snapshot, active_quantity_missing=active_missing)
        is source
    )


def test_an_activated_snapshot_ignores_the_borrowed_value():
    snapshot = _snapshot(active_at=NOW, scanner=10, manual=None, missing=3)
    assert effective_quantity_missing(snapshot, active_quantity_missing=5) == 3
    assert (
        quantity_missing_source(snapshot, active_quantity_missing=5)
        is MissingSource.OWN
    )


def test_outstanding_is_effective_requested_minus_effective_missing():
    active = _snapshot(active_at=NOW, scanner=5, manual=None, missing=2)
    assert outstanding_quantity(active, row=ROW) == 3
    draft = _snapshot(active_at=None, scanner=None, manual=None, missing=None)
    assert outstanding_quantity(draft, row=ROW, active_quantity_missing=4) == 6
    assert outstanding_quantity(draft, row=ROW) == 10


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
