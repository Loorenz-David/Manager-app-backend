"""Draft versions, step 2 (2026-09-28; plan §4.1, §4.4, §4.6, §4.8, §4.9, §4.11,
§4.12, §6): creating a draft, Scanner rows joining it, the versioned row edits and
their shortcuts, the manual requested quantity, apply-priorities onto a draft,
deleting a draft, the version reads and the membership consistency kind.

Rows are created through the demand service `AD` (the only creator of rows), which
refuses a session already in a transaction, so every test here is a committing test:
`seed -> commit -> AD -> ... -> finally purge + commit`. Every assertion is an outcome
at a public boundary: a command's response, a read's payload, an event, a row.
"""

import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select, text

from beyo_manager.config import Settings
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
    normalize_stock_criteria,
)
from beyo_manager.domain.stock_report.enums import (
    StockReportHistoryRecordTypeEnum,
    StockReportQuantityRequestedSourceEnum,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
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
from beyo_manager.services.commands.stock_report.activate_stock_report_snapshot_version import (
    activate_stock_report_snapshot_version,
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
from beyo_manager.services.commands.stock_report.delete_stock_report_item import (
    delete_stock_report_item,
)
from beyo_manager.services.commands.stock_report.delete_stock_report_snapshot_version import (
    delete_stock_report_snapshot_version,
)
from beyo_manager.services.commands.stock_report.refresh_stock_report_snapshot_version_requested import (
    refresh_stock_report_snapshot_version_requested,
)
from beyo_manager.services.commands.stock_report.repair_stock_report import (
    repair_stock_report,
)
from beyo_manager.services.commands.stock_report.set_stock_report_item_priority import (
    set_stock_report_item_priority,
)
from beyo_manager.services.commands.stock_report.set_stock_report_item_priority_order import (
    set_stock_report_item_priority_order,
)
from beyo_manager.services.commands.stock_report.set_stock_report_item_snapshot_missing_quantity import (
    set_stock_report_item_snapshot_missing_quantity,
)
from beyo_manager.services.commands.stock_report.set_stock_report_item_snapshot_requested_quantity import (
    set_stock_report_item_snapshot_requested_quantity,
)
from beyo_manager.services.commands.stock_report.stock_demand_entries import DemandEntry
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.stock_report.consistency import (
    compute_stock_report_divergences,
)
from beyo_manager.services.queries.stock_report.count_stock_report_draft_versions import (
    count_stock_report_draft_versions,
)
from beyo_manager.services.queries.stock_report.get_stock_report_active_snapshot_version import (
    get_stock_report_active_snapshot_version,
)
from beyo_manager.services.queries.stock_report.get_stock_report_snapshot_version import (
    get_stock_report_snapshot_version,
)
from beyo_manager.services.queries.stock_report.list_stock_report_items import (
    list_stock_report_items,
)
from beyo_manager.services.queries.stock_report.list_stock_report_snapshot_versions import (
    list_stock_report_snapshot_versions,
)
from tests.helpers.statement_listener import record_statements
from tests.helpers.stock_report import (
    assert_stock_report_clean,
    capture_dispatch,
    make_ctx,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
    set_snapshot_position,
    snapshot_positions,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 28, 12, 0, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)
_TIMEOUT_MS = Settings.model_fields["stock_demand_webhook_timeout_ms"].default
_COMMANDS = "beyo_manager.services.commands.stock_report"


def _pin(session, seeded):
    return SimpleNamespace(
        identity=make_ctx(session, seeded).identity,
        workspace=SimpleNamespace(client_id=seeded.workspace.client_id),
        manager=SimpleNamespace(client_id=seeded.manager.client_id),
        task=SimpleNamespace(client_id=seeded.task.client_id),
        item=SimpleNamespace(
            client_id=seeded.item.client_id, article_number=seeded.item.article_number
        ),
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
    await session.commit()  # a read before this autobegan; AD wants a clean session
    result = await apply_stock_demand(
        session,
        workspace_id=workspace_id,
        entries=entries,
        now=NOW,
        deadline=time.monotonic() + 60,
        timeout_ms=_TIMEOUT_MS,
    )
    await session.commit()
    return result


async def _by_token(session, workspace_id):
    rows = (
        await session.execute(
            select(StockReportItem).where(
                StockReportItem.workspace_id == workspace_id,
                StockReportItem.is_deleted.is_(False),
            )
        )
    ).scalars()
    out = {row.properties["wood_group"][0]: row.client_id for row in rows}
    await session.commit()
    return out


def _ctx(session, seeded, *, incoming_data=None, query_params=None, now=NOW):
    return ServiceContext(
        identity=seeded.identity,
        incoming_data=incoming_data or {},
        query_params=query_params or {},
        session=session,
        now=now,
    )


async def _CV(session, seeded, *, body=None, now=NOW, monkeypatch=None):
    captured = (
        capture_dispatch(
            monkeypatch, f"{_COMMANDS}.create_stock_report_snapshot_version.dispatch"
        )
        if monkeypatch is not None
        else None
    )
    result = await create_stock_report_snapshot_version(
        _ctx(session, seeded, incoming_data=body, now=now)
    )
    await session.commit()
    return result["stock_report_snapshot_version"], captured


async def _draft(session, seeded, *, title=None, now=NOW, monkeypatch=None):
    body = {"draft": True}
    if title is not None:
        body["title"] = title
    return await _CV(session, seeded, body=body, now=now, monkeypatch=monkeypatch)


async def _snapshots_of(session, version_id):
    out = {
        snapshot.stock_report_item_id: snapshot
        for snapshot in (
            await session.execute(
                select(StockReportItemSnapshot)
                .where(StockReportItemSnapshot.version_id == version_id)
                .execution_options(populate_existing=True)
            )
        ).scalars()
    }
    return out


async def _version_row(session, version_id):
    return await session.scalar(
        select(StockReportSnapshotVersion)
        .where(StockReportSnapshotVersion.client_id == version_id)
        .execution_options(populate_existing=True)
    )


async def _items(session, seeded, **params):
    params.setdefault("priority", "all")
    params.setdefault("include_zero_requested", True)
    result = await list_stock_report_items(_ctx(session, seeded, query_params=params))
    return {row["client_id"]: row for row in result["stock_report_items"]}


async def _versions(session, seeded, **params):
    result = await list_stock_report_snapshot_versions(
        _ctx(session, seeded, query_params=params)
    )
    return result["stock_report_snapshot_versions"]


async def _draft_count(session, seeded):
    return (await count_stock_report_draft_versions(_ctx(session, seeded)))[
        "draft_count"
    ]


async def _records(session, workspace_id):
    return (
        (
            await session.execute(
                select(StockReportHistoryRecord)
                .where(
                    StockReportHistoryRecord.workspace_id == workspace_id,
                    StockReportHistoryRecord.type
                    != StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
                )
                .order_by(
                    StockReportHistoryRecord.created_at,
                    StockReportHistoryRecord.client_id,
                )
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )


def _versioned(row_id, version_id, **body):
    return {**body, "client_id": row_id, "version_id": version_id}


async def _SP(session, seeded, row_id, priority, *, version_id=None, monkeypatch=None):
    captured = (
        capture_dispatch(
            monkeypatch, f"{_COMMANDS}.set_stock_report_item_priority.dispatch"
        )
        if monkeypatch is not None
        else None
    )
    data = {"client_id": row_id, "priority": priority}
    if version_id is not None:
        data["version_id"] = version_id
    result = await set_stock_report_item_priority(
        _ctx(session, seeded, incoming_data=data)
    )
    await session.commit()
    return result["stock_report_item"], captured


async def _SO(session, seeded, row_id, order, *, version_id=None):
    data = {"client_id": row_id, "priority_order": order}
    if version_id is not None:
        data["version_id"] = version_id
    result = await set_stock_report_item_priority_order(
        _ctx(session, seeded, incoming_data=data)
    )
    await session.commit()
    return result["stock_report_item"]


async def _SM(session, seeded, row_id, value, *, version_id=None, monkeypatch=None):
    captured = (
        capture_dispatch(
            monkeypatch,
            f"{_COMMANDS}.set_stock_report_item_snapshot_missing_quantity.dispatch",
        )
        if monkeypatch is not None
        else None
    )
    data = {"client_id": row_id, "quantity_missing": value}
    if version_id is not None:
        data["version_id"] = version_id
    result = await set_stock_report_item_snapshot_missing_quantity(
        _ctx(session, seeded, incoming_data=data)
    )
    await session.commit()
    return result["stock_report_item"], captured


async def _SR(session, seeded, row_id, value, *, version_id, monkeypatch=None):
    captured = (
        capture_dispatch(
            monkeypatch,
            f"{_COMMANDS}.set_stock_report_item_snapshot_requested_quantity.dispatch",
        )
        if monkeypatch is not None
        else None
    )
    result = await set_stock_report_item_snapshot_requested_quantity(
        _ctx(
            session,
            seeded,
            incoming_data=_versioned(row_id, version_id, quantity_requested=value),
        )
    )
    await session.commit()
    return result["stock_report_item"], captured


async def _apply(
    session, seeded, source_id, *, target_id=None, body=True, monkeypatch=None
):
    captured = (
        capture_dispatch(
            monkeypatch,
            f"{_COMMANDS}.apply_stock_report_snapshot_version_priorities.dispatch",
        )
        if monkeypatch is not None
        else None
    )
    data = {"client_id": source_id}
    if body:
        data["target_version_id"] = target_id
    result = await apply_stock_report_snapshot_version_priorities(
        _ctx(session, seeded, incoming_data=data, now=LATER)
    )
    await session.commit()
    return result, captured


async def _activate(
    session, seeded, version_id, *, body=None, now=LATER, monkeypatch=None
):
    captured = (
        capture_dispatch(
            monkeypatch, f"{_COMMANDS}.activate_stock_report_snapshot_version.dispatch"
        )
        if monkeypatch is not None
        else None
    )
    result = await activate_stock_report_snapshot_version(
        _ctx(
            session,
            seeded,
            incoming_data={**(body or {}), "client_id": version_id},
            now=now,
        )
    )
    await session.commit()
    return result["stock_report_snapshot_version"], captured


async def _refresh(
    session, seeded, version_id, *, body=None, now=LATER, monkeypatch=None
):
    captured = (
        capture_dispatch(
            monkeypatch,
            f"{_COMMANDS}.refresh_stock_report_snapshot_version_requested.dispatch",
        )
        if monkeypatch is not None
        else None
    )
    result = await refresh_stock_report_snapshot_version_requested(
        _ctx(
            session,
            seeded,
            incoming_data={**(body or {}), "client_id": version_id},
            now=now,
        )
    )
    await session.commit()
    return result, captured


async def _progress(session, seeded, version_id, *, priority="all"):
    result = await get_stock_report_snapshot_version(
        _ctx(
            session,
            seeded,
            incoming_data={"client_id": version_id},
            query_params={"priority": priority},
        )
    )
    await session.commit()
    return result["stock_report_snapshot_version"]["progress"]


async def _assign_seeded_item(session, seeded, row_id):
    await create_stock_task_assignments(
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


# ---------------------------------------------------------------------------
# Create draft (§4.1)
# ---------------------------------------------------------------------------


async def test_a_draft_is_live_lists_first_and_leaves_the_board_untouched(
    db_session, monkeypatch
):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10), _entry(1, "b", 4)])
        ids = await _by_token(db_session, workspace_id)
        a, b = ids["a"], ids["b"]
        active, _ = await _CV(db_session, seeded)
        await set_snapshot_position(db_session, a, "high", 1)
        await db_session.commit()
        board_before = await _items(db_session, seeded)
        active_before = await get_stock_report_active_snapshot_version(
            _ctx(db_session, seeded, query_params={"priority": "all"})
        )
        await db_session.commit()

        draft, captured = await _draft(
            db_session,
            seeded,
            title="  Upholstery push  ",
            now=LATER,
            monkeypatch=monkeypatch,
        )

        # The board and the active read are byte-identical before and after.
        assert await _items(db_session, seeded) == board_before
        assert (
            await get_stock_report_active_snapshot_version(
                _ctx(db_session, seeded, query_params={"priority": "all"})
            )
            == active_before
        )
        assert draft["state"] == "draft"
        assert draft["active_at"] is None
        assert draft["title"] == "Upholstery push"
        assert draft["snapshot_count"] == 2
        assert draft["scheduled_activation_at"] is None
        assert draft["scheduled_activation_keeps_active_missing"] is False
        assert [(e.event_name, e.client_id, e.extra) for e in captured] == [
            (
                "stock_report_snapshot_version:created",
                draft["client_id"],
                {"snapshot_count": 2, "state": "draft", "title": "Upholstery push"},
            )
        ]
        # Its snapshots hold nothing of their own.
        snapshots = await _snapshots_of(db_session, draft["client_id"])
        assert set(snapshots) == {a, b}
        assert all(
            (
                s.quantity_requested_scanner,
                s.quantity_requested_manual,
                s.quantity_missing,
                s.priority,
                s.priority_order,
                s.active_at,
                s.closed_at,
            )
            == (None, None, None, None, None, None, None)
            for s in snapshots.values()
        )
        # The read shows the live row, the borrowed missing and the board beside it.
        rows = await _items(db_session, seeded, version_id=draft["client_id"])
        assert rows[a]["snapshot"]["version_id"] == draft["client_id"]
        assert rows[a]["snapshot"]["quantity_requested"] == 10
        assert rows[a]["snapshot"]["quantity_requested_scanner"] == 10
        assert rows[a]["snapshot"]["quantity_requested_source"] == "scanner"
        assert rows[a]["snapshot"]["quantity_missing"] == 0
        assert rows[a]["snapshot"]["quantity_missing_source"] == "active"
        assert rows[a]["snapshot"]["active_quantity_missing"] == 0
        assert rows[a]["snapshot"]["priority"] is None
        # The list: the draft first with `active_at: null`, then the active one.
        listed = await _versions(db_session, seeded)
        assert [(v["client_id"], v["state"]) for v in listed] == [
            (draft["client_id"], "draft"),
            (active["client_id"], "active"),
        ]
        # A draft's progress is live: requested 14 over the two rows.
        # Positions are per version: on the draft both rows are unset (14); on the
        # active version only b is (a is high there).
        assert listed[0]["progress"]["quantity_requested"] == 14
        assert listed[1]["progress"]["quantity_requested"] == 4
        everything = await _versions(db_session, seeded, priority="all")
        assert everything[0]["progress"]["quantity_requested"] == 14
        assert everything[0]["filtered_snapshot_count"] == 2
        # Two drafts coexist, and the count read sees both.
        second, _ = await _draft(db_session, seeded, now=LATER + timedelta(minutes=1))
        assert second["title"] is None
        assert await _draft_count(db_session, seeded) == 2
        assert [
            v["client_id"] for v in await _versions(db_session, seeded, state="draft")
        ] == [
            second["client_id"],
            draft["client_id"],
        ]
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_create_body_rules(db_session, monkeypatch):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        # The documented default body with `draft: false` is a plain active create
        # whose `:created` says `active` (FQ-1).
        version, captured = await _CV(
            db_session,
            seeded,
            body={
                "draft": False,
                "title": None,
                "scheduled_activation_at": None,
                "scheduled_activation_keeps_active_missing": False,
            },
            monkeypatch=monkeypatch,
        )
        assert version["state"] == "active"
        assert captured[-1].extra == {
            "snapshot_count": 0,
            "state": "active",
            "title": None,
        }

        # A schedule with `draft: false` is refused (R-9, FQ-14): a date, or the
        # flag `true` — the defaults above were not.
        for body in (
            {"draft": False, "scheduled_activation_at": "2026-12-01T06:00:00+02:00"},
            {"scheduled_activation_keeps_active_missing": True},
            {"scheduled_activation_at": "2026-12-01T06:00:00+02:00"},
        ):
            with pytest.raises(ValidationError, match="STOCK_REPORT_VERSION_NOT_DRAFT"):
                await create_stock_report_snapshot_version(
                    _ctx(db_session, seeded, incoming_data=body)
                )
            await db_session.rollback()

        # Past or now → 422; naive → 422 (request validation, not a 500).
        with pytest.raises(ValidationError, match="STOCK_REPORT_SCHEDULE_IN_THE_PAST"):
            await create_stock_report_snapshot_version(
                _ctx(
                    db_session,
                    seeded,
                    incoming_data={
                        "draft": True,
                        "scheduled_activation_at": NOW.isoformat(),
                    },
                )
            )
        await db_session.rollback()
        with pytest.raises(ValidationError, match="scheduled_activation_at"):
            await create_stock_report_snapshot_version(
                _ctx(
                    db_session,
                    seeded,
                    incoming_data={
                        "draft": True,
                        "scheduled_activation_at": "2026-12-01T06:00:00",
                    },
                )
            )
        await db_session.rollback()
        with pytest.raises(ValidationError, match="title"):
            await create_stock_report_snapshot_version(
                _ctx(
                    db_session,
                    seeded,
                    incoming_data={"draft": True, "title": "x" * 201},
                )
            )
        await db_session.rollback()

        # A `+02:00` schedule is stored and echoed in UTC (Q-5, FQ-8); the flag
        # without a schedule is stored (FQ-16).
        scheduled, _ = await _CV(
            db_session,
            seeded,
            body={
                "draft": True,
                "title": " " * 2 + "a" * 200 + " " * 2,
                "scheduled_activation_at": "2026-12-01T06:00:00+02:00",
                "scheduled_activation_keeps_active_missing": True,
            },
        )
        assert scheduled["scheduled_activation_at"] == "2026-12-01T04:00:00+00:00"
        assert scheduled["scheduled_activation_keeps_active_missing"] is True
        assert scheduled["title"] == "a" * 200
        stored = await _version_row(db_session, scheduled["client_id"])
        assert stored.scheduled_activation_at == datetime(
            2026, 12, 1, 4, tzinfo=timezone.utc
        )
        await db_session.commit()
        flagged, _ = await _CV(
            db_session,
            seeded,
            body={"draft": True, "scheduled_activation_keeps_active_missing": True},
        )
        assert flagged["scheduled_activation_keeps_active_missing"] is True
        assert flagged["scheduled_activation_at"] is None
        assert await _draft_count(db_session, seeded) == 2
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# Live membership (§4.9)
# ---------------------------------------------------------------------------


async def test_a_scanner_row_joins_every_draft_but_never_the_active_version(db_session):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10)])
        active, _ = await _CV(db_session, seeded)
        d1, _ = await _draft(db_session, seeded)
        d2, _ = await _draft(db_session, seeded, now=LATER)

        result = await _AD(
            db_session, workspace_id, [_entry(0, "c", 0), _entry(1, "d", 5)]
        )
        ids = await _by_token(db_session, workspace_id)
        c, d = ids["c"], ids["d"]

        # The row's `:created` is the only event; no snapshot event.
        assert sorted((e.event_name, e.client_id) for e in result.events) == sorted(
            [("stock_report_item:created", c), ("stock_report_item:created", d)]
        )
        for draft in (d1, d2):
            snapshots = await _snapshots_of(db_session, draft["client_id"])
            assert {c, d} <= set(snapshots)
            for row_id in (c, d):
                s = snapshots[row_id]
                assert (
                    s.quantity_requested_scanner,
                    s.quantity_missing,
                    s.priority,
                    s.active_at,
                ) == (None, None, None, None)
            assert (
                await _version_row(db_session, draft["client_id"])
            ).snapshot_count == 3
        assert set(await _snapshots_of(db_session, active["client_id"])) == {ids["a"]}
        assert (await _version_row(db_session, active["client_id"])).snapshot_count == 1
        await db_session.commit()
        # The zero-quantity row is in the draft read only when zero rows are asked for.
        rows = await _items(
            db_session, seeded, version_id=d1["client_id"], include_zero_requested=False
        )
        assert set(rows) == {ids["a"], d}
        rows = await _items(db_session, seeded, version_id=d1["client_id"])
        assert rows[c]["snapshot"]["quantity_requested"] == 0
        # A second post for the same rows adds nothing.
        await _AD(db_session, workspace_id, [_entry(0, "c", 2)])
        assert (await _version_row(db_session, d1["client_id"])).snapshot_count == 3
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# Versioned edits (§4.6) and the history rule (§3.5, Q-10)
# ---------------------------------------------------------------------------


