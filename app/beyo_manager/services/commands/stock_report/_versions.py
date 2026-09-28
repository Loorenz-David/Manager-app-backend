"""The version lookup, the close-freeze and the refusal sentences the
version-scoped commands share (draft versions, 2026-09-28).

`find_version` is the 404 boundary of every route that names a version: absent and
foreign are one answer, `NotFound("Stock report snapshot version not found.")`, the
sentence apply-priorities published in v6. The state refusals are `ValidationError`
identities from the frontend contract (v7 §7): `STOCK_REPORT_VERSION_IS_CLOSED` for a
row edit on a closed version, `STOCK_REPORT_VERSION_NOT_DRAFT` for a draft-only
action on an activated one, `STOCK_REPORT_VERSION_NOT_ACTIVE` for the refresh, which
targets the active version only (v8).

`close_active_version` is the one close path (plan §4.1, §4.2 step 3): the direct
active create and the activation of a draft both close the running board the same
way — its open snapshots get `closed_at` and their counters **frozen from the
rows** in one `text()` `UPDATE … FROM` (plan §3.3), then the version row is stamped.
Every predicate is the **active** pair, so a draft is never closed here. The caller
holds the advisory lock and has locked the snapshots it needs; this locks the
version row itself.
"""

from __future__ import annotations

from sqlalchemy import DateTime, bindparam, select, text, update

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)
from beyo_manager.services.commands.stock_report._predicates import (
    SNAPSHOT_ACTIVE_SQL,
    version_is_active,
)
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent

VERSION_NOT_FOUND_MESSAGE = "Stock report snapshot version not found."
VERSION_IS_CLOSED_MESSAGE = (
    "STOCK_REPORT_VERSION_IS_CLOSED: this version is closed; its snapshots are "
    "history and cannot be edited."
)
VERSION_NOT_DRAFT_MESSAGE = (
    "STOCK_REPORT_VERSION_NOT_DRAFT: this action applies to a draft version only."
)
VERSION_NOT_ACTIVE_MESSAGE = (
    "STOCK_REPORT_VERSION_NOT_ACTIVE: only the active version can be refreshed; a "
    "draft is live already and a closed version is history."
)

_FREEZE_STATEMENT = text(
    "UPDATE stock_report_item_snapshots AS s "
    "SET closed_at = :now, "
    "quantity_in_queue = r.quantity_in_queue, "
    "quantity_in_progress = r.quantity_in_progress, "
    "quantity_awaiting = r.quantity_awaiting, "
    "updated_at = :now, updated_by_id = :actor "
    "FROM stock_report_items AS r "
    "WHERE r.client_id = s.stock_report_item_id "
    f"AND s.workspace_id = :ws AND {SNAPSHOT_ACTIVE_SQL}"
).bindparams(bindparam("now", type_=DateTime(timezone=True)))


async def find_version(session, workspace_id, version_id, *, for_update=False):
    """The version, re-read from the database (`populate_existing`), or `NotFound`.
    With `for_update` the row is locked — the delete-draft command's first row lock
    (plan §4.8) and the demand webhook's draft-membership lock share this shape."""
    statement = (
        select(StockReportSnapshotVersion)
        .where(
            StockReportSnapshotVersion.workspace_id == workspace_id,
            StockReportSnapshotVersion.client_id == version_id,
        )
        .execution_options(populate_existing=True)
    )
    if for_update:
        statement = statement.with_for_update()
    version = await session.scalar(statement)
    if version is None:
        raise NotFound(VERSION_NOT_FOUND_MESSAGE)
    return version


async def close_active_version(session, *, workspace_id, now, actor_user_id):
    """Close the workspace's active version, if any: freeze its open snapshots'
    counters from the rows and stamp both with `closed_at`. Returns the closed
    version (re-read) or None when there was none."""
    previous = await session.scalar(
        select(StockReportSnapshotVersion)
        .where(
            StockReportSnapshotVersion.workspace_id == workspace_id,
            version_is_active(),
        )
        .with_for_update()
    )
    if previous is None:
        return None
    await session.execute(
        _FREEZE_STATEMENT,
        {"now": now, "actor": actor_user_id or None, "ws": workspace_id},
    )
    await session.execute(
        update(StockReportSnapshotVersion)
        .where(StockReportSnapshotVersion.client_id == previous.client_id)
        .values(closed_at=now, closed_by_id=actor_user_id or None)
    )
    await session.refresh(previous)
    return previous


def closed_version_event(version):
    return WorkspaceEvent(
        event_name="stock_report_snapshot_version:closed",
        client_id=version.client_id,
        workspace_id=version.workspace_id,
        extra={"snapshot_count": version.snapshot_count},
    )


def updated_version_event(version):
    """`stock_report_snapshot_version:updated` — the PATCH-version route's event and
    a skipped scheduled activation's (v9 §5.19, §5.21): the three editable fields as
    they now stand, the schedule echoed in UTC."""
    return WorkspaceEvent(
        event_name="stock_report_snapshot_version:updated",
        client_id=version.client_id,
        workspace_id=version.workspace_id,
        extra={
            "title": version.title,
            "scheduled_activation_at": (
                version.scheduled_activation_at.isoformat()
                if version.scheduled_activation_at is not None
                else None
            ),
            "scheduled_activation_keeps_active_missing": (
                version.scheduled_activation_keeps_active_missing
            ),
        },
    )
