"""How the row-level commands find the snapshot they edit (draft versions,
2026-09-28; plan §4.6): the shortcut routes (`PATCH /items/{client_id}/…`, no
`version_id`) target the row's snapshot in the **active** version; the versioned
routes (`PATCH /snapshots/versions/{version_id}/items/{client_id}/…`) target the
row's snapshot in that version, whatever its state, and refuse a closed one.

Both are one command. The caller holds the command's first lock (the advisory lock
for the two priority routes, the row lock for missing and requested) before calling
`discover_target_snapshot`, so a shortcut that waits behind an activation resolves
the **newly** active version (R-3). Discovery is unlocked (§9 rule 4): it only
decides which snapshot id to lock. After the lock the caller re-reads and calls
`check_locked_target`, which maps the shortcut's two absences to v6's 422
`STOCK_REPORT_NO_ACTIVE_SNAPSHOT` and the versioned route's to 404 / 422
`STOCK_REPORT_VERSION_IS_CLOSED` (P-7), and returns the version read **after** the
lock — the reading that decides whether history is written (P-20).
"""

from __future__ import annotations

from dataclasses import dataclass

from beyo_manager.domain.stock_report.snapshot_rules import is_snapshot_active
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.stock_report._load_row_with_snapshot import (
    load_active_snapshot,
    load_version_snapshot,
)
from beyo_manager.services.commands.stock_report._versions import (
    VERSION_IS_CLOSED_MESSAGE,
    find_version,
)

NO_ACTIVE_SNAPSHOT_MESSAGE = (
    "STOCK_REPORT_NO_ACTIVE_SNAPSHOT: this stock report item has no active snapshot; "
    "create a new stock report version first."
)
ROW_NOT_FOUND_MESSAGE = "Stock report item not found."


@dataclass(frozen=True)
class TargetSnapshot:
    snapshot: object  # the unlocked discovery — an id to lock, never a decision
    version_id: str
    shortcut: bool


async def discover_target_snapshot(session, workspace_id, row_id, version_id):
    if version_id is None:
        discovered = await load_active_snapshot(session, workspace_id, row_id)
        if discovered is None:
            raise ValidationError(NO_ACTIVE_SNAPSHOT_MESSAGE)
        return TargetSnapshot(discovered, discovered.version_id, True)
    await find_version(session, workspace_id, version_id)
    discovered = await load_version_snapshot(session, workspace_id, row_id, version_id)
    if discovered is None:
        raise NotFound(ROW_NOT_FOUND_MESSAGE)
    return TargetSnapshot(discovered, version_id, False)


async def check_locked_target(session, workspace_id, target, snapshot):
    """`snapshot` is the post-lock re-read (None when it vanished meanwhile).
    Returns the version, read after the lock."""
    if target.shortcut:
        if snapshot is None or not is_snapshot_active(snapshot):
            raise ValidationError(NO_ACTIVE_SNAPSHOT_MESSAGE)
    version = await find_version(session, workspace_id, target.version_id)
    if version.closed_at is not None:
        # Unreachable on the shortcut (an active snapshot's version is open). On
        # the versioned route the id may have been closed by an activation, or
        # named a closed version outright; either way 422 comes before the 404
        # below (the priority commands lock open snapshots only, so a closed
        # snapshot is absent from their post-lock read).
        raise ValidationError(VERSION_IS_CLOSED_MESSAGE)
    if snapshot is None:
        raise NotFound(ROW_NOT_FOUND_MESSAGE)
    return version