async def test_versioned_priority_edits_group_per_version_and_write_history_only_on_the_active(
    db_session, monkeypatch
):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(
            db_session, workspace_id, [_entry(i, t, 10) for i, t in enumerate("abc")]
        )
        ids = await _by_token(db_session, workspace_id)
        a, b, c = ids["a"], ids["b"], ids["c"]
        active, _ = await _CV(db_session, seeded)
        for row_id in (a, b, c):
            await _SP(db_session, seeded, row_id, "high")
        draft, _ = await _draft(db_session, seeded)
        records_before = len(await _records(db_session, workspace_id))
        await db_session.commit()

        payload, captured = await _SP(
            db_session,
            seeded,
            a,
            "high",
            version_id=draft["client_id"],
            monkeypatch=monkeypatch,
        )
        assert payload["snapshot"]["version_id"] == draft["client_id"]
        assert (
            payload["snapshot"]["priority"],
            payload["snapshot"]["priority_order"],
        ) == ("high", 1)
        assert [e.extra["version_id"] for e in captured] == [draft["client_id"]]
        await _SP(db_session, seeded, c, "high", version_id=draft["client_id"])
        draft_positions = await snapshot_positions(db_session, workspace_id)
        # `snapshot_positions` reads every open snapshot: fold by version by hand.
        by_version = {}
        for s in (
            await db_session.execute(
                select(StockReportItemSnapshot).where(
                    StockReportItemSnapshot.workspace_id == workspace_id
                )
            )
        ).scalars():
            by_version.setdefault(s.version_id, {})[s.stock_report_item_id] = (
                s.priority.value if s.priority else None,
                s.priority_order,
            )
        assert by_version[draft["client_id"]] == {
            a: ("high", 1),
            b: (None, None),
            c: ("high", 2),
        }
        assert by_version[active["client_id"]] == {
            a: ("high", 1),
            b: ("high", 2),
            c: ("high", 3),
        }
        del draft_positions
        # In-group move on the draft: c to 1 → [c1, a2]; the active group untouched.
        moved = await _SO(db_session, seeded, c, 1, version_id=draft["client_id"])
        assert (
            moved["snapshot"]["priority_order"],
            moved["snapshot"]["version_id"],
        ) == (1, draft["client_id"])
        snapshots = await _snapshots_of(db_session, draft["client_id"])
        assert (snapshots[c].priority_order, snapshots[a].priority_order) == (1, 2)
        # No history for any draft edit.
        assert len(await _records(db_session, workspace_id)) == records_before
        await db_session.commit()

        # Q-10: Scanner raised the row to 25 after the freeze; a priority change
        # through the ACTIVE version's id records the frozen 10 with source scanner.
        await _AD(db_session, workspace_id, [_entry(0, "b", 25)])
        await _SP(db_session, seeded, b, "low", version_id=active["client_id"])
        record = (await _records(db_session, workspace_id))[-1]
        assert record.stock_report_item_id == b
        assert record.type is StockReportHistoryRecordTypeEnum.PRIORITY_CHANGE
        assert (record.quantity_requested, record.quantity_requested_source) == (
            10,
            StockReportQuantityRequestedSourceEnum.SCANNER,
        )
        await db_session.commit()

        # A row absent from the version → 404; a foreign / absent version → 404.
        await db_session.execute(
            text(
                "DELETE FROM stock_report_item_snapshots WHERE version_id = :v AND stock_report_item_id = :r"
            ),
            {"v": draft["client_id"], "r": b},
        )
        await db_session.commit()
        with pytest.raises(NotFound, match="Stock report item not found"):
            await set_stock_report_item_priority(
                _ctx(
                    db_session,
                    seeded,
                    incoming_data=_versioned(b, draft["client_id"], priority="low"),
                )
            )
        await db_session.rollback()
        with pytest.raises(NotFound, match="Stock report snapshot version not found"):
            await set_stock_report_item_priority(
                _ctx(
                    db_session,
                    seeded,
                    incoming_data=_versioned(a, "srv_absent", priority="low"),
                )
            )
        await db_session.rollback()
        # A closed version → 422.
        await _CV(db_session, seeded, now=LATER)
        for command, body in (
            (set_stock_report_item_priority, {"priority": "low"}),
            (set_stock_report_item_priority_order, {"priority_order": 1}),
            (set_stock_report_item_snapshot_missing_quantity, {"quantity_missing": 1}),
            (
                set_stock_report_item_snapshot_requested_quantity,
                {"quantity_requested": 1},
            ),
        ):
            with pytest.raises(ValidationError, match="STOCK_REPORT_VERSION_IS_CLOSED"):
                await command(
                    _ctx(
                        db_session,
                        seeded,
                        incoming_data=_versioned(a, active["client_id"], **body),
                    )
                )
            await db_session.rollback()
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_shortcuts_never_target_a_draft(db_session):
    """With a draft and no active version, the v6 routes answer as they always did:
    422 `STOCK_REPORT_NO_ACTIVE_SNAPSHOT` (P-7)."""
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10)])
        (a,) = (await _by_token(db_session, workspace_id)).values()
        draft, _ = await _draft(db_session, seeded)
        for command, body in (
            (set_stock_report_item_priority, {"priority": "high"}),
            (set_stock_report_item_priority_order, {"priority_order": 1}),
            (set_stock_report_item_snapshot_missing_quantity, {"quantity_missing": 1}),
        ):
            with pytest.raises(
                ValidationError, match="STOCK_REPORT_NO_ACTIVE_SNAPSHOT"
            ):
                await command(
                    _ctx(db_session, seeded, incoming_data={**body, "client_id": a})
                )
            await db_session.rollback()
        # The draft is untouched by the refusals.
        snapshots = await _snapshots_of(db_session, draft["client_id"])
        assert (snapshots[a].priority, snapshots[a].quantity_missing) == (None, None)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_versioned_missing_types_clears_and_refuses_null_on_the_active(
    db_session, monkeypatch
):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10), _entry(1, "b", 10)])
        ids = await _by_token(db_session, workspace_id)
        a, b = ids["a"], ids["b"]
        active, _ = await _CV(db_session, seeded)
        await _SM(db_session, seeded, a, 3)  # the shortcut, on the board
        draft, _ = await _draft(db_session, seeded)
        V = draft["client_id"]

        rows = await _items(db_session, seeded, version_id=V)
        assert (
            rows[a]["snapshot"]["quantity_missing"],
            rows[a]["snapshot"]["quantity_missing_source"],
        ) == (3, "active")

        typed, captured = await _SM(
            db_session, seeded, a, 2, version_id=V, monkeypatch=monkeypatch
        )
        assert (
            typed["snapshot"]["quantity_missing"],
            typed["snapshot"]["quantity_missing_source"],
        ) == (2, "own")
        assert typed["snapshot"]["active_quantity_missing"] == 3
        assert [e.extra["quantity_missing"] for e in captured] == [2]
        # A board change is visible on the draft's borrowing rows next read.
        await _SM(db_session, seeded, b, 4)
        rows = await _items(db_session, seeded, version_id=V)
        assert (
            rows[b]["snapshot"]["quantity_missing"],
            rows[b]["snapshot"]["quantity_missing_source"],
        ) == (4, "active")
        assert rows[a]["snapshot"]["quantity_missing"] == 2  # typed, not following
        # `null` clears; `null` again is a no-op.
        cleared, captured = await _SM(
            db_session, seeded, a, None, version_id=V, monkeypatch=monkeypatch
        )
        assert (
            cleared["snapshot"]["quantity_missing"],
            cleared["snapshot"]["quantity_missing_source"],
        ) == (3, "active")
        assert [e.extra["quantity_missing"] for e in captured] == [None]
        _, captured = await _SM(
            db_session, seeded, a, None, version_id=V, monkeypatch=monkeypatch
        )
        assert captured == []
        # `null` on the active version → 422.
        with pytest.raises(ValidationError, match="STOCK_REPORT_VERSION_NOT_DRAFT"):
            await set_stock_report_item_snapshot_missing_quantity(
                _ctx(
                    db_session,
                    seeded,
                    incoming_data=_versioned(
                        a, active["client_id"], quantity_missing=None
                    ),
                )
            )
        await db_session.rollback()
        # The ceiling on a draft is the effective requested minus live coverage:
        # 10 → 11 refused; with a manual 5, 6 refused and 5 accepted.
        with pytest.raises(
            ValidationError, match="STOCK_REPORT_MISSING_EXCEEDS_CEILING"
        ):
            await set_stock_report_item_snapshot_missing_quantity(
                _ctx(
                    db_session,
                    seeded,
                    incoming_data=_versioned(a, V, quantity_missing=11),
                )
            )
        await db_session.rollback()
        await _SR(db_session, seeded, a, 5, version_id=V)
        with pytest.raises(
            ValidationError, match="STOCK_REPORT_MISSING_EXCEEDS_CEILING"
        ):
            await set_stock_report_item_snapshot_missing_quantity(
                _ctx(
                    db_session,
                    seeded,
                    incoming_data=_versioned(a, V, quantity_missing=6),
                )
            )
        await db_session.rollback()
        accepted, _ = await _SM(db_session, seeded, a, 5, version_id=V)
        assert accepted["snapshot"]["quantity_missing"] == 5
        # The versioned route with the active id is the shortcut's twin.
        twin, _ = await _SM(db_session, seeded, b, 1, version_id=active["client_id"])
        assert (
            twin["snapshot"]["version_id"],
            twin["snapshot"]["quantity_missing"],
        ) == (active["client_id"], 1)
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# The manual requested quantity (§4.11)
# ---------------------------------------------------------------------------


