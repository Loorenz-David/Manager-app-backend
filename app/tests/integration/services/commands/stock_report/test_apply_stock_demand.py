"""Plan 6 — `apply_stock_demand` (master plan §6.5; intention §8B D6).

Every row here is a committing test (§9 rule 1; plan 6's fold note): `apply_stock_demand`
refuses a session already in a transaction, and the phase-1 kit's first `flush()`
autobegins one. So each test's shape is `seed -> commit -> AD(...) -> assertions ->
finally: purge + commit`.

C7 (the timing/deadline criterion, including the one sleeping test) lives in its own
file, `test_apply_stock_demand_timing.py`, excluded from L1 loops by file (H25).
"""

import asyncio
import time
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from beyo_manager.config import Settings
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
    normalize_stock_criteria,
)
from beyo_manager.domain.stock_report.enums import (
    StockDemandOutcomeEnum,
    StockReportPriorityEnum,
    StockTaskAssignmentStateEnum,
)
from beyo_manager.errors.stock_report import LocationTrackerWebhookAuthError
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.stock_report.apply_stock_demand import (
    apply_stock_demand,
)
from beyo_manager.services.commands.stock_report.stock_demand_entries import DemandEntry
from tests.helpers.statement_listener import count_writes, record_statements
from tests.helpers.stock_report import (
    active_snapshot,
    ensure_active_snapshots,
    set_snapshot_position,
    assert_stock_report_clean,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
WRITE_TABLES = {
    "stock_report_items",
    "stock_task_assignments",
    "stock_report_history_records",
    "tasks",
}
_DEFAULT_TIMEOUT_MS = Settings.model_fields["stock_demand_webhook_timeout_ms"].default


def _entry(index, category_raw, properties_raw, quantity):
    return DemandEntry(
        index=index,
        item_category_raw=category_raw,
        properties_raw=properties_raw,
        properties_normalized=normalize_stock_criteria(properties_raw),
        properties_signature=compute_stock_criteria_signature(properties_raw),
        quantity_requested=quantity,
    )


async def _AD(session, workspace_id, entries, *, deadline=None, now=None, timeout_ms=None):
    return await apply_stock_demand(
        session,
        workspace_id=workspace_id,
        entries=entries,
        now=now if now is not None else NOW,
        deadline=deadline if deadline is not None else time.monotonic() + 60,
        timeout_ms=timeout_ms if timeout_ms is not None else _DEFAULT_TIMEOUT_MS,
    )


async def _quantity_requested(session, row_id):
    # `apply_stock_demand` refuses a session already in a transaction (B5), and any
    # read on this session autobegins one — so every helper that reads between two
    # `_AD` calls must close it out again before returning.
    value = await session.scalar(
        select(StockReportItem.quantity_requested).where(StockReportItem.client_id == row_id)
    )
    await session.commit()
    return value


# ---------------------------------------------------------------------------
# C1 — find-or-create
# ---------------------------------------------------------------------------


async def test_c1a_new_entry_creates_row_and_emits_created_only(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        properties_raw = {"wood_group": ["teak"]}
        result = await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 5)])

        row = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.workspace_id == workspace_id)
            )
        ).scalar_one()
        assert row.quantity_requested == 5
        assert row.properties == {"wood_group": ["teak"]}
        assert row.properties_signature == compute_stock_criteria_signature(properties_raw)
        assert row.created_by_id is None
        assert row.quantity_in_queue == 0
        assert row.quantity_in_progress == 0
        assert row.quantity_awaiting == 0
        # A row created by demand has no snapshot until the next version is opened.
        assert await active_snapshot(db_session, row.client_id) is None

        assert len(result.outcomes) == 1
        assert result.outcomes[0].outcome == StockDemandOutcomeEnum.APPLIED

        assert len(result.events) == 1
        assert result.events[0].event_name == "stock_report_item:created"
        assert result.events[0].client_id == row.client_id
        assert result.events[0].workspace_id == workspace_id
        assert result.events[0].extra == {}

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c1b_existing_row_quantity_changes_emits_updated_only(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        properties_raw = {"wood_group": ["teak"]}
        first = await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 5)])
        created_id = first.events[0].client_id

        result = await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 7)])

        rows = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.workspace_id == workspace_id)
            )
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].client_id == created_id
        assert rows[0].quantity_requested == 7

        assert len(result.events) == 1
        assert result.events[0].event_name == "stock_report_item:updated"
        assert result.events[0].client_id == created_id
        assert result.events[0].extra["quantity_requested"] == 7

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c4m_demand_never_stamps_authorship_columns(db_session):
    """Plan 8 C4(m) (batch B2 review 1 N4/CF-1; owner card 1, 2026-09-21): the demand
    path is a system actor. A created row's `created_by_id`/`updated_by_id`/
    `updated_at` are all NULL, and a later quantity change leaves `updated_by_id`/
    `updated_at` NULL too — this project stamps authorship on user-facing writers
    only (MC-17), never on Scanner's webhook. The fixture and both named mutations
    live in `apply_stock_demand.py` (phase 7's approved perimeter, not phase 8's own
    surface) per plan 8 §7's one-file perimeter extension."""
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        properties_raw = {"wood_group": ["teak"]}
        first = await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 5)])
        created_id = first.events[0].client_id

        await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 9)])

        row = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.client_id == created_id)
            )
        ).scalar_one()
        assert row.quantity_requested == 9
        assert row.created_by_id is None
        assert row.updated_by_id is None
        assert row.updated_at is None

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c1c_replay_same_quantity_writes_nothing(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        properties_raw = {"wood_group": ["teak"]}
        await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 5)])

        async with record_statements(db_session) as statements:
            result = await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 5)])

        assert count_writes(statements, WRITE_TABLES) == 0
        assert result.events == []
        assert result.outcomes[0].outcome == StockDemandOutcomeEnum.APPLIED

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c1d_soft_deleted_row_is_not_matched_new_row_created(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        properties_raw = {"wood_group": ["teak"]}
        first = await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 5)])
        old_id = first.events[0].client_id
        await db_session.execute(
            text(
                "UPDATE stock_report_items SET is_deleted = true, deleted_at = :now "
                "WHERE client_id = :id"
            ),
            {"now": NOW, "id": old_id},
        )
        await db_session.commit()

        result = await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 3)])

        rows = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.workspace_id == workspace_id)
            )
        ).scalars().all()
        assert len(rows) == 2
        old_row = next(r for r in rows if r.client_id == old_id)
        new_row = next(r for r in rows if r.client_id != old_id)
        assert old_row.is_deleted is True
        assert old_row.quantity_requested == 5
        assert new_row.is_deleted is False
        assert new_row.quantity_requested == 3
        assert result.events[0].event_name == "stock_report_item:created"
        assert result.events[0].client_id == new_row.client_id

        old_history = (
            await db_session.execute(
                select(StockReportHistoryRecord).where(
                    StockReportHistoryRecord.stock_report_item_id == old_id
                )
            )
        ).scalars().all()
        assert len(old_history) == 1

        new_history = (
            await db_session.execute(
                select(StockReportHistoryRecord).where(
                    StockReportHistoryRecord.stock_report_item_id == new_row.client_id
                )
            )
        ).scalars().all()
        assert len(new_history) == 1

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c1e_mixed_batch_one_new_one_changed(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        existing_props = {"wood_group": ["teak"]}
        new_props = {"wood_group": ["oak"]}
        await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", existing_props, 5)])

        result = await _AD(
            db_session,
            workspace_id,
            [
                _entry(0, "Dining Chairs", new_props, 2),
                _entry(1, "Dining Chairs", existing_props, 8),
            ],
        )

        assert [o.outcome for o in result.outcomes] == [
            StockDemandOutcomeEnum.APPLIED,
            StockDemandOutcomeEnum.APPLIED,
        ]
        event_names = sorted(e.event_name for e in result.events)
        assert event_names == ["stock_report_item:created", "stock_report_item:updated"]

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c1f_unknown_workspace_raises_auth_error(db_session):
    with pytest.raises(LocationTrackerWebhookAuthError) as excinfo:
        await _AD(
            db_session,
            "ws_stock_demand_does_not_exist",
            [_entry(0, "Dining Chairs", {"wood_group": ["teak"]}, 5)],
        )
    assert excinfo.value.http_status == 401
    assert excinfo.value.message == "Unauthorized."


# ---------------------------------------------------------------------------
# C2 — category resolution
# ---------------------------------------------------------------------------


async def test_c2a_exact_category_name_match(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        result = await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", {"wood_group": ["teak"]}, 5)])
        row = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.workspace_id == workspace_id)
            )
        ).scalar_one()
        assert row.item_category_id == seeded.categories[0].client_id
        assert result.outcomes[0].outcome == StockDemandOutcomeEnum.APPLIED

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c2b_case_insensitive_fallback_when_unique(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        result = await _AD(db_session, workspace_id, [_entry(0, "dining chairs", {"wood_group": ["teak"]}, 5)])
        row = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.workspace_id == workspace_id)
            )
        ).scalar_one()
        assert row.item_category_id == seeded.categories[0].client_id
        assert result.outcomes[0].outcome == StockDemandOutcomeEnum.APPLIED

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c2c_ambiguous_case_insensitive_match_is_not_resolved(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    variant = ItemCategory(
        workspace_id=seeded.workspace.client_id,
        name="dining chairs",
        major_category=seeded.categories[0].major_category,
    )
    db_session.add(variant)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        result = await _AD(db_session, workspace_id, [_entry(0, "DINING CHAIRS", {"wood_group": ["teak"]}, 5)])
        assert result.outcomes[0].outcome == StockDemandOutcomeEnum.CATEGORY_NOT_FOUND
        rows = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.workspace_id == workspace_id)
            )
        ).scalars().all()
        assert rows == []

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c2d_exact_match_wins_over_ambiguous_case_insensitive(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    variant = ItemCategory(
        workspace_id=seeded.workspace.client_id,
        name="dining chairs",
        major_category=seeded.categories[0].major_category,
    )
    db_session.add(variant)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        result = await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", {"wood_group": ["teak"]}, 5)])
        row = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.workspace_id == workspace_id)
            )
        ).scalar_one()
        assert row.item_category_id == seeded.categories[0].client_id
        assert result.outcomes[0].outcome == StockDemandOutcomeEnum.APPLIED

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c2e_unknown_category_entry_is_skipped_others_applied(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        result = await _AD(
            db_session,
            workspace_id,
            [
                _entry(0, "Serving Trolleys", {}, 1),
                _entry(1, "Dining Chairs", {"wood_group": ["teak"]}, 5),
            ],
        )
        assert [o.outcome for o in result.outcomes] == [
            StockDemandOutcomeEnum.CATEGORY_NOT_FOUND,
            StockDemandOutcomeEnum.APPLIED,
        ]
        rows = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.workspace_id == workspace_id)
            )
        ).scalars().all()
        assert len(rows) == 1

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c2f_category_name_with_surrounding_whitespace_resolves(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    sofas = ItemCategory(
        workspace_id=seeded.workspace.client_id,
        name="Sofas",
        major_category=seeded.categories[0].major_category,
    )
    db_session.add(sofas)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        result = await _AD(db_session, workspace_id, [_entry(0, "  Sofas ", {"wood_group": ["teak"]}, 5)])
        assert result.outcomes[0].outcome == StockDemandOutcomeEnum.APPLIED
        row = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.workspace_id == workspace_id)
            )
        ).scalar_one()
        assert row.item_category_id == sofas.client_id

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c2g_soft_deleted_category_is_not_matched(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.execute(
        text("UPDATE item_categories SET is_deleted = true WHERE client_id = :id"),
        {"id": seeded.categories[0].client_id},
    )
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        result = await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", {"wood_group": ["teak"]}, 5)])
        assert result.outcomes[0].outcome == StockDemandOutcomeEnum.CATEGORY_NOT_FOUND

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C3 — goal records (MC-6)
# ---------------------------------------------------------------------------


async def test_c3_sequence_goal_records_only_on_increase(db_session):
    """C3(a)->(e): one row through 5 -> 5 -> 3 -> 4 -> 0."""
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        properties_raw = {"wood_group": ["teak"]}

        # (a) new entry with 5 -> one goal record.
        result = await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 5)])
        row_id = result.events[0].client_id

        async def _history():
            # See `_quantity_requested`'s note: this read autobegins a transaction
            # that must be closed before the next `_AD` call.
            rows = (
                (
                    await db_session.execute(
                        select(StockReportHistoryRecord)
                        .where(StockReportHistoryRecord.stock_report_item_id == row_id)
                        .order_by(
                            StockReportHistoryRecord.created_at,
                            StockReportHistoryRecord.client_id,
                        )
                    )
                )
                .scalars()
                .all()
            )
            await db_session.commit()
            return rows

        history = await _history()
        assert len(history) == 1
        record = history[0]
        assert record.quantity_requested == 5
        assert record.quantity_awaiting == 0
        assert record.priority is None
        assert record.priority_order is None
        assert record.created_by_id is None
        assert record.created_at == NOW

        # (b) then 5 again -> no record, no write.
        async with record_statements(db_session) as statements:
            await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 5)])
        assert count_writes(statements, WRITE_TABLES) == 0
        assert len(await _history()) == 1

        # (c) then 3 -> no record; row at 3.
        await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 3)])
        assert len(await _history()) == 1
        assert await _quantity_requested(db_session, row_id) == 3

        # (d) then 4 -> a record (4 > stored 3, not compared to the historical max 5).
        await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 4)])
        history = await _history()
        assert len(history) == 2
        assert history[-1].quantity_requested == 4

        # (e) then 0 -> no record; row at 0.
        await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 0)])
        assert len(await _history()) == 2
        assert await _quantity_requested(db_session, row_id) == 0

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c3f_new_row_at_zero_has_no_goal_record(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        result = await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", {"wood_group": ["teak"]}, 0)])
        row_id = result.events[0].client_id
        history = (
            await db_session.execute(
                select(StockReportHistoryRecord).where(
                    StockReportHistoryRecord.stock_report_item_id == row_id
                )
            )
        ).scalars().all()
        assert history == []
        assert await _quantity_requested(db_session, row_id) == 0

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c3g_goal_record_snapshots_priority_not_live_counter(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        properties_raw = {"wood_group": ["teak"]}
        first = await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 5)])
        row_id = first.events[0].client_id
        # A companion row at priority_order 1 so the target row's order 2 is a dense
        # two-member "high" group (order_density, MC-20) rather than a manufactured
        # divergence — the plan's fixture names the row's own priority/order, not the
        # rest of the group needed to make that order legitimate.
        companion = await _AD(
            db_session, workspace_id, [_entry(0, "Dining Chairs", {"wood_group": ["oak"]}, 1)]
        )
        companion_id = companion.events[0].client_id
        await db_session.commit()
        # The position lives on the active item snapshot (2026-09-26): the goal
        # record must read it from there, and null when the row has none.
        await ensure_active_snapshots(db_session, workspace_id, now=NOW)
        await set_snapshot_position(db_session, companion_id, "high", 1)
        await set_snapshot_position(db_session, row_id, "high", 2)
        await db_session.execute(
            text(
                "UPDATE stock_report_items SET quantity_awaiting = 3 "
                "WHERE client_id = :id"
            ),
            {"id": row_id},
        )
        db_session.add(
            StockTaskAssignment(
                workspace_id=workspace_id,
                stock_report_item_id=row_id,
                task_id=seeded.task.client_id,
                item_id=seeded.item.client_id,
                quantity=3,
                state=StockTaskAssignmentStateEnum.AWAITING,
            )
        )
        await db_session.execute(
            text("UPDATE tasks SET is_stock_assignment = true WHERE client_id = :id"),
            {"id": seeded.task.client_id},
        )
        await db_session.commit()

        # Fixture precondition: the crafted row/assignment/flag are still consistent.
        await assert_stock_report_clean(db_session, workspace_id)
        await db_session.commit()  # the check above autobegins a transaction (B5)

        await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 9)])

        history = (
            (
                await db_session.execute(
                    select(StockReportHistoryRecord)
                    .where(StockReportHistoryRecord.stock_report_item_id == row_id)
                    .order_by(
                        StockReportHistoryRecord.created_at,
                        StockReportHistoryRecord.client_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(history) == 2
        record = history[-1]
        assert record.quantity_requested == 9
        assert record.priority == StockReportPriorityEnum.HIGH
        assert record.priority_order == 2
        assert record.quantity_awaiting == 0

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C4 — replay (MC-9)
# ---------------------------------------------------------------------------


async def test_c4a_replay_of_mixed_batch_writes_nothing(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        props_changed = {"wood_group": ["teak"]}
        props_unchanged = {"wood_group": ["pine"]}
        props_new = {"wood_group": ["oak"]}
        await _AD(
            db_session,
            workspace_id,
            [
                _entry(0, "Dining Chairs", props_changed, 5),
                _entry(1, "Dining Chairs", props_unchanged, 7),
            ],
        )

        batch = [
            _entry(0, "Dining Chairs", props_new, 2),
            _entry(1, "Dining Chairs", props_changed, 9),
            _entry(2, "Dining Chairs", props_unchanged, 7),
        ]
        await _AD(db_session, workspace_id, batch)

        async with record_statements(db_session) as statements:
            result = await _AD(db_session, workspace_id, batch)

        assert count_writes(statements, WRITE_TABLES) == 0
        assert result.events == []
        assert all(o.outcome == StockDemandOutcomeEnum.APPLIED for o in result.outcomes)

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c4b_replay_of_all_new_batch_omits_insert(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        batch = [
            _entry(0, "Dining Chairs", {"wood_group": ["oak"]}, 2),
            _entry(1, "Dining Chairs", {"wood_group": ["pine"]}, 4),
        ]
        await _AD(db_session, workspace_id, batch)

        async with record_statements(db_session) as statements:
            await _AD(db_session, workspace_id, batch)

        assert count_writes(statements, {"stock_report_items"}) == 0

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C5 — concurrency (MC-4 invariant)
# ---------------------------------------------------------------------------


async def test_c5a_concurrent_first_deliveries_of_same_identity_leave_one_row(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        properties_raw = {"wood_group": ["teak"]}
        barrier = asyncio.Barrier(2)

        async def _run_main():
            await barrier.wait()
            return await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 5)])

        async def _run_second():
            async for session2 in get_db_session():
                await barrier.wait()
                return await _AD(session2, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 5)])
            raise AssertionError("Database session generator yielded no session")

        result_a, result_b = await asyncio.wait_for(
            asyncio.gather(_run_main(), _run_second()), timeout=10
        )

        rows = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.workspace_id == workspace_id)
            )
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].quantity_requested == 5

        assert result_a.outcomes[0].outcome == StockDemandOutcomeEnum.APPLIED
        assert result_b.outcomes[0].outcome == StockDemandOutcomeEnum.APPLIED

        created_events = [
            e for e in result_a.events + result_b.events if e.event_name == "stock_report_item:created"
        ]
        assert len(created_events) == 1

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c5b_concurrent_batches_opposite_order_both_complete(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        props_x = {"wood_group": ["teak"]}
        props_y = {"wood_group": ["oak"]}
        entries_a = [_entry(0, "Dining Chairs", props_x, 1), _entry(1, "Dining Chairs", props_y, 2)]
        entries_b = [_entry(0, "Dining Chairs", props_y, 2), _entry(1, "Dining Chairs", props_x, 1)]
        barrier = asyncio.Barrier(2)

        async def _run_a():
            await barrier.wait()
            return await _AD(db_session, workspace_id, entries_a)

        async def _run_b():
            async for session2 in get_db_session():
                await barrier.wait()
                return await _AD(session2, workspace_id, entries_b)
            raise AssertionError("Database session generator yielded no session")

        await asyncio.wait_for(asyncio.gather(_run_a(), _run_b()), timeout=10)

        rows = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.workspace_id == workspace_id)
            )
        ).scalars().all()
        assert len(rows) == 2

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c5c_concurrent_soft_delete_under_lock_raises_and_heals(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        properties_raw = {"wood_group": ["teak"]}
        first = await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 5)])
        row_id = first.events[0].client_id

        holder_locked = asyncio.Event()
        release_holder = asyncio.Event()

        async def _holder():
            async for session in get_db_session():
                await session.execute(
                    select(StockReportItem)
                    .where(StockReportItem.client_id == row_id)
                    .with_for_update()
                )
                await session.execute(
                    text(
                        "UPDATE stock_report_items SET is_deleted = true, deleted_at = :now "
                        "WHERE client_id = :id"
                    ),
                    {"now": NOW, "id": row_id},
                )
                holder_locked.set()
                await asyncio.wait_for(release_holder.wait(), timeout=5)
                await session.commit()
                return
            raise AssertionError("Database session generator yielded no session")

        holder_task = asyncio.create_task(_holder())
        await asyncio.wait_for(holder_locked.wait(), timeout=5)

        async with record_statements(db_session) as statements:
            demand_task = asyncio.create_task(
                _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 7)])
            )
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(asyncio.shield(demand_task), timeout=0.5)

            release_holder.set()
            await asyncio.wait_for(holder_task, timeout=5)

            with pytest.raises(RuntimeError, match="stock demand identity vanished under lock"):
                await asyncio.wait_for(demand_task, timeout=5)

        assert count_writes(statements, WRITE_TABLES) == 0

        rows = (
            await db_session.execute(
                select(StockReportItem).where(
                    StockReportItem.workspace_id == workspace_id,
                    StockReportItem.client_id == row_id,
                    StockReportItem.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        assert rows == []
        await db_session.commit()  # the check above autobegins a transaction (B5)

        await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 7)])
        new_row = (
            await db_session.execute(
                select(StockReportItem).where(
                    StockReportItem.workspace_id == workspace_id,
                    StockReportItem.is_deleted.is_(False),
                )
            )
        ).scalar_one()
        assert new_row.client_id != row_id
        assert new_row.quantity_requested == 7

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C6 — statement bound (D6)
# ---------------------------------------------------------------------------


