"""The version commands and reads (2026-09-26): `create_stock_report_snapshot_version`,
`apply_stock_report_snapshot_version_priorities`, `list_stock_report_snapshot_versions`,
`get_stock_report_missing_summary`.

Rows are created through the demand service `AD` (the only creator of rows), which
refuses a session already in a transaction, so every test here is a committing test:
`seed -> commit -> AD -> ... -> finally purge + commit`.
"""

import asyncio
import time
from datetime import datetime, timezone

from types import SimpleNamespace

import pytest
from sqlalchemy import select, text

from beyo_manager.config import Settings, settings
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
    normalize_stock_criteria,
)
from beyo_manager.domain.stock_report.enums import (
    StockReportHistoryRecordTypeEnum,
    StockTaskAssignmentStateEnum,
)
from beyo_manager.domain.stock_report.snapshot_rules import (
    PROGRESS_KEYS,
    empty_version_progress,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.stock_report._move_assignment import move_assignment
from beyo_manager.services.commands.stock_report.delete_stock_report_item import (
    delete_stock_report_item,
)
from beyo_manager.services.commands.stock_report.process_items_processed import (
    process_items_processed,
)
from beyo_manager.services.commands.stock_report.apply_stock_demand import (
    apply_stock_demand,
)
from beyo_manager.services.commands.stock_report.apply_stock_report_snapshot_version_priorities import (
    apply_stock_report_snapshot_version_priorities,
)
from beyo_manager.services.commands.stock_report.create_stock_report_snapshot_version import (
    create_stock_report_snapshot_version,
)
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from beyo_manager.services.commands.stock_report.stock_demand_entries import DemandEntry
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.stock_report.get_stock_report_active_snapshot_version import (
    get_stock_report_active_snapshot_version,
)
from beyo_manager.services.queries.stock_report.get_stock_report_missing_summary import (
    get_stock_report_missing_summary,
)
from beyo_manager.services.queries.stock_report.list_stock_report_snapshot_versions import (
    list_stock_report_snapshot_versions,
)
from tests.helpers.statement_listener import record_statements
from tests.helpers.stock_report import (
    active_snapshot,
    assert_stock_report_clean,
    capture_dispatch,
    make_ctx,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
    set_snapshot_position,
    snapshot_positions,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


def _pin(session, seeded):
    """Everything a test reads from the seed, captured **once** while the ORM
    instances are live: `session.rollback()` expires them and a later attribute read
    would attempt IO outside the greenlet context (the `_seller` precedent)."""
    return SimpleNamespace(
        identity=make_ctx(session, seeded).identity,
        worker_identity=make_ctx(session, seeded, role_name="worker").identity,
        workspace=SimpleNamespace(client_id=seeded.workspace.client_id),
        manager=SimpleNamespace(client_id=seeded.manager.client_id),
        task=SimpleNamespace(client_id=seeded.task.client_id),
        item=SimpleNamespace(
            client_id=seeded.item.client_id, article_number=seeded.item.article_number
        ),
    )

NOW = datetime(2026, 9, 26, 12, 0, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
_TIMEOUT_MS = Settings.model_fields["stock_demand_webhook_timeout_ms"].default
VERSION_SITE = (
    "beyo_manager.services.commands.stock_report"
    ".create_stock_report_snapshot_version.dispatch"
)
APPLY_SITE = (
    "beyo_manager.services.commands.stock_report"
    ".apply_stock_report_snapshot_version_priorities.dispatch"
)


def _entry(index, token, quantity=10):
    raw = {"wood_group": [token]}
    return DemandEntry(
        index=index,
        item_category_raw="Dining Chairs",
        properties_raw=raw,
        properties_normalized=normalize_stock_criteria(raw),
        properties_signature=compute_stock_criteria_signature(raw),
        quantity_requested=quantity,
    )


async def _AD(session, workspace_id, entries):
    return await apply_stock_demand(
        session,
        workspace_id=workspace_id,
        entries=entries,
        now=NOW,
        deadline=time.monotonic() + 60,
        timeout_ms=_TIMEOUT_MS,
    )


async def _ids(session, workspace_id):
    return sorted(
        (
            await session.scalars(
                select(StockReportItem.client_id).where(
                    StockReportItem.workspace_id == workspace_id,
                    StockReportItem.is_deleted.is_(False),
                )
            )
        ).all()
    )


def _ctx(session, seeded, *, incoming_data=None, query_params=None, now=NOW):
    return ServiceContext(
        identity=seeded.identity,
        incoming_data=incoming_data or {},
        query_params=query_params or {},
        session=session,
        now=now,
    )


async def _CV(session, seeded, *, now=NOW, monkeypatch=None):
    captured = (
        capture_dispatch(monkeypatch, VERSION_SITE) if monkeypatch is not None else None
    )
    result = await create_stock_report_snapshot_version(_ctx(session, seeded, now=now))
    await session.commit()
    return result["stock_report_snapshot_version"], captured


async def _versions(session, workspace_id):
    return (
        await session.execute(
            select(StockReportSnapshotVersion)
            .where(StockReportSnapshotVersion.workspace_id == workspace_id)
            .order_by(StockReportSnapshotVersion.active_at)
            .execution_options(populate_existing=True)
        )
    ).scalars().all()


async def _snapshots_of(session, version_id):
    return {
        snapshot.stock_report_item_id: snapshot
        for snapshot in (
            await session.execute(
                select(StockReportItemSnapshot)
                .where(StockReportItemSnapshot.version_id == version_id)
                .execution_options(populate_existing=True)
            )
        ).scalars()
    }


# ---------------------------------------------------------------------------
# create_stock_report_snapshot_version
# ---------------------------------------------------------------------------


async def test_first_version_snapshots_every_live_row_including_zero_requested(
    db_session, monkeypatch
):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(
            db_session,
            workspace_id,
            [_entry(0, "a", 10), _entry(1, "b", 0), _entry(2, "c", 3)],
        )
        await db_session.commit()
        # A soft-deleted row is not live and gets no snapshot.
        a, b, c = await _ids(db_session, workspace_id)
        await db_session.commit()  # the read above autobegan; AD wants a clean session
        await _AD(db_session, workspace_id, [_entry(0, "gone", 1)])
        await db_session.commit()
        gone = next(i for i in await _ids(db_session, workspace_id) if i not in (a, b, c))
        await db_session.execute(
            text("UPDATE stock_report_items SET is_deleted = true WHERE client_id = :id"),
            {"id": gone},
        )
        await db_session.commit()

        version, captured = await _CV(db_session, seeded, monkeypatch=monkeypatch)

        assert version["snapshot_count"] == 3
        assert version["closed_at"] is None
        assert version["active_at"] == NOW.isoformat()
        assert version["created_by_id"] == seeded.manager.client_id
        snapshots = await _snapshots_of(db_session, version["client_id"])
        assert set(snapshots) == {a, b, c}
        # Labelled by frozen quantity, never by id order (a ULID is not creation
        # order, master plan §10).
        assert sorted(
            (s.quantity_requested_scanner, s.quantity_missing, s.priority, s.priority_order)
            for s in snapshots.values()
        ) == [(0, 0, None, None), (3, 0, None, None), (10, 0, None, None)]
        assert all(s.closed_at is None and s.active_at == NOW for s in snapshots.values())
        # `:created` carries `state` and `title` since drafts (2026-09-28, v7 §7.1).
        assert [(e.event_name, e.client_id, e.extra) for e in captured] == [
            (
                "stock_report_snapshot_version:created",
                version["client_id"],
                {"snapshot_count": 3, "state": "active", "title": None},
            )
        ]
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_second_version_closes_the_first_and_freezes_its_counters(
    db_session, monkeypatch
):
    """Arm: an assignment moves the row's counters **after** the first version and
    **before** the second. The closed snapshot must hold the counters as they stood
    at the close — not the ones it was created with, and not the ones the row moves
    on to afterwards. `quantity_missing` and priority start over on the new one."""
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10)])
        await db_session.commit()
        (row_id,) = await _ids(db_session, workspace_id)
        first, _ = await _CV(db_session, seeded)
        await set_snapshot_position(db_session, row_id, "high", 1)
        await db_session.execute(
            text(
                "UPDATE stock_report_item_snapshots SET quantity_missing = 2 "
                "WHERE stock_report_item_id = :id AND closed_at IS NULL"
            ),
            {"id": row_id},
        )
        await db_session.commit()
        # The seeded item (quantity 4) on the seeded task: in_queue 4.
        await create_stock_task_assignments(
            _ctx(
                db_session,
                seeded,
                incoming_data={
                    "entries": [
                        {
                            "stock_report_item_id": row_id,
                            "task_id": seeded.task.client_id,
                            "item_id": seeded.item.client_id,
                            "override_property_mismatch": True,
                        }
                    ]
                },
            )
        )
        await db_session.commit()
        # Scanner raises demand meanwhile: the row moves on, the snapshot must not.
        await _AD(db_session, workspace_id, [_entry(0, "a", 25)])
        await db_session.commit()

        second, captured = await _CV(db_session, seeded, now=LATER, monkeypatch=monkeypatch)

        versions = await _versions(db_session, workspace_id)
        assert [v.client_id for v in versions] == [first["client_id"], second["client_id"]]
        assert versions[0].closed_at == LATER
        assert versions[0].closed_by_id == seeded.manager.client_id
        assert versions[1].closed_at is None
        old = (await _snapshots_of(db_session, first["client_id"]))[row_id]
        new = (await _snapshots_of(db_session, second["client_id"]))[row_id]
        assert old.closed_at == LATER
        assert (old.quantity_requested_scanner, old.quantity_missing, old.priority_order) == (10, 2, 1)
        assert (old.quantity_in_queue, old.quantity_in_progress, old.quantity_awaiting) == (4, 0, 0)
        assert new.closed_at is None
        assert (new.quantity_requested_scanner, new.quantity_missing, new.priority, new.priority_order) == (25, 0, None, None)
        assert (await active_snapshot(db_session, row_id)).client_id == new.client_id
        assert [(e.event_name, e.client_id) for e in captured] == [
            ("stock_report_snapshot_version:closed", first["client_id"]),
            ("stock_report_snapshot_version:created", second["client_id"]),
        ]
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_an_empty_workspace_still_gets_a_version_with_no_snapshots(db_session):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        version, _ = await _CV(db_session, seeded)
        assert version["snapshot_count"] == 0
        assert await _snapshots_of(db_session, version["client_id"]) == {}
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_two_concurrent_creates_leave_exactly_one_active_version(db_session):
    """Both writers serialize on the advisory lock; the loser closes the winner's
    version, and Postgres never holds two open ones."""
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    identity = seeded.identity
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10)])
        await db_session.commit()

        barrier = asyncio.Barrier(2)

        async def _create():
            async for session in get_db_session():
                await barrier.wait()
                await create_stock_report_snapshot_version(
                    ServiceContext(identity=identity, incoming_data={}, session=session)
                )
                return
            raise AssertionError("Database session generator yielded no session")

        await asyncio.wait_for(asyncio.gather(_create(), _create()), timeout=15)

        versions = await _versions(db_session, workspace_id)
        assert len(versions) == 2
        assert sum(v.closed_at is None for v in versions) == 1
        assert (
            await db_session.scalar(
                select(StockReportItemSnapshot.client_id)
                .where(
                    StockReportItemSnapshot.workspace_id == workspace_id,
                    StockReportItemSnapshot.closed_at.is_(None),
                )
                .execution_options(populate_existing=True)
            )
        ) is not None
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# list_stock_report_snapshot_versions / get_stock_report_missing_summary
# ---------------------------------------------------------------------------