async def test_requested_quantity_on_a_draft_and_on_the_active_version(
    db_session, monkeypatch
):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10), _entry(1, "b", 4)])
        ids = await _by_token(db_session, workspace_id)
        a, b = ids["a"], ids["b"]
        active, _ = await _CV(db_session, seeded)
        draft, _ = await _draft(db_session, seeded)
        A, D = active["client_id"], draft["client_id"]
        records_before = len(await _records(db_session, workspace_id))
        await db_session.commit()

        # Set on a draft: effective = the value, scanner = live, source manual; no history.
        payload, captured = await _SR(
            db_session, seeded, a, 7, version_id=D, monkeypatch=monkeypatch
        )
        s = payload["snapshot"]
        assert (
            s["quantity_requested"],
            s["quantity_requested_scanner"],
            s["quantity_requested_source"],
        ) == (7, 10, "manual")
        assert [
            (
                e.extra["quantity_requested_scanner"],
                e.extra["quantity_requested_manual"],
            )
            for e in captured
        ] == [(None, 7)]
        assert len(await _records(db_session, workspace_id)) == records_before
        await db_session.commit()
        # Scanner moves: the draft shows the new live value beside the manual one;
        # the active version's frozen value is untouched.
        await _AD(db_session, workspace_id, [_entry(0, "a", 14)])
        draft_rows = await _items(db_session, seeded, version_id=D)
        assert (
            draft_rows[a]["snapshot"]["quantity_requested"],
            draft_rows[a]["snapshot"]["quantity_requested_scanner"],
        ) == (7, 14)
        board = await _items(db_session, seeded)
        assert (
            board[a]["snapshot"]["quantity_requested"],
            board[a]["snapshot"]["quantity_requested_scanner"],
        ) == (10, 10)
        # Pin (card 6): typing the value Scanner shows stores it; the draft holds it
        # when Scanner moves.
        pinned, captured = await _SR(
            db_session, seeded, b, 4, version_id=D, monkeypatch=monkeypatch
        )
        assert pinned["snapshot"]["quantity_requested_source"] == "manual"
        assert len(captured) == 1
        await _AD(db_session, workspace_id, [_entry(0, "b", 9)])
        draft_rows = await _items(db_session, seeded, version_id=D)
        assert (
            draft_rows[b]["snapshot"]["quantity_requested"],
            draft_rows[b]["snapshot"]["quantity_requested_scanner"],
        ) == (4, 9)
        # Same stored manual value → no event; a revert on a row with no override → no event.
        _, captured = await _SR(
            db_session, seeded, b, 4, version_id=D, monkeypatch=monkeypatch
        )
        assert captured == []
        reverted, captured = await _SR(
            db_session, seeded, a, None, version_id=D, monkeypatch=monkeypatch
        )
        assert (
            reverted["snapshot"]["quantity_requested"],
            reverted["snapshot"]["quantity_requested_source"],
        ) == (14, "scanner")
        assert [e.extra["quantity_requested_manual"] for e in captured] == [None]
        _, captured = await _SR(
            db_session, seeded, a, None, version_id=D, monkeypatch=monkeypatch
        )
        assert captured == []

        # On the active version: the override moves the progress target and writes
        # a `quantity_requested_override` record with source manual.
        await _SP(db_session, seeded, a, "high")
        payload, captured = await _SR(
            db_session, seeded, a, 12, version_id=A, monkeypatch=monkeypatch
        )
        s = payload["snapshot"]
        assert (
            s["quantity_requested"],
            s["quantity_requested_scanner"],
            s["quantity_requested_source"],
        ) == (12, 10, "manual")
        assert [
            (
                e.extra["quantity_requested_scanner"],
                e.extra["quantity_requested_manual"],
            )
            for e in captured
        ] == [(10, 12)]
        record = (await _records(db_session, workspace_id))[-1]
        assert (
            record.type is StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_OVERRIDE
        )
        assert (
            record.stock_report_item_id,
            record.quantity_requested,
            record.quantity_requested_source,
        ) == (a, 12, StockReportQuantityRequestedSourceEnum.MANUAL)
        assert (record.priority.value, record.priority_order) == ("high", 1)
        await db_session.commit()
        progress = (
            await get_stock_report_active_snapshot_version(
                _ctx(db_session, seeded, query_params={"priority": "high"})
            )
        )["stock_report_snapshot_version"]["progress"]
        assert (progress["quantity_requested"], progress["quantity_target"]) == (12, 12)
        await db_session.commit()
        # Revert on the active version: the frozen value, a record with source scanner.
        reverted, _ = await _SR(db_session, seeded, a, None, version_id=A)
        assert (
            reverted["snapshot"]["quantity_requested"],
            reverted["snapshot"]["quantity_requested_source"],
        ) == (10, "scanner")
        record = (await _records(db_session, workspace_id))[-1]
        assert (
            record.type,
            record.quantity_requested,
            record.quantity_requested_source,
        ) == (
            StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_OVERRIDE,
            10,
            StockReportQuantityRequestedSourceEnum.SCANNER,
        )
        await db_session.commit()

        # Lowering below the covered quantity on the active version clamps its
        # missing in the same request (one coalesced event); a draft is not clamped.
        await _assign_seeded_item(db_session, seeded, a)  # in_queue 1
        await _SM(db_session, seeded, a, 9)  # ceiling 10 - 1
        await _SM(db_session, seeded, a, 9, version_id=D)
        clamped, captured = await _SR(
            db_session, seeded, a, 5, version_id=A, monkeypatch=monkeypatch
        )
        assert (
            clamped["snapshot"]["quantity_requested"],
            clamped["snapshot"]["quantity_missing"],
        ) == (5, 4)  # clamped to 5 - 1
        assert [
            (
                e.client_id,
                e.extra["quantity_requested_manual"],
                e.extra["quantity_missing"],
            )
            for e in captured
        ] == [(clamped["snapshot"]["client_id"], 5, 4)]
        untouched, _ = await _SR(db_session, seeded, a, 5, version_id=D)
        assert (
            untouched["snapshot"]["quantity_requested"],
            untouched["snapshot"]["quantity_missing"],
        ) == (5, 9)
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# apply-priorities with a target (§4.4)
# ---------------------------------------------------------------------------