async def test_c6a_statement_count_equal_across_batch_sizes_all_new(db_session):
    seeded_small = await seed_stock_report_workspace(db_session, suffix="c6asmall")
    seeded_large = await seed_stock_report_workspace(db_session, suffix="c6alarge")
    await db_session.commit()
    ws_small, ws_large = seeded_small.workspace.client_id, seeded_large.workspace.client_id
    try:
        small_entries = [_entry(i, "Dining Chairs", {"wood_group": [f"v{i}"]}, 1) for i in range(3)]
        large_entries = [_entry(i, "Dining Chairs", {"wood_group": [f"v{i}"]}, 1) for i in range(300)]

        async with record_statements(db_session) as small_statements:
            await _AD(db_session, ws_small, small_entries)
        async with record_statements(db_session) as large_statements:
            await _AD(db_session, ws_large, large_entries)

        assert len(small_statements) == len(large_statements)
        assert len(small_statements) <= 8

        await assert_stock_report_clean(db_session, ws_small)
        await assert_stock_report_clean(db_session, ws_large)
    finally:
        await purge_stock_report_workspace(db_session, ws_small)
        await purge_stock_report_workspace(db_session, ws_large)
        await db_session.commit()


async def test_c6b_statement_count_equal_across_batch_sizes_all_changed(db_session):
    seeded_small = await seed_stock_report_workspace(db_session, suffix="c6bsmall")
    seeded_large = await seed_stock_report_workspace(db_session, suffix="c6blarge")
    await db_session.commit()
    ws_small, ws_large = seeded_small.workspace.client_id, seeded_large.workspace.client_id
    try:
        small_v1 = [_entry(i, "Dining Chairs", {"wood_group": [f"v{i}"]}, 1) for i in range(3)]
        large_v1 = [_entry(i, "Dining Chairs", {"wood_group": [f"v{i}"]}, 1) for i in range(300)]
        await _AD(db_session, ws_small, small_v1)
        await _AD(db_session, ws_large, large_v1)

        small_v2 = [_entry(i, "Dining Chairs", {"wood_group": [f"v{i}"]}, 2) for i in range(3)]
        large_v2 = [_entry(i, "Dining Chairs", {"wood_group": [f"v{i}"]}, 2) for i in range(300)]

        async with record_statements(db_session) as small_statements:
            await _AD(db_session, ws_small, small_v2)
        async with record_statements(db_session) as large_statements:
            await _AD(db_session, ws_large, large_v2)

        assert len(small_statements) == len(large_statements)
        assert len(small_statements) <= 8

        await assert_stock_report_clean(db_session, ws_small)
        await assert_stock_report_clean(db_session, ws_large)
    finally:
        await purge_stock_report_workspace(db_session, ws_small)
        await purge_stock_report_workspace(db_session, ws_large)
        await db_session.commit()