async def test_versions_list_is_newest_first_paginated_and_workspace_scoped(db_session):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    foreign = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id, foreign_id = seeded.workspace.client_id, foreign.workspace.client_id
    try:
        first, _ = await _CV(db_session, seeded, now=NOW)
        second, _ = await _CV(db_session, seeded, now=LATER)
        await _CV(db_session, foreign)

        result = await list_stock_report_snapshot_versions(
            _ctx(db_session, seeded, query_params={"limit": 1, "offset": 0})
        )
        assert [v["client_id"] for v in result["stock_report_snapshot_versions"]] == [
            second["client_id"]
        ]
        assert result["stock_report_snapshot_versions_pagination"] == {
            "has_more": True,
            "limit": 1,
            "offset": 0,
        }
        rest = await list_stock_report_snapshot_versions(
            _ctx(db_session, seeded, query_params={"limit": 1, "offset": 1})
        )
        assert [v["client_id"] for v in rest["stock_report_snapshot_versions"]] == [
            first["client_id"]
        ]
        assert rest["stock_report_snapshot_versions_pagination"]["has_more"] is False
        empty = await list_stock_report_snapshot_versions(
            _ctx(db_session, seeded, query_params={"limit": 50, "offset": 5})
        )
        assert empty == {
            "stock_report_snapshot_versions": [],
            "stock_report_snapshot_versions_pagination": {
                "has_more": False,
                "limit": 50,
                "offset": 5,
            },
        }
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await purge_stock_report_workspace(db_session, foreign_id)
        await db_session.commit()