async def test_apply_priorities_onto_a_draft_and_the_refusals(db_session, monkeypatch):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10), _entry(1, "b", 10)])
        ids = await _by_token(db_session, workspace_id)
        a, b = ids["a"], ids["b"]
        v1, _ = await _CV(db_session, seeded)
        await _SP(db_session, seeded, a, "high")
        await _SP(db_session, seeded, b, "high")
        draft, _ = await _draft(db_session, seeded)
        D = draft["client_id"]
        await _SR(db_session, seeded, a, 3, version_id=D)  # a manual value on the draft
        records_before = len(await _records(db_session, workspace_id))
        await db_session.commit()

        # Active → draft: positions copied, no history, the draft's snapshots answer.
        result, captured = await _apply(
            db_session, seeded, v1["client_id"], target_id=D, monkeypatch=monkeypatch
        )
        assert result["changed"] == 2
        assert {
            row["snapshot"]["version_id"] for row in result["stock_report_items"]
        } == {D}
        assert {e.extra["version_id"] for e in captured} == {D}
        snapshots = await _snapshots_of(db_session, D)
        assert {
            r: (s.priority.value, s.priority_order) for r, s in snapshots.items()
        } == {a: ("high", 1), b: ("high", 2)}
        assert len(await _records(db_session, workspace_id)) == records_before
        await db_session.commit()

        # Refusals.
        with pytest.raises(
            ValidationError, match="STOCK_REPORT_SOURCE_VERSION_IS_ACTIVE"
        ):
            await _apply(db_session, seeded, v1["client_id"], body=False)
        await db_session.rollback()
        with pytest.raises(ValidationError, match="STOCK_REPORT_SOURCE_IS_TARGET"):
            await _apply(db_session, seeded, D, target_id=D)
        await db_session.rollback()
        with pytest.raises(ValidationError, match="STOCK_REPORT_SOURCE_IS_TARGET"):
            await _apply(db_session, seeded, v1["client_id"], target_id=v1["client_id"])
        await db_session.rollback()
        with pytest.raises(NotFound):
            await _apply(db_session, seeded, D, target_id="srv_absent")
        await db_session.rollback()

        # Draft → the active version (no body): history written, and the draft's
        # manual value is NOT copied. Reorder the draft first so something changes.
        await _SO(db_session, seeded, b, 1, version_id=D)
        result, _ = await _apply(db_session, seeded, D, body=False)
        assert result["changed"] == 2
        board = await _items(db_session, seeded)
        assert (
            board[b]["snapshot"]["priority_order"],
            board[a]["snapshot"]["priority_order"],
        ) == (1, 2)
        assert board[a]["snapshot"]["quantity_requested_source"] == "scanner"
        assert len(await _records(db_session, workspace_id)) == records_before + 2
        await db_session.commit()

        # A closed target is refused.
        v2, _ = await _CV(db_session, seeded, now=LATER)
        with pytest.raises(
            ValidationError, match="STOCK_REPORT_TARGET_VERSION_IS_CLOSED"
        ):
            await _apply(db_session, seeded, D, target_id=v1["client_id"])
        await db_session.rollback()
        # Closed → draft works (v1 closed holding b1 a2; put the draft back to a1 b2 first).
        await _SO(db_session, seeded, a, 1, version_id=D)
        result, _ = await _apply(db_session, seeded, v1["client_id"], target_id=D)
        assert result["changed"] == 2
        snapshots = await _snapshots_of(db_session, D)
        assert (snapshots[b].priority_order, snapshots[a].priority_order) == (1, 2)
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# Delete draft (§4.8)
# ---------------------------------------------------------------------------


