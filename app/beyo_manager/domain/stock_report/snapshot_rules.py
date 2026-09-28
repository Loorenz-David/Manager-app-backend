"""Pure rules of the snapshot layer (no I/O).

* `version_state` / `is_version_draft` / `is_version_active` — the three derived
  states of a version (draft versions, 2026-09-28): `draft` = neither date set,
  `active` = `active_at` only, `closed` = both. The fourth combination is
  unstorable (`ck_…_closed_implies_activated`) and raises here.
* `is_snapshot_open` (`closed_at IS NULL`, drafts included — the counters'
  live-or-frozen switch) and `is_snapshot_active` (the pair — "the board").
* `effective_quantity_requested` / `scanner_quantity_requested` /
  `quantity_requested_source` — the one derivation of a snapshot's requested
  quantity: the user's manual override when set, else Scanner's value, which is the
  **live row's** while the version is a draft and the frozen
  `quantity_requested_scanner` once activated (a closed snapshot never reads the row).
* `effective_quantity_missing` / `quantity_missing_source` — the missing twin: an
  activated snapshot's own number; on a draft the typed value, else the active
  version's value for the same row (borrowed), else 0.
* `missing_quantity_ceiling` — the most a snapshot may mark missing: what its
  effective requested still leaves uncovered by the row's live counters. Both the
  PATCH refusal and the creation-time clamp read this one function; callers pass
  the effective value.
* `outstanding_quantity` — what the board shows as still to do for a snapshot; the
  listing's default predicate is `outstanding_quantity(...) > 0`.
* `merge_priority_orders` — the "copy a previous version's order" rule: source
  members first in source order, current-only members after in their current order,
  every group renumbered densely.
* `fold_version_progress` / `empty_version_progress` — the shape of a version's
  progress (addendum 2026-09-26): one aggregate per priority group folded into
  totals plus `by_priority`, every priority key always present — `high`, `medium`,
  `low` and `unset` (the null-priority snapshots, since the progress follows the
  board's `priority` filter). A computed dict, built here and not in `serializers.py`
  (46_serialization "Exempt cases").
"""

from __future__ import annotations

from collections.abc import Iterable

from beyo_manager.domain.stock_report.enums import (
    StockReportPriorityEnum,
    StockReportQuantityMissingSourceEnum,
    StockReportQuantityRequestedSourceEnum,
    StockReportSnapshotVersionStateEnum,
)

PROGRESS_KEYS = (
    "items_total",
    "items_completed",
    "quantity_requested",
    "quantity_missing",
    "quantity_target",
    "quantity_in_queue",
    "quantity_in_progress",
    "quantity_awaiting",
    "quantity_resolved",
    "quantity_completed",
)


# The `by_priority` key of the null-priority snapshots (owner's word, 2026-09-26).
UNSET_PRIORITY_KEY = "unset"
PROGRESS_PRIORITY_KEYS = (
    *(priority.value for priority in StockReportPriorityEnum),
    UNSET_PRIORITY_KEY,
)


def _zero_progress() -> dict:
    return {key: 0 for key in PROGRESS_KEYS}


def empty_version_progress() -> dict:
    progress = _zero_progress()
    progress["by_priority"] = {key: _zero_progress() for key in PROGRESS_PRIORITY_KEYS}
    return progress


def fold_version_progress(groups: Iterable) -> dict:
    """`groups` — one mapping per priority group of a version, carrying `priority`
    (an enum member, its value, or `None` for the `unset` slot) and every key of `PROGRESS_KEYS` as already
    aggregated integers. The per-item caps (`quantity_completed = Σ min(target_i,
    awaiting_i)`, `items_completed`) are the aggregator's job; this only sums groups
    into totals and slots each under its priority key."""
    progress = empty_version_progress()
    for group in groups:
        priority = group["priority"]
        if priority is None:
            priority = UNSET_PRIORITY_KEY
        priority = priority.value if hasattr(priority, "value") else priority
        slot = progress["by_priority"][priority]
        for key in PROGRESS_KEYS:
            value = int(group[key])
            slot[key] += value
            progress[key] += value
    return progress


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


def version_state(version) -> StockReportSnapshotVersionStateEnum:
    """Derived from the two dates; the unstorable pair (`closed_at` without
    `active_at`) raises rather than being read as anything."""
    if version.closed_at is not None:
        if version.active_at is None:
            raise ValueError(
                "a version cannot be closed without having been activated"
            )
        return StockReportSnapshotVersionStateEnum.CLOSED
    if version.active_at is not None:
        return StockReportSnapshotVersionStateEnum.ACTIVE
    return StockReportSnapshotVersionStateEnum.DRAFT


def is_version_draft(version) -> bool:
    return version.active_at is None and version.closed_at is None


def is_version_active(version) -> bool:
    return version.active_at is not None and version.closed_at is None