async def test_missing_summary_counts_active_snapshots_only(db_session):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10), _entry(1, "b", 10), _entry(2, "c", 10)])
        await db_session.commit()
        a, b, c = await _ids(db_session, workspace_id)
        await _CV(db_session, seeded)
        for row_id, missing in ((a, 4), (b, 3), (c, 0)):
            await db_session.execute(
                text(
                    "UPDATE stock_report_item_snapshots SET quantity_missing = :m "
                    "WHERE stock_report_item_id = :id AND closed_at IS NULL"
                ),
                {"m": missing, "id": row_id},
            )
        await db_session.commit()
        assert await get_stock_report_missing_summary(_ctx(db_session, seeded)) == {
            "quantity_missing_total": 7,
            "items_with_missing": 2,
        }
        # A new version resets missing to 0 and the closed snapshots no longer count.
        await _CV(db_session, seeded, now=LATER)
        assert await get_stock_report_missing_summary(_ctx(db_session, seeded)) == {
            "quantity_missing_total": 0,
            "items_with_missing": 0,
        }
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# apply_stock_report_snapshot_version_priorities
# ---------------------------------------------------------------------------


async def test_apply_copies_a_closed_versions_order_onto_the_active_one(
    db_session, monkeypatch
):
    """Version 1: high = A1 B2 C3, low = X1; D present but unprioritised. Between
    the versions C's row is deleted and E is created (so E is in V2 only). V2 is
    given `high = E1, A2` and `low = D1` by hand. Applying V1 onto V2: A B take V1's
    `high` in V1 order; E, **absent** from V1, keeps its `high` after them; X takes
    V1's `low`; D, **present** in V1 as unprioritised, takes that null (the source's
    value is copied whatever it is — only absence keeps the current one)."""
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(
            db_session,
            workspace_id,
            [_entry(i, t) for i, t in enumerate("abcxd")],
        )
        await db_session.commit()
        ids = await _ids(db_session, workspace_id)
        by_token = {}
        for row in (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.client_id.in_(ids))
            )
        ).scalars():
            by_token[row.properties["wood_group"][0]] = row.client_id
        A, B, C, X, D = (by_token[t] for t in "abcxd")
        first, _ = await _CV(db_session, seeded)
        for row_id, priority, order in ((A, "high", 1), (B, "high", 2), (C, "high", 3), (X, "low", 1)):
            await set_snapshot_position(db_session, row_id, priority, order)
        await db_session.commit()

        # C is gone by V2; E is new in V2.
        await db_session.execute(
            text("UPDATE stock_report_items SET is_deleted = true WHERE client_id = :id"),
            {"id": C},
        )
        await db_session.commit()
        await _AD(db_session, workspace_id, [_entry(9, "e")])
        await db_session.commit()
        E = next(i for i in await _ids(db_session, workspace_id) if i not in (A, B, X, D))
        second, _ = await _CV(db_session, seeded, now=LATER)
        for row_id, priority, order in ((E, "high", 1), (A, "high", 2), (D, "low", 1)):
            await set_snapshot_position(db_session, row_id, priority, order)
        await db_session.commit()
        before_records = len(
            (await db_session.scalars(select(StockReportHistoryRecord.client_id).where(
                StockReportHistoryRecord.workspace_id == workspace_id,
                StockReportHistoryRecord.type != StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
            ))).all()
        )

        captured = capture_dispatch(monkeypatch, APPLY_SITE)
        ctx = _ctx(db_session, seeded, incoming_data={"client_id": first["client_id"]}, now=LATER)
        result = await apply_stock_report_snapshot_version_priorities(ctx)
        await db_session.commit()

        assert await snapshot_positions(db_session, workspace_id) == {
            A: ("high", 1),
            B: ("high", 2),
            E: ("high", 3),
            X: ("low", 1),
            D: (None, None),
        }
        # Changed: A (2->1), B (null->high 2), E (1->3), X (null->low 1), D (low 1->null).
        assert result["changed"] == 5
        assert {row["client_id"] for row in result["stock_report_items"]} == {A, B, E, X, D}
        assert all(row["snapshot"]["version_id"] == second["client_id"] for row in result["stock_report_items"])
        records = (
            await db_session.execute(
                select(StockReportHistoryRecord).where(
                    StockReportHistoryRecord.workspace_id == workspace_id,
                    StockReportHistoryRecord.created_at == LATER,
                    StockReportHistoryRecord.type != StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
                )
            )
        ).scalars().all()
        assert len(records) == 5 and before_records == 0
        assert {(r.stock_report_item_id, r.type) for r in records} == {
            (A, StockReportHistoryRecordTypeEnum.PRIORITY_ORDER_CHANGE),
            (B, StockReportHistoryRecordTypeEnum.PRIORITY_CHANGE),
            (E, StockReportHistoryRecordTypeEnum.PRIORITY_ORDER_CHANGE),
            (X, StockReportHistoryRecordTypeEnum.PRIORITY_CHANGE),
            (D, StockReportHistoryRecordTypeEnum.PRIORITY_CHANGE),
        }
        assert all(r.created_by_id == seeded.manager.client_id for r in records)
        assert sorted(e.event_name for e in captured) == ["stock_report_item_snapshot:updated"] * 5
        assert {e.extra["stock_report_item_id"]: (e.extra["priority"], e.extra["priority_order"]) for e in captured} == {
            A: ("high", 1),
            B: ("high", 2),
            E: ("high", 3),
            X: ("low", 1),
            D: (None, None),
        }
        # The movers are stamped by the applying user.
        assert (await active_snapshot(db_session, A)).updated_at == LATER
        assert (await active_snapshot(db_session, A)).updated_by_id == seeded.manager.client_id
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_apply_refuses_the_active_source_and_unknown_or_foreign_versions(db_session):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    foreign = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id, foreign_id = seeded.workspace.client_id, foreign.workspace.client_id
    try:
        active, _ = await _CV(db_session, seeded)
        foreign_version, _ = await _CV(db_session, foreign)

        with pytest.raises(ValidationError) as excinfo:
            await apply_stock_report_snapshot_version_priorities(
                _ctx(db_session, seeded, incoming_data={"client_id": active["client_id"]})
            )
        await db_session.rollback()
        assert str(excinfo.value).startswith("STOCK_REPORT_SOURCE_VERSION_IS_ACTIVE:")

        for client_id in (foreign_version["client_id"], "srv_absent"):
            with pytest.raises(NotFound):
                await apply_stock_report_snapshot_version_priorities(
                    _ctx(db_session, seeded, incoming_data={"client_id": client_id})
                )
            await db_session.rollback()
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await purge_stock_report_workspace(db_session, foreign_id)
        await db_session.commit()