async def test_delete_draft_removes_it_and_refuses_activated_versions(
    db_session, monkeypatch
):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10)])
        active, _ = await _CV(db_session, seeded)
        draft, _ = await _draft(db_session, seeded)
        D = draft["client_id"]
        board_before = await _items(db_session, seeded)
        assert await _draft_count(db_session, seeded) == 1

        captured = capture_dispatch(
            monkeypatch, f"{_COMMANDS}.delete_stock_report_snapshot_version.dispatch"
        )
        result = await delete_stock_report_snapshot_version(
            _ctx(db_session, seeded, incoming_data={"client_id": D})
        )
        await db_session.commit()
        assert result == {"client_id": D}
        assert [(e.event_name, e.client_id, e.extra) for e in captured] == [
            ("stock_report_snapshot_version:deleted", D, {})
        ]
        assert await _version_row(db_session, D) is None
        assert await _snapshots_of(db_session, D) == {}
        assert await _items(db_session, seeded) == board_before
        assert await _draft_count(db_session, seeded) == 0

        with pytest.raises(ValidationError, match="STOCK_REPORT_VERSION_NOT_DRAFT"):
            await delete_stock_report_snapshot_version(
                _ctx(
                    db_session, seeded, incoming_data={"client_id": active["client_id"]}
                )
            )
        await db_session.rollback()
        with pytest.raises(NotFound):
            await delete_stock_report_snapshot_version(
                _ctx(db_session, seeded, incoming_data={"client_id": D})
            )
        await db_session.rollback()
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# Reads (§6): `version_id`, `state`, the single-version read, the draft count
# ---------------------------------------------------------------------------


