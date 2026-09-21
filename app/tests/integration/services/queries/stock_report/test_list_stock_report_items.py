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
    "priority",
    "priority_order",
    "created_at",
    "updated_at",
    "created_by_id",
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
    await session.execute(
        text(
            "UPDATE stock_report_items SET priority = :priority, "
            "priority_order = :order WHERE client_id = :client_id"
        ),
        {"priority": priority, "order": order, "client_id": client_id},
    )


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


async def _list(session, identity, priority=None):
    ctx = ServiceContext(
        identity=identity,
        incoming_data={},
        query_params={"priority": priority},
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
        # Two separate `AD` calls, so the two null rows carry different `created_at`.
        await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", "teak0")])
        first = (await _ids(db_session, workspace_id))[0]
        await db_session.commit()
        await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", "teak1")])
        await db_session.execute(
            text(
                "UPDATE stock_report_items SET created_at = :created_at "
                "WHERE client_id = :client_id"
            ),
            {"created_at": NOW.replace(hour=9), "client_id": first},
        )
        await db_session.commit()
        await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", "teak2")])
        ids = await _ids(db_session, workspace_id)
        priced = [client_id for client_id in ids if client_id != first][0]
        await _set_order(db_session, priced, "high", 1)
        await db_session.commit()

        listed = [
            row["client_id"]
            for row in (await _list(db_session, identity))["stock_report_items"]
        ]

        assert priced not in listed
        # `first` was back-dated, so `created_at` ascending puts it first even
        # though it does not sort first by `client_id`.
        assert listed[0] == first
        assert len(listed) == 2

        # An empty parameter means the same null listing, not the unknown-token case.
        assert [
            row["client_id"]
            for row in (await _list(db_session, identity, ""))["stock_report_items"]
        ] == listed
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
        for row in rows:
            assert set(row) == ROW_KEYS
            assert set(row["item_category"]) == CATEGORY_KEYS
        assert (
            by_name["Dining Chairs"]["item_category"]["image_url"]
            == "https://example.test/chairs.png"
        )
        # Present and None, never absent.
        assert "image_url" in by_name["Coffee Tables"]["item_category"]
        assert by_name["Coffee Tables"]["item_category"]["image_url"] is None
        assert by_name["Dining Chairs"]["item_category"]["major_category"] == "seat"
        assert by_name["Dining Chairs"]["properties"] == {"wood_group": ["teak0"]}
        assert by_name["Dining Chairs"]["priority"] is None
        assert by_name["Dining Chairs"]["priority_order"] is None
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
        # The foreign row is a cross-workspace reference: same category name, same
        # properties, same `high` group with the same order.
        await _AD(db_session, foreign_id, [_entry(0, "Dining Chairs", "teak0")])
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
