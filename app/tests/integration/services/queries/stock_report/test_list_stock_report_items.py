"""Plan 12 — `GET /api/v1/stock-report/items` (master plan §6.5; intention §7A
"Read order", §9 response shape).

Rows are created through the demand service `AD`; `priority`/`priority_order` are
written by raw SQL afterwards, and the labels are bound by **sorting the real ids at
runtime** (`client_id` is a ULID with no monotonic counter, master plan §10).

This file exercises one representative case per code path; row-by-row transcription
and mutation arming belong to the tester (see the implementer handoff).
"""

import time
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from beyo_manager.config import Settings
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
    normalize_stock_criteria,
)
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.services.commands.stock_report.apply_stock_demand import (
    apply_stock_demand,
)
from beyo_manager.services.commands.stock_report.stock_demand_entries import DemandEntry
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.stock_report.list_stock_report_items import (
    list_stock_report_items,
)
from tests.helpers.stock_report import (
    ensure_active_snapshots,
    set_snapshot_position,
    make_ctx,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
_TIMEOUT_MS = Settings.model_fields["stock_demand_webhook_timeout_ms"].default

ROW_KEYS = {
    "client_id",
    "item_category",
    "properties",
    "properties_signature",
    "quantity_requested",
    "quantity_in_queue",
    "quantity_in_progress",
    "quantity_awaiting",
    "created_at",
    "updated_at",
    "created_by_id",
    "updated_by_id",
    "snapshot",
}
SNAPSHOT_KEYS = {
    "client_id",
    "version_id",
    "stock_report_item_id",
    "quantity_requested",
    "quantity_in_queue",
    "quantity_in_progress",
    "quantity_awaiting",
    "quantity_missing",
    "quantity_resolved",
    "priority",
    "priority_order",
    "active_at",
    "closed_at",
    "created_at",
    "updated_at",
    "updated_by_id",
}
CATEGORY_KEYS = {"client_id", "name", "major_category", "image_url"}


def _entry(index, category, token, quantity=10):
    raw = {"wood_group": [token]}
    return DemandEntry(
        index=index,
        item_category_raw=category,
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


async def _set_order(session, client_id, priority, order):
    await set_snapshot_position(session, client_id, priority, order)


async def _version(session, workspace_id):
    """Every live row gets an active snapshot (the board is a snapshot read)."""
    await ensure_active_snapshots(session, workspace_id, now=NOW)
    await session.commit()


async def _ids(session, workspace_id):
    """Every row id of the workspace, sorted **descending** by `client_id`, so the
    labels below disagree with `client_id` ascending."""
    return sorted(
        (
            await session.execute(
                select(StockReportItem.client_id).where(
                    StockReportItem.workspace_id == workspace_id
                )
            )
        )
        .scalars()
        .all(),
        reverse=True,
    )


async def _list(
    session,
    identity,
    priority=None,
    include_zero_requested=False,
    item_major_categories=None,
    item_category_ids=None,
    live_stock=False,
    missing_only=False,
):
    ctx = ServiceContext(
        identity=identity,
        incoming_data={},
        query_params={
            "priority": priority,
            "include_zero_requested": include_zero_requested,
            "item_major_categories": item_major_categories,
            "item_category_ids": item_category_ids,
            "live_stock": live_stock,
            "missing_only": missing_only,
        },
        session=session,
    )
    return await list_stock_report_items(ctx)


async def test_read_order_is_high_medium_low_then_priority_order(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    identity = make_ctx(db_session, seeded).identity
    try:
        await _AD(
            db_session,
            workspace_id,
            [
                _entry(index, "Dining Chairs", f"teak{index}")
                for index in range(7)
            ],
        )
        await _version(db_session, workspace_id)
        A, B, C, D, M, X, Y = await _ids(db_session, workspace_id)
        for client_id, priority, order in (
            (A, "high", 1),
            (B, "high", 2),
            (C, "high", 3),
            (D, "high", 4),
            (M, "medium", 1),
            (X, "low", 1),
            (Y, "low", 2),
        ):
            await _set_order(db_session, client_id, priority, order)
        await db_session.commit()

        result = await _list(db_session, identity, "high,medium,low")

        assert [row["client_id"] for row in result["stock_report_items"]] == [
            A,
            B,
            C,
            D,
            M,
            X,
            Y,
        ]
        # §5 / 07_queries_local override: this endpoint emits no pagination key.
        assert set(result) == {"stock_report_items"}
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_no_filter_lists_only_null_priority_rows_by_created_at(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    identity = make_ctx(db_session, seeded).identity
    try:
        # Two separate `AD` calls, so the two null rows carry different
        # `created_at`, plus a third row that is given a priority.
        await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", "teak0")])
        await db_session.commit()
        await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", "teak1")])
        await db_session.commit()
        await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", "teak2")])
        await db_session.commit()
        await _version(db_session, workspace_id)

        # A ULID carries no monotonic counter (master plan §10), so *which* row is
        # back-dated is chosen from the **sorted real ids**: N1 is the null row with
        # the LARGER `client_id`, so `created_at` ascending is guaranteed to
        # disagree with `client_id` ascending. Leaving it to creation order makes the
        # cell's second mutant inert on roughly a third of runs.
        ids = await _ids(db_session, workspace_id)  # descending `client_id`
        priced = ids[1]
        N1, N2 = ids[0], ids[2]  # N1 > N2 by `client_id`
        await db_session.execute(
            text(
                "UPDATE stock_report_items SET created_at = :created_at "
                "WHERE client_id = :client_id"
            ),
            {"created_at": NOW.replace(hour=9), "client_id": N1},
        )
        await _set_order(db_session, priced, "high", 1)
        await db_session.commit()
        assert N1 > N2

        listed = [
            row["client_id"]
            for row in (await _list(db_session, identity))["stock_report_items"]
        ]

        assert priced not in listed
        # `created_at` ascending puts N1 first; `client_id` ascending would put N2
        # first, which is what makes the ordering half of this row discriminating.
        assert listed == [N1, N2]

        # An empty parameter means the same null listing, not the unknown-token case.
        assert [
            row["client_id"]
            for row in (await _list(db_session, identity, ""))["stock_report_items"]
        ] == listed
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_zero_requested_rows_are_hidden_unless_explicitly_included(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    identity = make_ctx(db_session, seeded).identity
    try:
        await _AD(
            db_session,
            workspace_id,
            [
                _entry(0, "Dining Chairs", "requested", quantity=3),
                _entry(1, "Dining Chairs", "zero", quantity=0),
            ],
        )
        await db_session.commit()
        await _version(db_session, workspace_id)

        rows_by_quantity = {
            row["quantity_requested"]: row["client_id"]
            for row in (
                await _list(db_session, identity, include_zero_requested=True)
            )["stock_report_items"]
        }

        assert [
            row["client_id"]
            for row in (await _list(db_session, identity))["stock_report_items"]
        ] == [rows_by_quantity[3]]
        assert {
            row["client_id"]
            for row in (
                await _list(db_session, identity, include_zero_requested=True)
            )["stock_report_items"]
        } == {rows_by_quantity[3], rows_by_quantity[0]}
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_category_filters_narrow_rows_and_combine_with_each_other(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    identity = make_ctx(db_session, seeded).identity
    seat, wood = seeded.categories
    try:
        await _AD(
            db_session,
            workspace_id,
            [
                _entry(0, seat.name, "seat", quantity=3),
                _entry(1, wood.name, "wood", quantity=4),
            ],
        )
        await db_session.commit()
        await _version(db_session, workspace_id)

        all_rows = (await _list(db_session, identity))["stock_report_items"]
        ids_by_category = {
            row["item_category"]["client_id"]: row["client_id"] for row in all_rows
        }

        assert {
            row["client_id"]
            for row in (
                await _list(
                    db_session, identity, item_major_categories=[seat.major_category]
                )
            )["stock_report_items"]
        } == {ids_by_category[seat.client_id]}
        assert {
            row["client_id"]
            for row in (
                await _list(db_session, identity, item_category_ids=[wood.client_id])
            )["stock_report_items"]
        } == {ids_by_category[wood.client_id]}
        assert (
            await _list(
                db_session,
                identity,
                item_major_categories=[seat.major_category],
                item_category_ids=[wood.client_id],
            )
        )["stock_report_items"] == []
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_unknown_priority_token_is_refused(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    identity = make_ctx(db_session, seeded).identity
    try:
        with pytest.raises(ValidationError) as excinfo:
            await _list(db_session, identity, "urgent")
        assert str(excinfo.value).startswith("STOCK_REPORT_UNKNOWN_PRIORITY_FILTER:")
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_priority_all_lists_prioritised_then_unprioritised_in_board_order(
    db_session,
):
    """`priority=all` (2026-09-26): every active snapshot. Prioritised rows first in
    the board order (high, medium, low, then `priority_order`), then the
    unprioritised by `(created_at, client_id)` — the two filtered reads concatenated.
    The labels deliberately disagree with `client_id` order (`_ids` sorts
    descending), so an order falling back to `client_id` would fail."""
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    identity = make_ctx(db_session, seeded).identity
    try:
        await _AD(
            db_session,
            workspace_id,
            [_entry(index, "Dining Chairs", f"teak{index}") for index in range(6)],
        )
        await _version(db_session, workspace_id)
        H2, L1, H1, N_a, M1, N_b = await _ids(db_session, workspace_id)
        for client_id, priority, order in (
            (H1, "high", 1),
            (H2, "high", 2),
            (M1, "medium", 1),
            (L1, "low", 1),
        ):
            await _set_order(db_session, client_id, priority, order)
        await db_session.commit()
        unprioritised = [
            client_id
            for (client_id,) in (
                await db_session.execute(
                    select(StockReportItem.client_id)
                    .where(StockReportItem.client_id.in_([N_a, N_b]))
                    .order_by(StockReportItem.created_at, StockReportItem.client_id)
                )
            ).all()
        ]

        result = await _list(db_session, identity, "all")

        listed = [row["client_id"] for row in result["stock_report_items"]]
        assert listed == [H1, H2, M1, L1, *unprioritised]
        # It is the union of the two filtered reads, nothing more and nothing less.
        prioritised = await _list(db_session, identity, "high,medium,low")
        nulls = await _list(db_session, identity, None)
        assert listed == [
            row["client_id"]
            for row in prioritised["stock_report_items"] + nulls["stock_report_items"]
        ]
        assert [row["snapshot"]["priority"] for row in result["stock_report_items"]] == [
            "high",
            "high",
            "medium",
            "low",
            None,
            None,
        ]
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"priority": "all,high"}, id="all-combined"),
        pytest.param({"priority": "high, all"}, id="all-combined-spaced"),
        pytest.param({"priority": "all", "live_stock": True}, id="all-on-live-read"),
    ],
)
async def test_priority_all_is_refused_when_combined(db_session, params):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    identity = make_ctx(db_session, seeded).identity
    try:
        with pytest.raises(ValidationError) as excinfo:
            await _list(db_session, identity, **params)
        expected = (
            "STOCK_REPORT_LIVE_STOCK_FILTER_CONFLICT:"
            if params.get("live_stock")
            else "STOCK_REPORT_UNKNOWN_PRIORITY_FILTER:"
        )
        assert str(excinfo.value).startswith(expected)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_row_shape_carries_the_four_key_category_including_a_null_image(
    db_session,
):
    """Plan 12 C4(e): `item_category` is four keys, and on a category with no image
    `image_url` is **present and `None`** — an omitted key and a null key are
    different things to a renderer."""
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    identity = make_ctx(db_session, seeded).identity
    try:
        await _AD(
            db_session,
            workspace_id,
            [
                _entry(0, "Dining Chairs", "teak0"),
                _entry(1, "Coffee Tables", "teak1"),
            ],
        )
        await db_session.commit()
        await _version(db_session, workspace_id)
        await db_session.execute(
            text(
                "UPDATE item_categories SET image_url = :url WHERE name = "
                "'Dining Chairs' AND workspace_id = :workspace_id"
            ),
            {"url": "https://example.test/chairs.png", "workspace_id": workspace_id},
        )
        await db_session.commit()

        rows = (await _list(db_session, identity))["stock_report_items"]

        assert len(rows) == 2
        by_name = {row["item_category"]["name"]: row for row in rows}
        # Both rows in ONE assertion, keyed by category, so a mutant that drops
        # `image_url` shows **both** reddenings at once instead of aborting the
        # loop on whichever row the read order happens to return first.
        assert {name: set(row) for name, row in by_name.items()} == {
            "Dining Chairs": ROW_KEYS,
            "Coffee Tables": ROW_KEYS,
        }
        assert {
            name: set(row["item_category"]) for name, row in by_name.items()
        } == {
            "Dining Chairs": CATEGORY_KEYS,
            "Coffee Tables": CATEGORY_KEYS,
        }
        assert (
            by_name["Dining Chairs"]["item_category"]["image_url"]
            == "https://example.test/chairs.png"
        )
        # Present and None, never absent.
        assert "image_url" in by_name["Coffee Tables"]["item_category"]
        assert by_name["Coffee Tables"]["item_category"]["image_url"] is None
        assert by_name["Dining Chairs"]["item_category"]["major_category"] == "seat"
        assert by_name["Dining Chairs"]["properties"] == {"wood_group": ["teak0"]}
        snapshot = by_name["Dining Chairs"]["snapshot"]
        assert set(snapshot) == SNAPSHOT_KEYS
        assert snapshot["priority"] is None
        assert snapshot["priority_order"] is None
        assert snapshot["quantity_missing"] == 0
        assert snapshot["closed_at"] is None
        assert snapshot["stock_report_item_id"] == by_name["Dining Chairs"]["client_id"]
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_soft_deleted_and_foreign_rows_are_not_listed(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    foreign = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    foreign_id = foreign.workspace.client_id
    identity = make_ctx(db_session, seeded).identity
    try:
        await _AD(
            db_session,
            workspace_id,
            [_entry(0, "Dining Chairs", "teak0"), _entry(1, "Dining Chairs", "teak1")],
        )
        live, deleted = sorted(await _ids(db_session, workspace_id))
        await db_session.commit()
        await _version(db_session, workspace_id)
        # The foreign row is a cross-workspace reference: same category name, same
        # properties, same `high` group with the same order.
        await _AD(db_session, foreign_id, [_entry(0, "Dining Chairs", "teak0")])
        await db_session.commit()
        await _version(db_session, foreign_id)
        foreign_row = (await _ids(db_session, foreign_id))[0]
        await _set_order(db_session, foreign_row, "high", 1)
        await db_session.execute(
            text(
                "UPDATE stock_report_items SET is_deleted = true "
                "WHERE client_id = :client_id"
            ),
            {"client_id": deleted},
        )
        await db_session.commit()

        listed = [
            row["client_id"]
            for row in (await _list(db_session, identity))["stock_report_items"]
        ]

        assert listed == [live]
        assert (
            await _list(db_session, identity, "high")
        )["stock_report_items"] == []
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await purge_stock_report_workspace(db_session, foreign_id)
        await db_session.commit()


async def test_a_row_whose_category_was_soft_deleted_still_serializes_its_name(
    db_session,
):
    """MC-16: categories are batch-loaded **by id**, so a soft-deleted category does
    not make its rows vanish from the board."""
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    identity = make_ctx(db_session, seeded).identity
    try:
        await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", "teak0")])
        await db_session.commit()
        await _version(db_session, workspace_id)
        await db_session.execute(
            text(
                "UPDATE item_categories SET is_deleted = true WHERE name = "
                "'Dining Chairs' AND workspace_id = :workspace_id"
            ),
            {"workspace_id": workspace_id},
        )
        await db_session.commit()

        rows = (await _list(db_session, identity))["stock_report_items"]

        assert len(rows) == 1
        assert rows[0]["item_category"]["name"] == "Dining Chairs"
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# The snapshot read (2026-09-26): default vs `live_stock`, `missing_only`
# ---------------------------------------------------------------------------


async def _set_missing(session, client_id, missing):
    await session.execute(
        text(
            "UPDATE stock_report_item_snapshots SET quantity_missing = :missing "
            "WHERE stock_report_item_id = :client_id AND closed_at IS NULL"
        ),
        {"missing": missing, "client_id": client_id},
    )


async def test_default_read_hides_rows_without_an_active_snapshot_and_live_shows_them(
    db_session,
):
    """A row Scanner created since the last version is invisible on the board until
    the next version — and visible on `live_stock=true` with `snapshot: null`."""
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    identity = make_ctx(db_session, seeded).identity
    try:
        await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", "teak0")])
        await db_session.commit()
        await _version(db_session, workspace_id)
        await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", "late")])
        await db_session.commit()
        snapshotted, late = (
            row["client_id"]
            for row in sorted(
                (await _list(db_session, identity, live_stock=True))[
                    "stock_report_items"
                ],
                key=lambda row: row["snapshot"] is None,
            )
        )

        listed = (await _list(db_session, identity))["stock_report_items"]
        assert [row["client_id"] for row in listed] == [snapshotted]
        assert listed[0]["snapshot"] is not None

        live = (await _list(db_session, identity, live_stock=True))["stock_report_items"]
        by_id = {row["client_id"]: row for row in live}
        assert set(by_id) == {snapshotted, late}
        assert by_id[late]["snapshot"] is None
        assert by_id[snapshotted]["snapshot"]["quantity_requested"] == 10
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_outstanding_is_requested_minus_missing_and_missing_only_filters(
    db_session,
):
    """Default hides a snapshot whose `requested - missing <= 0`;
    `include_zero_requested` shows it; `missing_only` keeps only `missing > 0`."""
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    identity = make_ctx(db_session, seeded).identity
    try:
        await _AD(
            db_session,
            workspace_id,
            [
                _entry(0, "Dining Chairs", "all-missing", quantity=3),
                _entry(1, "Dining Chairs", "some-missing", quantity=5),
                _entry(2, "Dining Chairs", "none-missing", quantity=4),
            ],
        )
        await db_session.commit()
        await _version(db_session, workspace_id)
        by_quantity = {
            row["quantity_requested"]: row["client_id"]
            for row in (await _list(db_session, identity))["stock_report_items"]
        }
        all_missing, some_missing, none_missing = (
            by_quantity[3], by_quantity[5], by_quantity[4]
        )
        await _set_missing(db_session, all_missing, 3)
        await _set_missing(db_session, some_missing, 2)
        await db_session.commit()

        default = {
            row["client_id"]
            for row in (await _list(db_session, identity))["stock_report_items"]
        }
        assert default == {some_missing, none_missing}
        included = {
            row["client_id"]
            for row in (
                await _list(db_session, identity, include_zero_requested=True)
            )["stock_report_items"]
        }
        assert included == {all_missing, some_missing, none_missing}
        missing = {
            row["client_id"]: row["snapshot"]["quantity_missing"]
            for row in (
                await _list(
                    db_session, identity, missing_only=True, include_zero_requested=True
                )
            )["stock_report_items"]
        }
        assert missing == {all_missing: 3, some_missing: 2}
        # `missing_only` alone (2026-09-26 fix): the outstanding rule is the
        # worker's view and does not apply to the buyer's list. A fully missing
        # snapshot (outstanding 0) is exactly what the buyer needs to see — before
        # the fix it was hidden, while the missing-summary counter still counted it.
        # With and without `priority=all`: `all_missing` has no priority.
        for priority in (None, "all"):
            missing_alone = {
                row["client_id"]: row["snapshot"]["quantity_missing"]
                for row in (
                    await _list(db_session, identity, priority, missing_only=True)
                )["stock_report_items"]
            }
            assert missing_alone == {all_missing: 3, some_missing: 2}, priority
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


@pytest.mark.parametrize(
    "params", [{"priority": "high"}, {"missing_only": True}, {"priority": ""}]
)
async def test_snapshot_filters_are_refused_on_a_live_read(db_session, params):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    identity = make_ctx(db_session, seeded).identity
    try:
        with pytest.raises(ValidationError) as excinfo:
            await _list(db_session, identity, live_stock=True, **params)
        assert str(excinfo.value).startswith(
            "STOCK_REPORT_LIVE_STOCK_FILTER_CONFLICT:"
        )
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()