async def test_version_reads(db_session):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    foreign = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id, foreign_id = seeded.workspace.client_id, foreign.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10), _entry(1, "b", 6)])
        ids = await _by_token(db_session, workspace_id)
        a, b = ids["a"], ids["b"]
        v1, _ = await _CV(db_session, seeded)
        await _assign_seeded_item(db_session, seeded, a)  # in_queue 1, live
        await _SM(db_session, seeded, a, 3)
        d1, _ = await _draft(db_session, seeded, now=NOW + timedelta(minutes=1))
        d2, _ = await _draft(db_session, seeded, now=NOW + timedelta(minutes=2))
        await _draft(db_session, foreign)
        v2, _ = await _CV(db_session, seeded, now=LATER)  # closes v1

        # A draft read: live counters, live requested, borrowed missing from v2 (0 now).
        rows = await _items(db_session, seeded, version_id=d1["client_id"])
        assert rows[a]["snapshot"]["quantity_in_queue"] == 1
        assert rows[a]["snapshot"]["quantity_requested"] == 10
        assert (
            rows[a]["snapshot"]["quantity_missing"],
            rows[a]["snapshot"]["quantity_missing_source"],
        ) == (0, "active")
        # A closed read: frozen counters, frozen requested, and the current board's missing beside it.
        await _SM(db_session, seeded, a, 2)  # on v2
        await _AD(db_session, workspace_id, [_entry(0, "a", 30)])
        closed = await _items(db_session, seeded, version_id=v1["client_id"])
        assert closed[a]["snapshot"]["quantity_requested"] == 10
        assert closed[a]["snapshot"]["quantity_in_queue"] == 1
        assert (
            closed[a]["snapshot"]["quantity_missing"],
            closed[a]["snapshot"]["active_quantity_missing"],
        ) == (3, 2)
        assert closed[a]["snapshot"]["closed_at"] == LATER.isoformat()
        # `missing_only` on a draft reads the effective missing: a borrows 2, b typed 0.
        await _SM(db_session, seeded, b, 0, version_id=d1["client_id"])
        await _SM(db_session, seeded, b, 1)  # the board says 1 for b; the draft typed 0
        missing = await _items(
            db_session, seeded, version_id=d1["client_id"], missing_only=True
        )
        assert set(missing) == {a}
        # `priority` omitted → the draft's null-priority rows; `all` → every row.
        await _SP(db_session, seeded, a, "high", version_id=d1["client_id"])
        assert set(
            await _items(db_session, seeded, version_id=d1["client_id"], priority=None)
        ) == {b}
        assert set(await _items(db_session, seeded, version_id=d1["client_id"])) == {
            a,
            b,
        }
        # Refusals.
        with pytest.raises(
            ValidationError, match="STOCK_REPORT_LIVE_STOCK_FILTER_CONFLICT"
        ):
            await list_stock_report_items(
                _ctx(
                    db_session,
                    seeded,
                    query_params={"version_id": d1["client_id"], "live_stock": True},
                )
            )
        await db_session.rollback()
        with pytest.raises(NotFound):
            await list_stock_report_items(
                _ctx(db_session, seeded, query_params={"version_id": "srv_absent"})
            )
        await db_session.rollback()

        # The list and its `state` filter (G-2): drafts first, newest created first.
        listed = await _versions(db_session, seeded)
        assert [v["client_id"] for v in listed] == [
            d2["client_id"],
            d1["client_id"],
            v2["client_id"],
            v1["client_id"],
        ]
        assert [v["state"] for v in listed] == ["draft", "draft", "active", "closed"]
        assert [
            v["client_id"]
            for v in await _versions(db_session, seeded, state="active,closed")
        ] == [v2["client_id"], v1["client_id"]]
        assert [
            v["client_id"]
            for v in await _versions(db_session, seeded, state="draft, ,closed")
        ] == [d2["client_id"], d1["client_id"], v1["client_id"]]
        for bad in ("all", "active,x"):
            with pytest.raises(
                ValidationError, match="STOCK_REPORT_UNKNOWN_VERSION_STATE"
            ):
                await _versions(db_session, seeded, state=bad)
            await db_session.rollback()
        # The single-version read, any state; `active` still the active read.
        one = await get_stock_report_snapshot_version(
            _ctx(
                db_session,
                seeded,
                incoming_data={"client_id": d1["client_id"]},
                query_params={"priority": "all"},
            )
        )
        one = one["stock_report_snapshot_version"]
        assert (one["client_id"], one["state"], one["filtered_snapshot_count"]) == (
            d1["client_id"],
            "draft",
            2,
        )
        assert one["progress"]["quantity_requested"] == 36  # live: 30 + 6
        with pytest.raises(NotFound):
            await get_stock_report_snapshot_version(
                _ctx(db_session, seeded, incoming_data={"client_id": "srv_absent"})
            )
        await db_session.rollback()
        with pytest.raises(NotFound):
            await get_stock_report_snapshot_version(
                _ctx(
                    db_session,
                    seeded,
                    incoming_data={
                        "client_id": (await _versions(db_session, foreign))[0][
                            "client_id"
                        ]
                    },
                )
            )
        await db_session.rollback()
        # The draft count (G-3): this workspace's two, one statement.
        async with record_statements(db_session) as statements:
            assert await _draft_count(db_session, seeded) == 2
        assert len(statements) == 1
        assert await _draft_count(db_session, foreign) == 1
        await db_session.commit()
        await delete_stock_report_snapshot_version(
            _ctx(db_session, seeded, incoming_data={"client_id": d2["client_id"]})
        )
        await db_session.commit()
        assert await _draft_count(db_session, seeded) == 1
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await purge_stock_report_workspace(db_session, foreign_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# Membership consistency (§4.12) and the cascade (§4.7)
# ---------------------------------------------------------------------------


async def test_membership_consistency_and_repair(db_session):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10), _entry(1, "b", 10)])
        ids = await _by_token(db_session, workspace_id)
        a, b = ids["a"], ids["b"]
        active, _ = await _CV(db_session, seeded)
        draft, _ = await _draft(db_session, seeded)
        D = draft["client_id"]
        # A row created since is in the draft but not in the active version: clean.
        await _AD(db_session, workspace_id, [_entry(0, "c", 1)])
        c = (await _by_token(db_session, workspace_id))["c"]
        assert await compute_stock_report_divergences(db_session, workspace_id) == []

        # A missing snapshot: reported against the version, repaired by insert.
        await db_session.execute(
            text(
                "DELETE FROM stock_report_item_snapshots WHERE version_id = :v AND stock_report_item_id = :r"
            ),
            {"v": D, "r": b},
        )
        await db_session.commit()
        assert await compute_stock_report_divergences(db_session, workspace_id) == [
            {
                "kind": "draft_membership_mismatch",
                "client_id": D,
                "field": "stock_report_item_id",
                "stored": None,
                "expected": b,
            }
        ]
        repaired = await repair_stock_report(_ctx(db_session, seeded))
        await db_session.commit()
        assert [d["kind"] for d in repaired["repaired"]] == [
            "draft_membership_mismatch"
        ]
        snapshots = await _snapshots_of(db_session, D)
        assert set(snapshots) == {a, b, c}
        assert (
            snapshots[b].quantity_requested_scanner,
            snapshots[b].quantity_missing,
            snapshots[b].active_at,
        ) == (None, None, None)
        assert (await _version_row(db_session, D)).snapshot_count == 3
        assert await compute_stock_report_divergences(db_session, workspace_id) == []
        await db_session.commit()

        # A stray snapshot of a deleted row, holding high 1 above c at high 2:
        # removed, the gap closed, the count decremented (Q-18).
        await _SP(db_session, seeded, b, "high", version_id=D)
        await _SP(db_session, seeded, c, "high", version_id=D)
        await db_session.execute(
            text(
                "UPDATE stock_report_items SET is_deleted = true WHERE client_id = :r"
            ),
            {"r": b},
        )
        await db_session.commit()
        found = await compute_stock_report_divergences(db_session, workspace_id)
        assert [d for d in found if d["kind"] == "draft_membership_mismatch"] == [
            {
                "kind": "draft_membership_mismatch",
                "client_id": D,
                "field": "stock_report_item_id",
                "stored": b,
                "expected": None,
            }
        ]
        repaired = await repair_stock_report(_ctx(db_session, seeded))
        await db_session.commit()
        assert {d["kind"] for d in repaired["repaired"]} >= {
            "draft_membership_mismatch"
        }
        snapshots = await _snapshots_of(db_session, D)
        assert set(snapshots) == {a, c}
        assert (snapshots[c].priority.value, snapshots[c].priority_order) == ("high", 1)
        assert (await _version_row(db_session, D)).snapshot_count == 2
        assert await compute_stock_report_divergences(db_session, workspace_id) == []
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_deleting_a_row_removes_it_from_every_draft(db_session):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10), _entry(1, "b", 10)])
        ids = await _by_token(db_session, workspace_id)
        a, b = ids["a"], ids["b"]
        active, _ = await _CV(db_session, seeded)
        await _SP(db_session, seeded, a, "high")
        await _SP(db_session, seeded, b, "high")
        drafts = [
            (await _draft(db_session, seeded))[0],
            (await _draft(db_session, seeded, now=LATER))[0],
        ]
        for draft in drafts:
            await _SP(db_session, seeded, a, "high", version_id=draft["client_id"])
            await _SP(db_session, seeded, b, "high", version_id=draft["client_id"])

        await delete_stock_report_item(
            _ctx(db_session, seeded, incoming_data={"client_id": a})
        )
        await db_session.commit()

        closed = (await _snapshots_of(db_session, active["client_id"]))[a]
        assert closed.closed_at == NOW
        board = await _items(db_session, seeded)
        assert set(board) == {b} and board[b]["snapshot"]["priority_order"] == 1
        for draft in drafts:
            snapshots = await _snapshots_of(db_session, draft["client_id"])
            assert set(snapshots) == {b}
            assert snapshots[b].priority_order == 1
            assert (
                await _version_row(db_session, draft["client_id"])
            ).snapshot_count == 1
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_draft_snapshot_count_follows_membership(db_session):
    """`snapshot_count` on a draft is its live size: a row that joins raises it and
    a repair's insert keeps the two in step (an aggregate check of the whole file)."""
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        draft, _ = await _draft(db_session, seeded)
        assert draft["snapshot_count"] == 0
        await _AD(
            db_session, workspace_id, [_entry(i, t, 1) for i, t in enumerate("abc")]
        )
        stored = await _version_row(db_session, draft["client_id"])
        held = await db_session.scalar(
            select(func.count())
            .select_from(StockReportItemSnapshot)
            .where(StockReportItemSnapshot.version_id == draft["client_id"])
        )
        assert (stored.snapshot_count, held) == (3, 3)
        listed = await _versions(db_session, seeded, priority="all")
        assert (listed[0]["snapshot_count"], listed[0]["filtered_snapshot_count"]) == (
            3,
            3,
        )
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# Activation by hand (§4.2, step 3 of §12) and the refresh (§4.3)
# ---------------------------------------------------------------------------


