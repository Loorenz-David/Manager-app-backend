"""The version lookup and the refusal sentences the version-scoped commands share
(draft versions, 2026-09-28).

`find_version` is the 404 boundary of every route that names a version: absent and
foreign are one answer, `NotFound("Stock report snapshot version not found.")`, the
sentence apply-priorities published in v6. The state refusals are `ValidationError`
identities from the frontend contract (v7 §7): `STOCK_REPORT_VERSION_IS_CLOSED` for a
row edit on a closed version, `STOCK_REPORT_VERSION_NOT_DRAFT` for a draft-only
action on an activated one.
"""

from __future__ import annotations

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)

VERSION_NOT_FOUND_MESSAGE = "Stock report snapshot version not found."
VERSION_IS_CLOSED_MESSAGE = (
    "STOCK_REPORT_VERSION_IS_CLOSED: this version is closed; its snapshots are "
    "history and cannot be edited."
)
VERSION_NOT_DRAFT_MESSAGE = (
    "STOCK_REPORT_VERSION_NOT_DRAFT: this action applies to a draft version only."
)


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