async def test_apply_with_nothing_to_change_writes_nothing(db_session, monkeypatch):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a")])
        await db_session.commit()
        first, _ = await _CV(db_session, seeded)
        await _CV(db_session, seeded, now=LATER)
        captured = capture_dispatch(monkeypatch, APPLY_SITE)
        result = await apply_stock_report_snapshot_version_priorities(
            _ctx(db_session, seeded, incoming_data={"client_id": first["client_id"]})
        )
        assert result == {"changed": 0, "stock_report_items": []}
        assert captured == []
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# Version progress (addendum 2026-09-26): `get_stock_report_active_snapshot_version`
# and the `progress` each row of the list carries — one engine.
# ---------------------------------------------------------------------------

PROCESSED_API_KEY = "test-versions-processed-key"


def _expect(**values):
    """A progress slot: every key at 0 except the given ones."""
    slot = {key: 0 for key in PROGRESS_KEYS}
    slot.update(values)
    return slot


async def _seed_snapshot(session, row_id, *, missing=0, resolved=0, counters=None):
    """Fixture state the engine reads: the active snapshot's missing / resolved and
    the row's live counters (set directly — the engine reads columns; the real
    moves are exercised by the walk test below)."""
    await session.execute(
        text(
            "UPDATE stock_report_item_snapshots SET quantity_missing = :m, "
            "quantity_resolved = :r WHERE stock_report_item_id = :id "
            "AND closed_at IS NULL"
        ),
        {"m": missing, "r": resolved, "id": row_id},
    )
    if counters is not None:
        in_queue, in_progress, awaiting = counters
        await session.execute(
            text(
                "UPDATE stock_report_items SET quantity_in_queue = :q, "
                "quantity_in_progress = :p, quantity_awaiting = :a "
                "WHERE client_id = :id"
            ),
            {"q": in_queue, "p": in_progress, "a": awaiting, "id": row_id},
        )