async def test_c6c_statement_count_equal_across_batch_sizes_all_unchanged(db_session):
    seeded_small = await seed_stock_report_workspace(db_session, suffix="c6csmall")
    seeded_large = await seed_stock_report_workspace(db_session, suffix="c6clarge")
    await db_session.commit()
    ws_small, ws_large = seeded_small.workspace.client_id, seeded_large.workspace.client_id
    try:
        small = [_entry(i, "Dining Chairs", {"wood_group": [f"v{i}"]}, 1) for i in range(3)]
        large = [_entry(i, "Dining Chairs", {"wood_group": [f"v{i}"]}, 1) for i in range(300)]
        await _AD(db_session, ws_small, small)
        await _AD(db_session, ws_large, large)

        async with record_statements(db_session) as small_statements:
            await _AD(db_session, ws_small, small)
        async with record_statements(db_session) as large_statements:
            await _AD(db_session, ws_large, large)

        assert len(small_statements) == len(large_statements)
        assert len(small_statements) == 5
        assert len(small_statements) <= 8

        await assert_stock_report_clean(db_session, ws_small)
        await assert_stock_report_clean(db_session, ws_large)
    finally:
        await purge_stock_report_workspace(db_session, ws_small)
        await purge_stock_report_workspace(db_session, ws_large)
        await db_session.commit()