def is_snapshot_open(snapshot) -> bool:
    """Draft or active: the counters are the row's live ones."""
    return snapshot.closed_at is None


def is_snapshot_active(snapshot) -> bool:
    """The board: activated and not yet closed."""
    return snapshot.active_at is not None and snapshot.closed_at is None


# ---------------------------------------------------------------------------
# The requested quantity — one derivation
# ---------------------------------------------------------------------------


def scanner_quantity_requested(snapshot, *, row) -> int:
    """What Scanner says (a draft: the live row) or said (activated: the frozen
    column). Never None on a stored snapshot: the check ties the column to
    `active_at`."""
    if snapshot.active_at is None:
        return row.quantity_requested
    return snapshot.quantity_requested_scanner


def effective_quantity_requested(snapshot, *, row) -> int:
    if snapshot.quantity_requested_manual is not None:
        return snapshot.quantity_requested_manual
    return scanner_quantity_requested(snapshot, row=row)


def quantity_requested_source(snapshot) -> StockReportQuantityRequestedSourceEnum:
    if snapshot.quantity_requested_manual is not None:
        return StockReportQuantityRequestedSourceEnum.MANUAL
    return StockReportQuantityRequestedSourceEnum.SCANNER


# ---------------------------------------------------------------------------
# The missing quantity — borrowed unless typed
# ---------------------------------------------------------------------------


def effective_quantity_missing(snapshot, *, active_quantity_missing) -> int:
    """`active_quantity_missing` is the row's **active** snapshot's number (None
    when the workspace has no active version or the row has no snapshot in it).
    An activated snapshot ignores it: its own column is its number."""
    if snapshot.active_at is not None:
        return snapshot.quantity_missing
    if snapshot.quantity_missing is not None:
        return snapshot.quantity_missing
    if active_quantity_missing is not None:
        return active_quantity_missing
    return 0


def quantity_missing_source(
    snapshot, *, active_quantity_missing
) -> StockReportQuantityMissingSourceEnum:
    if snapshot.active_at is not None or snapshot.quantity_missing is not None:
        return StockReportQuantityMissingSourceEnum.OWN
    if active_quantity_missing is not None:
        return StockReportQuantityMissingSourceEnum.ACTIVE
    return StockReportQuantityMissingSourceEnum.NONE


def missing_quantity_ceiling(
    *,
    quantity_requested: int,
    quantity_in_queue: int,
    quantity_in_progress: int,
    quantity_awaiting: int,
    quantity_resolved: int,
) -> int:
    """`quantity_requested` is the **effective** value (the caller derives it).
    `quantity_resolved` is part of "covered": units Scanner already processed
    against this demand cannot be marked missing (addendum 2026-09-26)."""
    covered = (
        quantity_in_queue + quantity_in_progress + quantity_awaiting + quantity_resolved
    )
    return max(0, quantity_requested - covered)


def outstanding_quantity(snapshot, *, row, active_quantity_missing=None) -> int:
    return effective_quantity_requested(snapshot, row=row) - effective_quantity_missing(
        snapshot, active_quantity_missing=active_quantity_missing
    )


def merge_priority_orders(active: Iterable, source: Iterable) -> dict[str, tuple]:
    """New `(priority, priority_order)` per **changed** active snapshot when the
    `source` version's order is applied onto the `active` one.

    Both arguments are sequences of objects exposing `client_id`,
    `stock_report_item_id`, `priority` and `priority_order`. An active snapshot whose
    row has a source snapshot takes the source `priority`; one whose row is absent
    from the source keeps its current one (owner ruling 2026-09-26). Within each
    priority group the source members come first in source order, then the kept
    members in their current order, and the group is renumbered `1..n`. A null
    priority always pairs with a null order.
    """
    source_by_row = {snapshot.stock_report_item_id: snapshot for snapshot in source}
    groups: dict = {}
    proposed: dict[str, tuple] = {}
    for snapshot in active:
        origin = source_by_row.get(snapshot.stock_report_item_id)
        if origin is not None:
            new_priority = origin.priority
            sort_key = (0, origin.priority_order or 0, snapshot.client_id)
        else:
            new_priority = snapshot.priority
            sort_key = (1, snapshot.priority_order or 0, snapshot.client_id)
        if new_priority is None:
            proposed[snapshot.client_id] = (None, None)
            continue
        groups.setdefault(new_priority, []).append((sort_key, snapshot.client_id))

    for priority, members in groups.items():
        for order, (_key, client_id) in enumerate(sorted(members), 1):
            proposed[client_id] = (priority, order)

    changed: dict[str, tuple] = {}
    for snapshot in active:
        new_value = proposed[snapshot.client_id]
        if new_value != (snapshot.priority, snapshot.priority_order):
            changed[snapshot.client_id] = new_value
    return changed