async def _progress(session, seeded, priority="all"):
    result = await get_stock_report_active_snapshot_version(
        _ctx(session, seeded, query_params={"priority": priority})
    )
    return result["stock_report_snapshot_version"]


async def _listed(session, seeded, priority):
    listed = await list_stock_report_snapshot_versions(
        _ctx(session, seeded, query_params={"priority": priority})
    )
    return listed["stock_report_snapshot_versions"][0]


async def _listed_progress(session, seeded, priority):
    return (await _listed(session, seeded, priority))["progress"]


async def _assign_seeded_item(session, seeded, row_id):
    result = await create_stock_task_assignments(
        _ctx(
            session,
            seeded,
            incoming_data={
                "entries": [
                    {
                        "stock_report_item_id": row_id,
                        "task_id": seeded.task.client_id,
                        "item_id": seeded.item.client_id,
                        "override_property_mismatch": True,
                    }
                ]
            },
        )
    )
    await session.commit()
    return result["stock_task_assignments"][0]["client_id"]


async def _move(session, seeded, assignment_id, target):
    assignment = (
        await session.execute(
            select(StockTaskAssignment)
            .where(StockTaskAssignment.client_id == assignment_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    await move_assignment(
        session,
        assignment,
        target,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="test",
    )
    await session.commit()


async def _resolve_seeded_item(session, seeded, monkeypatch):
    monkeypatch.setattr(
        settings, "manager_api_key_to_location_tracker_app", PROCESSED_API_KEY
    )
    monkeypatch.setattr(
        settings, "location_tracker_webhook_workspace_id", seeded.workspace.client_id
    )
    body = ('[{"article_number": "%s"}]' % seeded.item.article_number).encode("utf-8")
    result = await process_items_processed(
        ServiceContext(
            identity={},
            incoming_data={"raw_body": body, "headers": {"x-api-key": PROCESSED_API_KEY}},
            session=session,
            now=NOW,
        )
    )
    assert result["results"][0]["outcome"] == "resolved"


async def test_active_version_is_null_before_the_first_version(db_session):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        assert await get_stock_report_active_snapshot_version(
            _ctx(db_session, seeded)
        ) == {"stock_report_snapshot_version": None}
        # The filter is parsed first: a bad value is refused even with no version.
        for bad in ("all,high", "urgent"):
            with pytest.raises(ValidationError, match="STOCK_REPORT_UNKNOWN_PRIORITY_FILTER"):
                await get_stock_report_active_snapshot_version(
                    _ctx(db_session, seeded, query_params={"priority": bad})
                )
            with pytest.raises(ValidationError, match="STOCK_REPORT_UNKNOWN_PRIORITY_FILTER"):
                await list_stock_report_snapshot_versions(
                    _ctx(db_session, seeded, query_params={"priority": bad})
                )
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_active_version_progress_follows_the_boards_priority_filter(db_session):
    """The matrix, by hand (`priority` as on `GET /items`: `high,medium,low` = the
    prioritised rows a-c, omitted = the unset row d, `all` = a-d; e never counts):

    | row | requested | priority | missing | in_queue/in_progress/awaiting | resolved | target | awaiting(wire) | completed |
    | a   | 10        | high 1   | 2       | 3 / 1 / 2                     | 5        | 8      | 7              | 7 (open)  |
    | b   | 6         | high 2   | 0       | 0 / 0 / 6                     | 2        | 6      | 8              | 6 (done)  |
    | c   | 5         | low 1    | 5       | 0 / 0 / 0                     | 0        | 0      | 0              | 0 (done)  |
    | d   | 8         | —        | 0       | 0 / 0 / 8                     | 0        | excluded: no priority        |
    | e   | 4         | medium 1 | 0       | 0 / 0 / 0                     | 0        | excluded: row deleted        |

    e is the medium group's only member, so that group reaches the aggregate with every
    row deleted — its sums must come back 0, not NULL.
    """
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(
            db_session,
            workspace_id,
            [
                _entry(0, "a", 10),
                _entry(1, "b", 6),
                _entry(2, "c", 5),
                _entry(3, "d", 8),
                _entry(4, "e", 4),
            ],
        )
        await db_session.commit()
        by_token = {}
        for row in (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.workspace_id == workspace_id)
            )
        ).scalars():
            by_token[row.properties["wood_group"][0]] = row.client_id
        a, b, c, d, e = (by_token[t] for t in "abcde")
        version, _ = await _CV(db_session, seeded)
        await set_snapshot_position(db_session, a, "high", 1)
        await set_snapshot_position(db_session, b, "high", 2)
        await set_snapshot_position(db_session, e, "medium", 1)
        await set_snapshot_position(db_session, c, "low", 1)
        await _seed_snapshot(db_session, a, missing=2, resolved=5, counters=(3, 1, 2))
        await _seed_snapshot(db_session, b, resolved=2, counters=(0, 0, 6))
        await _seed_snapshot(db_session, c, missing=5)
        await _seed_snapshot(db_session, d, counters=(0, 0, 8))
        await db_session.commit()
        await delete_stock_report_item(
            _ctx(db_session, seeded, incoming_data={"client_id": e})
        )
        await db_session.commit()

        payload = await _progress(db_session, seeded, "high,medium,low")

        assert payload["client_id"] == version["client_id"]
        assert payload["closed_at"] is None
        progress = payload["progress"]
        high = _expect(
            items_total=2,
            items_completed=1,
            quantity_requested=16,
            quantity_missing=2,
            quantity_target=14,
            quantity_in_queue=3,
            quantity_in_progress=1,
            quantity_awaiting=15,
            quantity_resolved=7,
            quantity_completed=13,
        )
        low = _expect(
            items_total=1,
            items_completed=1,
            quantity_requested=5,
            quantity_missing=5,
        )
        unset = _expect(
            items_total=1,
            items_completed=1,
            quantity_requested=8,
            quantity_target=8,
            quantity_awaiting=8,
            quantity_completed=8,
        )
        assert progress["by_priority"] == {
            "high": high,
            "medium": _expect(),
            "low": low,
            "unset": _expect(),
        }
        assert {key: progress[key] for key in PROGRESS_KEYS} == _expect(
            items_total=3,
            items_completed=2,
            quantity_requested=21,
            quantity_missing=7,
            quantity_target=14,
            quantity_in_queue=3,
            quantity_in_progress=1,
            quantity_awaiting=15,
            quantity_resolved=7,
            quantity_completed=13,
        )

        # Omitted: the unset row only — the board's default read.
        omitted = await get_stock_report_active_snapshot_version(_ctx(db_session, seeded))
        omitted = omitted["stock_report_snapshot_version"]["progress"]
        assert omitted["by_priority"] == {
            "high": _expect(),
            "medium": _expect(),
            "low": _expect(),
            "unset": unset,
        }
        assert {key: omitted[key] for key in PROGRESS_KEYS} == unset

        # `all`: every live row, the unset one included; the deleted one still not.
        everything = (await _progress(db_session, seeded, "all"))["progress"]
        assert everything["by_priority"] == {
            "high": high,
            "medium": _expect(),
            "low": low,
            "unset": unset,
        }
        assert {key: everything[key] for key in PROGRESS_KEYS} == _expect(
            items_total=4,
            items_completed=3,
            quantity_requested=29,
            quantity_missing=7,
            quantity_target=22,
            quantity_in_queue=3,
            quantity_in_progress=1,
            quantity_awaiting=23,
            quantity_resolved=7,
            quantity_completed=21,
        )

        # One priority: that group alone, the others at zero.
        only_low = (await _progress(db_session, seeded, "low"))["progress"]
        assert {key: only_low[key] for key in PROGRESS_KEYS} == low
        assert only_low["by_priority"]["high"] == _expect()

        # `filtered_snapshot_count` is the stored `snapshot_count` under the filter:
        # it counts the deleted row e (as `snapshot_count` does) where `items_total`
        # does not — 4 against 3 for the prioritised groups.
        snapshot_count = payload["snapshot_count"]
        assert payload["filtered_snapshot_count"] == 4
        assert progress["items_total"] == 3
        for priority, expected in (
            (None, 1),
            ("low", 1),
            ("high", 2),
            ("medium", 1),
            ("all", snapshot_count),
        ):
            active = await get_stock_report_active_snapshot_version(
                _ctx(db_session, seeded, query_params={"priority": priority})
            )
            active = active["stock_report_snapshot_version"]
            assert active["filtered_snapshot_count"] == expected, priority
            assert active["snapshot_count"] == snapshot_count, priority
            assert (await _listed(db_session, seeded, priority))[
                "filtered_snapshot_count"
            ] == expected, priority

        # The same object rides on the list row, under the same filter.
        assert await _listed_progress(db_session, seeded, "high,medium,low") == progress
        assert await _listed_progress(db_session, seeded, None) == omitted
        assert await _listed_progress(db_session, seeded, "all") == everything
        assert await _listed_progress(db_session, seeded, "low") == only_low
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_progress_never_drops_when_scanner_resolves(db_session, monkeypatch):
    """One prioritised row of 10 and the seeded item (4), walked through the real
    commands: in_queue -> awaiting -> back to in_queue (falls, MC-5 parity) ->
    awaiting -> resolved by Scanner (holds: the row's awaiting is 0, the snapshot
    remembers 4)."""
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "teak", 10)])
        await db_session.commit()
        (row_id,) = await _ids(db_session, workspace_id)
        await _CV(db_session, seeded)
        await set_snapshot_position(db_session, row_id, "high", 1)
        await db_session.commit()

        assignment_id = await _assign_seeded_item(db_session, seeded, row_id)
        progress = (await _progress(db_session, seeded))["progress"]
        assert (progress["quantity_in_queue"], progress["quantity_awaiting"]) == (4, 0)
        assert progress["quantity_completed"] == 0

        await _move(db_session, seeded, assignment_id, StockTaskAssignmentStateEnum.AWAITING)
        progress = (await _progress(db_session, seeded))["progress"]
        assert (progress["quantity_in_queue"], progress["quantity_awaiting"]) == (0, 4)
        assert progress["quantity_completed"] == 4

        await _move(db_session, seeded, assignment_id, StockTaskAssignmentStateEnum.IN_QUEUE)
        progress = (await _progress(db_session, seeded))["progress"]
        assert (progress["quantity_in_queue"], progress["quantity_awaiting"]) == (4, 0)

        await _move(db_session, seeded, assignment_id, StockTaskAssignmentStateEnum.AWAITING)
        await _resolve_seeded_item(db_session, seeded, monkeypatch)
        progress = (await _progress(db_session, seeded))["progress"]
        assert progress["quantity_in_queue"] == 0
        assert progress["quantity_awaiting"] == 4
        assert progress["quantity_resolved"] == 4
        assert progress["quantity_completed"] == 4
        assert progress["quantity_target"] == 10
        assert progress["items_completed"] == 0
        row = await db_session.scalar(
            select(StockReportItem.quantity_awaiting).where(
                StockReportItem.client_id == row_id
            )
        )
        assert row == 0
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_closed_version_progress_is_frozen_and_the_list_costs_two_statements(
    db_session, monkeypatch
):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "teak", 10)])
        await db_session.commit()
        (row_id,) = await _ids(db_session, workspace_id)
        v1, _ = await _CV(db_session, seeded)
        await set_snapshot_position(db_session, row_id, "high", 1)
        await db_session.commit()
        assignment_id = await _assign_seeded_item(db_session, seeded, row_id)
        await _move(db_session, seeded, assignment_id, StockTaskAssignmentStateEnum.AWAITING)

        v2, _ = await _CV(db_session, seeded, now=LATER)
        await set_snapshot_position(db_session, row_id, "high", 1)
        await db_session.commit()
        await _resolve_seeded_item(db_session, seeded, monkeypatch)

        async with record_statements(db_session) as statements:
            listed = await list_stock_report_snapshot_versions(
                _ctx(db_session, seeded, query_params={"priority": "high"})
            )
        assert len(statements) == 2, statements
        by_id = {v["client_id"]: v for v in listed["stock_report_snapshot_versions"]}
        assert list(by_id) == [v2["client_id"], v1["client_id"]]

        frozen = by_id[v1["client_id"]]["progress"]
        assert (frozen["quantity_awaiting"], frozen["quantity_resolved"]) == (4, 0)
        assert frozen["quantity_completed"] == 4
        live = by_id[v2["client_id"]]["progress"]
        assert (live["quantity_awaiting"], live["quantity_resolved"]) == (4, 4)
        assert live["quantity_completed"] == 4
        assert (await _progress(db_session, seeded))["progress"] == live

        empty = await list_stock_report_snapshot_versions(
            _ctx(db_session, seeded, query_params={"limit": 50, "offset": 5})
        )
        assert empty["stock_report_snapshot_versions"] == []
        assert empty_version_progress()["by_priority"]["high"] == _expect()
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()
