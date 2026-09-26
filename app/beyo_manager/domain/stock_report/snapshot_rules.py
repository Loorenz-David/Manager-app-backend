"""Pure rules of the snapshot layer (no I/O).

* `missing_quantity_ceiling` — the most a snapshot may mark missing: what its frozen
  `quantity_requested` still leaves uncovered by the row's live counters. Both the
  PATCH refusal and the creation-time clamp read this one function.
* `outstanding_quantity` — what the board shows as still to do for a snapshot; the
  listing's default predicate is `outstanding_quantity(snapshot) > 0`.
* `merge_priority_orders` — the "copy a previous version's order" rule: source
  members first in source order, current-only members after in their current order,
  every group renumbered densely.
* `fold_version_progress` / `empty_version_progress` — the shape of a version's
  progress (addendum 2026-09-26): one aggregate per priority group folded into
  totals plus `by_priority`, every priority key always present. A computed dict, built
  here and not in `serializers.py` (46_serialization "Exempt cases").
"""

from __future__ import annotations

from collections.abc import Iterable

from beyo_manager.domain.stock_report.enums import StockReportPriorityEnum

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


def _zero_progress() -> dict:
    return {key: 0 for key in PROGRESS_KEYS}


def empty_version_progress() -> dict:
    progress = _zero_progress()
    progress["by_priority"] = {
        priority.value: _zero_progress() for priority in StockReportPriorityEnum
    }
    return progress


def fold_version_progress(groups: Iterable) -> dict:
    """`groups` — one mapping per priority group of a version, carrying `priority`
    (an enum member or its value) and every key of `PROGRESS_KEYS` as already
    aggregated integers. The per-item caps (`quantity_completed = Σ min(target_i,
    awaiting_i)`, `items_completed`) are the aggregator's job; this only sums groups
    into totals and slots each under its priority key."""
    progress = empty_version_progress()
    for group in groups:
        priority = group["priority"]
        priority = priority.value if hasattr(priority, "value") else priority
        slot = progress["by_priority"][priority]
        for key in PROGRESS_KEYS:
            value = int(group[key])
            slot[key] += value
            progress[key] += value
    return progress


def missing_quantity_ceiling(
    *,
    quantity_requested: int,
    quantity_in_queue: int,
    quantity_in_progress: int,
    quantity_awaiting: int,
    quantity_resolved: int,
) -> int:
    """`quantity_resolved` is part of "covered": units Scanner already processed
    against this frozen demand cannot be marked missing (addendum 2026-09-26)."""
    covered = (
        quantity_in_queue + quantity_in_progress + quantity_awaiting + quantity_resolved
    )
    return max(0, quantity_requested - covered)


def is_snapshot_active(snapshot) -> bool:
    return snapshot.closed_at is None


def outstanding_quantity(snapshot) -> int:
    return snapshot.quantity_requested - snapshot.quantity_missing


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