async def test_activation_freezes_settles_the_missing_and_closes_the_board(
    db_session, monkeypatch
):
    """`keep_active_missing: true`: a typed draft value stays, an untyped row carries
    the closing board's missing, both clamped to the live ceiling; the Scanner value
    frozen is the live one of activation time; manual overrides survive; the
    previous version closes with frozen counters; one `priority_change` per
    prioritised row with the effective value; no per-snapshot event (P-16)."""
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(
            db_session,
            workspace_id,
            [_entry(0, "a", 10), _entry(1, "b", 4), _entry(2, "c", 6)],
        )
        ids = await _by_token(db_session, workspace_id)
        a, b, c = ids["a"], ids["b"], ids["c"]
        v1, _ = await _CV(db_session, seeded)
        await _SP(db_session, seeded, a, "high")
        await _assign_seeded_item(db_session, seeded, a)  # a: in_queue 1, live
        await _SM(db_session, seeded, a, 3)
        await _SM(db_session, seeded, b, 2)
        draft, _ = await _draft(
            db_session, seeded, title="Monday", now=NOW + timedelta(minutes=1)
        )
        D = draft["client_id"]
        await _SP(db_session, seeded, b, "high", version_id=D)
        await _SP(db_session, seeded, c, "high", version_id=D)
        await _SR(db_session, seeded, c, 5, version_id=D)  # an override on the draft
        await _SM(db_session, seeded, b, 1, version_id=D)  # typed on the draft
        # Scanner moves after the draft was made: a drops to 3 (its board missing 3
        # now exceeds the live ceiling 3 - 1), and a new row d arrives.
        await _AD(db_session, workspace_id, [_entry(0, "a", 3), _entry(1, "d", 3)])
        d = (await _by_token(db_session, workspace_id))["d"]
        # §4.1's window, forced by hand: the draft lacks d's snapshot.
        await db_session.execute(
            text(
                "DELETE FROM stock_report_item_snapshots WHERE version_id = :v AND stock_report_item_id = :r"
            ),
            {"v": D, "r": d},
        )
        await db_session.commit()
        records_before = len(await _records(db_session, workspace_id))

        version, captured = await _activate(
            db_session,
            seeded,
            D,
            body={"keep_active_missing": True},
            monkeypatch=monkeypatch,
        )

        assert (version["state"], version["active_at"], version["snapshot_count"]) == (
            "active",
            LATER.isoformat(),
            4,
        )
        assert version["scheduled_activation_at"] is None
        assert [(e.event_name, e.client_id, e.extra) for e in captured] == [
            (
                "stock_report_snapshot_version:closed",
                v1["client_id"],
                {"snapshot_count": 3},
            ),
            (
                "stock_report_snapshot_version:activated",
                D,
                {
                    "snapshot_count": 4,
                    "title": "Monday",
                    "scheduled": False,
                    "keep_active_missing": True,
                },
            ),
        ]
        # The previous version closed with its counters frozen from the rows.
        previous = await _version_row(db_session, v1["client_id"])
        assert previous.closed_at == LATER
        closed_a = (await _snapshots_of(db_session, v1["client_id"]))[a]
        assert (closed_a.closed_at, closed_a.quantity_in_queue) == (LATER, 1)
        # The new board: one statement's worth of freeze, settle and stamp.
        snapshots = await _snapshots_of(db_session, D)
        assert {
            r: (
                s.quantity_requested_scanner,
                s.quantity_requested_manual,
                s.quantity_missing,
                s.active_at,
                s.priority.value if s.priority else None,
                s.priority_order,
            )
            for r, s in snapshots.items()
        } == {
            a: (3, None, 2, LATER, None, None),  # carried 3, clamped to 3 - 1
            b: (4, None, 1, LATER, "high", 1),  # typed 1 beats the board's 2
            c: (6, 5, 0, LATER, "high", 2),  # the board had 0 for c; override kept
            d: (3, None, 0, LATER, None, None),  # reconciled in; no board twin
        }
        board = await _items(db_session, seeded)
        assert set(board) == {a, b, c, d}
        assert (
            board[c]["snapshot"]["quantity_requested"],
            board[c]["snapshot"]["quantity_requested_scanner"],
            board[c]["snapshot"]["quantity_requested_source"],
        ) == (5, 6, "manual")
        assert board[a]["snapshot"]["quantity_missing"] == 2
        # History: b and c only, with the effective value and its source.
        records = (await _records(db_session, workspace_id))[records_before:]
        assert sorted(
            (
                r.stock_report_item_id,
                r.type,
                r.quantity_requested,
                r.quantity_requested_source,
                r.priority.value,
                r.priority_order,
            )
            for r in records
        ) == sorted(
            [
                (
                    b,
                    StockReportHistoryRecordTypeEnum.PRIORITY_CHANGE,
                    4,
                    StockReportQuantityRequestedSourceEnum.SCANNER,
                    "high",
                    1,
                ),
                (
                    c,
                    StockReportHistoryRecordTypeEnum.PRIORITY_CHANGE,
                    5,
                    StockReportQuantityRequestedSourceEnum.MANUAL,
                    "high",
                    2,
                ),
            ]
        )
        assert await _draft_count(db_session, seeded) == 0
        assert [
            (v["client_id"], v["state"]) for v in await _versions(db_session, seeded)
        ] == [
            (D, "active"),
            (v1["client_id"], "closed"),
        ]
        await assert_stock_report_clean(db_session, workspace_id)
        # Refusals change nothing: not a draft, absent, v7's body.
        with pytest.raises(ValidationError, match="STOCK_REPORT_VERSION_NOT_DRAFT"):
            await _activate(db_session, seeded, D)
        await db_session.rollback()
        with pytest.raises(NotFound):
            await _activate(db_session, seeded, "srv_absent")
        await db_session.rollback()
        with pytest.raises(ValidationError, match="refresh_quantity_requested"):
            await _activate(
                db_session, seeded, D, body={"refresh_quantity_requested": False}
            )
        await db_session.rollback()
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_activation_resets_untyped_missing_and_needs_no_previous_board(
    db_session, monkeypatch
):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    fresh = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id, fresh_id = seeded.workspace.client_id, fresh.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10), _entry(1, "b", 10)])
        ids = await _by_token(db_session, workspace_id)
        a, b = ids["a"], ids["b"]
        await _CV(db_session, seeded)
        await _assign_seeded_item(db_session, seeded, a)  # in_queue 1
        await _SM(db_session, seeded, a, 3)
        await _SM(db_session, seeded, b, 5)
        draft, _ = await _draft(db_session, seeded)
        D = draft["client_id"]
        await _SM(db_session, seeded, a, 9, version_id=D)  # typed, at the ceiling 10 - 1
        await _AD(db_session, workspace_id, [_entry(0, "a", 8)])  # ceiling now 8 - 1

        version, captured = await _activate(
            db_session,
            seeded,
            D,
            body={"keep_active_missing": False},
            monkeypatch=monkeypatch,
        )
        assert captured[-1].extra["keep_active_missing"] is False
        snapshots = await _snapshots_of(db_session, D)
        assert (snapshots[a].quantity_missing, snapshots[b].quantity_missing) == (7, 0)
        assert snapshots[a].quantity_requested_scanner == 8
        await assert_stock_report_clean(db_session, workspace_id)

        # No previous board, a schedule on the draft: activation by hand is a 200
        # that clears the schedule in the same statement (R-2), emits no `:closed`,
        # and starts every missing at 0 whatever the flag.
        await _AD(db_session, fresh_id, [_entry(0, "a", 10)])
        scheduled, _ = await _CV(
            db_session,
            fresh,
            body={
                "draft": True,
                "scheduled_activation_at": "2026-12-01T06:00:00+02:00",
            },
        )
        version, captured = await _activate(
            db_session,
            fresh,
            scheduled["client_id"],
            body={"keep_active_missing": True},
            monkeypatch=monkeypatch,
        )
        assert (version["state"], version["scheduled_activation_at"]) == (
            "active",
            None,
        )
        assert [e.event_name for e in captured] == [
            "stock_report_snapshot_version:activated"
        ]
        rows = await _items(db_session, fresh)
        assert [
            (r["snapshot"]["quantity_requested"], r["snapshot"]["quantity_missing"])
            for r in rows.values()
        ] == [(10, 0)]
        await assert_stock_report_clean(db_session, fresh_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await purge_stock_report_workspace(db_session, fresh_id)
        await db_session.commit()


async def test_refresh_refreezes_the_active_version(db_session, monkeypatch):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10), _entry(1, "b", 4)])
        ids = await _by_token(db_session, workspace_id)
        a, b = ids["a"], ids["b"]
        v1, _ = await _CV(db_session, seeded)
        V = v1["client_id"]
        await _SP(db_session, seeded, a, "high")
        await _SP(db_session, seeded, b, "high")
        await _assign_seeded_item(db_session, seeded, a)  # in_queue 1
        await _SM(db_session, seeded, a, 9)  # ceiling 10 - 1
        await _SM(db_session, seeded, b, 4)  # target 0: b is complete
        draft, _ = await _draft(db_session, seeded)
        assert (await _progress(db_session, seeded, V))["items_completed"] == 1
        # A manual raise on the active version moves the target: b is no longer
        # complete (the second exception to "never goes backwards", §4.11).
        await _SR(db_session, seeded, b, 9, version_id=V)
        assert (await _progress(db_session, seeded, V))["items_completed"] == 0
        await _SR(db_session, seeded, b, None, version_id=V)
        assert (await _progress(db_session, seeded, V))["items_completed"] == 1

        # Scanner moves a (down) and b (up), and c arrives.
        await _AD(
            db_session,
            workspace_id,
            [_entry(0, "a", 7), _entry(1, "b", 6), _entry(2, "c", 5)],
        )
        c = (await _by_token(db_session, workspace_id))["c"]
        result, captured = await _refresh(
            db_session, seeded, V, monkeypatch=monkeypatch
        )
        assert (result["changed"], result["added"]) == (2, 1)
        assert result["stock_report_snapshot_version"]["snapshot_count"] == 3
        snapshots = await _snapshots_of(db_session, V)
        # a re-frozen and its missing clamped to 7 - 1; b re-frozen, missing kept;
        # c joined with the version's own `active_at` (P-15), frozen now.
        assert (
            snapshots[a].quantity_requested_scanner,
            snapshots[a].quantity_missing,
        ) == (7, 6)
        assert (
            snapshots[b].quantity_requested_scanner,
            snapshots[b].quantity_missing,
        ) == (6, 4)
        assert (
            snapshots[c].quantity_requested_scanner,
            snapshots[c].quantity_missing,
            snapshots[c].active_at,
            snapshots[c].priority,
        ) == (5, 0, NOW, None)
        # One coalesced event per touched snapshot (a: scanner + clamp), none for
        # the new row, then `:refreshed`. The snapshot events come in the order the
        # re-freeze `UPDATE ... RETURNING` yields them, which no clause fixes, so
        # they are compared sorted.
        assert sorted((e.event_name, e.client_id) for e in captured[:-1]) == sorted(
            [
                ("stock_report_item_snapshot:updated", snapshots[a].client_id),
                ("stock_report_item_snapshot:updated", snapshots[b].client_id),
            ]
        )
        assert (captured[-1].event_name, captured[-1].client_id) == (
            "stock_report_snapshot_version:refreshed",
            V,
        )
        event_a = next(e for e in captured if e.client_id == snapshots[a].client_id)
        assert (
            event_a.extra["quantity_requested_scanner"],
            event_a.extra["quantity_missing"],
        ) == (7, 6)
        assert captured[-1].extra == {
            "snapshot_count": 3,
            "changed": 2,
            "added": 1,
            "keep_manual_requested": True,
        }
        # Progress went backwards (R-10): b's target rose from 0 to 2.
        assert (await _progress(db_session, seeded, V))["items_completed"] == 0
        # The draft is untouched by a refresh of the board.
        assert all(
            s.quantity_requested_scanner is None
            for s in (await _snapshots_of(db_session, draft["client_id"])).values()
        )

        # An override survives `keep_manual_requested: true`: the Scanner-only change
        # still emits, is not counted as changed, and a later revert lands on the
        # refreshed value.
        await _SR(db_session, seeded, b, 9, version_id=V)
        await _AD(db_session, workspace_id, [_entry(0, "b", 8)])
        result, captured = await _refresh(
            db_session, seeded, V, monkeypatch=monkeypatch
        )
        assert (result["changed"], result["added"]) == (0, 0)
        assert [
            (
                e.extra["quantity_requested_scanner"],
                e.extra["quantity_requested_manual"],
            )
            for e in captured
            if e.event_name == "stock_report_item_snapshot:updated"
        ] == [(8, 9)]
        reverted, _ = await _SR(db_session, seeded, b, None, version_id=V)
        assert reverted["snapshot"]["quantity_requested"] == 8
        # Nothing moved → no snapshot event, only `:refreshed` with zeros.
        _, captured = await _refresh(db_session, seeded, V, monkeypatch=monkeypatch)
        assert [e.event_name for e in captured] == [
            "stock_report_snapshot_version:refreshed"
        ]

        # `false` clears the overrides with one record each (source scanner).
        await _SR(db_session, seeded, b, 9, version_id=V)
        records_before = len(await _records(db_session, workspace_id))
        result, captured = await _refresh(
            db_session,
            seeded,
            V,
            body={"keep_manual_requested": False},
            monkeypatch=monkeypatch,
        )
        assert (result["changed"], result["added"]) == (1, 0)
        assert [
            e.extra["quantity_requested_manual"]
            for e in captured
            if e.event_name == "stock_report_item_snapshot:updated"
        ] == [None]
        assert captured[-1].extra["keep_manual_requested"] is False
        records = (await _records(db_session, workspace_id))[records_before:]
        assert [
            (
                r.stock_report_item_id,
                r.type,
                r.quantity_requested,
                r.quantity_requested_source,
            )
            for r in records
        ] == [
            (
                b,
                StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_OVERRIDE,
                8,
                StockReportQuantityRequestedSourceEnum.SCANNER,
            )
        ]
        assert (await _items(db_session, seeded))[b]["snapshot"][
            "quantity_requested_source"
        ] == "scanner"
        await assert_stock_report_clean(db_session, workspace_id)

        # Refusals: a draft, a closed version, an absent one.
        with pytest.raises(ValidationError, match="STOCK_REPORT_VERSION_NOT_ACTIVE"):
            await _refresh(db_session, seeded, draft["client_id"])
        await db_session.rollback()
        await _CV(db_session, seeded, now=LATER)  # closes v1
        with pytest.raises(ValidationError, match="STOCK_REPORT_VERSION_NOT_ACTIVE"):
            await _refresh(db_session, seeded, V)
        await db_session.rollback()
        with pytest.raises(NotFound):
            await _refresh(db_session, seeded, "srv_absent")
        await db_session.rollback()
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


@pytest.mark.parametrize("command", ["activate", "refresh"])
async def test_lock_order_is_rows_then_snapshots_then_versions(db_session, command):
    """MC-1: both commands lock the live rows first, then the snapshots, then the
    version row(s) — never a lower class after a higher one."""
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10)])
        active, _ = await _CV(db_session, seeded)
        draft, _ = await _draft(db_session, seeded)
        target = draft["client_id"] if command == "activate" else active["client_id"]
        run = _activate if command == "activate" else _refresh
        async with record_statements(db_session) as statements:
            await run(db_session, seeded, target)
        classes = [
            "stock_report_items",
            "stock_report_item_snapshots",
            "stock_report_snapshot_versions",
        ]
        locked = [
            table
            for statement in statements
            if "FOR UPDATE" in statement.upper()
            for table in classes
            if f"FROM {table}" in statement
        ]
        assert locked[:2] == classes[:2], statements
        assert [classes.index(t) for t in locked] == sorted(
            classes.index(t) for t in locked
        ), statements
        if command == "activate":
            assert "stock_report_snapshot_versions" in locked
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()