async def test_c6d_statement_count_equal_across_batch_sizes_one_unknown_category(db_session):
    seeded_small = await seed_stock_report_workspace(db_session, suffix="c6dsmall")
    seeded_large = await seed_stock_report_workspace(db_session, suffix="c6dlarge")
    await db_session.commit()
    ws_small, ws_large = seeded_small.workspace.client_id, seeded_large.workspace.client_id
    try:

        def build(n):
            entries = [_entry(0, "Nonexistent Category", {}, 1)]
            entries += [_entry(i, "Dining Chairs", {"wood_group": [f"v{i}"]}, 1) for i in range(1, n)]
            return entries

        async with record_statements(db_session) as small_statements:
            await _AD(db_session, ws_small, build(3))
        async with record_statements(db_session) as large_statements:
            await _AD(db_session, ws_large, build(300))

        assert len(small_statements) == len(large_statements)
        assert len(small_statements) <= 8

        await assert_stock_report_clean(db_session, ws_small)
        await assert_stock_report_clean(db_session, ws_large)
    finally:
        await purge_stock_report_workspace(db_session, ws_small)
        await purge_stock_report_workspace(db_session, ws_large)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C8 — events (MC-19). C8(a) is discharged by test_c1a (same mutation, see the
# plan's "(C1(a) mutation)" cell); C8(c) is a fresh fixture combining an
# unchanged and a skipped entry in one request.
# ---------------------------------------------------------------------------


async def test_c8b_updated_event_payload_matches_returning_values(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        properties_raw = {"wood_group": ["teak"]}
        first = await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 5)])
        row_id = first.events[0].client_id
        await db_session.commit()
        await ensure_active_snapshots(db_session, workspace_id, now=NOW)
        await set_snapshot_position(db_session, row_id, "high", 1)
        await db_session.commit()

        result = await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 9)])

        assert len(result.events) == 1
        event = result.events[0]
        assert event.event_name == "stock_report_item:updated"
        assert event.client_id == row_id
        # Four quantity keys only: the snapshot's position is not the row's payload.
        assert event.extra == {
            "quantity_requested": 9,
            "quantity_in_queue": 0,
            "quantity_in_progress": 0,
            "quantity_awaiting": 0,
        }

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c8c_unchanged_and_skipped_entries_emit_no_events(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        properties_raw = {"wood_group": ["teak"]}
        await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 5)])

        result = await _AD(
            db_session,
            workspace_id,
            [
                _entry(0, "Dining Chairs", properties_raw, 5),
                _entry(1, "Serving Trolleys", {}, 1),
            ],
        )

        assert result.events == []
        assert [o.outcome for o in result.outcomes] == [
            StockDemandOutcomeEnum.APPLIED,
            StockDemandOutcomeEnum.CATEGORY_NOT_FOUND,
        ]

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c8d_event_workspace_id_is_the_argument_not_empty(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        result = await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", {"wood_group": ["teak"]}, 5)])
        assert len(result.events) == 1
        assert result.events[0].workspace_id == workspace_id
        assert result.events[0].workspace_id != ""

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()
