"""Plan 12 — the two ordering commands (master plan §6.5; intention §7A MC-7, §6A
MC-6, §14B B2, MC-17, MC-19).

Fixture, per plan 12 §6: rows are created through the demand service `AD` (the only
creator of rows) and `priority`/`priority_order` are then written by raw SQL. The
seed orders the `high` group **against** its ordering key — the row at order 1
carries the group's largest `client_id` and the row at order 4 its smallest — so a
shift that renumbers by `client_id` cannot pass (`client_id` is a ULID with no
monotonic counter, master plan §10).

`apply_stock_demand` refuses a session already in a transaction, so every test here
is a committing test: `seed -> commit -> AD -> ... -> finally purge + commit`
(§9 rule 1, charter rule 11½).

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
from beyo_manager.domain.stock_report.enums import (
    StockReportHistoryRecordTypeEnum,
    StockReportPriorityEnum,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.services.commands.stock_report.apply_stock_demand import (
    apply_stock_demand,
)
from beyo_manager.services.commands.stock_report.set_stock_report_item_priority import (
    set_stock_report_item_priority,
)
from beyo_manager.services.commands.stock_report.set_stock_report_item_priority_order import (
    set_stock_report_item_priority_order,
)
from beyo_manager.services.commands.stock_report.stock_demand_entries import DemandEntry
from beyo_manager.services.context import ServiceContext
from tests.helpers.stock_report import (
    assert_stock_report_clean,
    capture_dispatch,
    make_ctx,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
_TIMEOUT_MS = Settings.model_fields["stock_demand_webhook_timeout_ms"].default

PRIORITY_SITE = (
    "beyo_manager.services.commands.stock_report.set_stock_report_item_priority.dispatch"
)
ORDER_SITE = (
    "beyo_manager.services.commands.stock_report"
    ".set_stock_report_item_priority_order.dispatch"
)


def _entry(index, properties_raw, quantity=10, category="Dining Chairs"):
    return DemandEntry(
        index=index,
        item_category_raw=category,
        properties_raw=properties_raw,
        properties_normalized=normalize_stock_criteria(properties_raw),
        properties_signature=compute_stock_criteria_signature(properties_raw),
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


class Groups:
    """The seeded labels of plan 12 §6: `high` = A1 B2 C3 D4, `low` = X1 Y2, N."""

    def __init__(self, ids):
        self.A, self.B, self.C, self.D, self.X, self.Y, self.N = ids

    @property
    def high(self):
        return (self.A, self.B, self.C, self.D)


async def _seed_groups(session, workspace_id):
    """Seven rows through `AD`, then priority/order by raw SQL.

    The labels are bound by **sorting the real ids at runtime**, descending, so
    `priority_order` ascending disagrees with `client_id` ascending inside `high`.
    """
    await _AD(
        session,
        workspace_id,
        [_entry(index, {"wood_group": [f"teak{index}"]}) for index in range(7)],
    )
    ids = sorted(
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
    groups = Groups(ids)
    assignments = [
        (groups.A, "high", 1),
        (groups.B, "high", 2),
        (groups.C, "high", 3),
        (groups.D, "high", 4),
        (groups.X, "low", 1),
        (groups.Y, "low", 2),
    ]
    for client_id, priority, order in assignments:
        await session.execute(
            text(
                "UPDATE stock_report_items SET priority = :priority, "
                "priority_order = :order WHERE client_id = :client_id"
            ),
            {"priority": priority, "order": order, "client_id": client_id},
        )
    # `high`'s order 1 must carry the group's largest client_id (plan 12 §6).
    assert groups.A > groups.B > groups.C > groups.D
    await session.commit()
    return groups


async def _state(session, workspace_id):
    """`(priority, priority_order)` of every non-deleted row in the workspace."""
    rows = (
        await session.execute(
            select(
                StockReportItem.client_id,
                StockReportItem.priority,
                StockReportItem.priority_order,
            ).where(
                StockReportItem.workspace_id == workspace_id,
                StockReportItem.is_deleted.is_(False),
            )
        )
    ).all()
    return {
        client_id: (priority.value if priority is not None else None, order)
        for client_id, priority, order in rows
    }


async def _records(session, workspace_id):
    return (
        (
            await session.execute(
                select(StockReportHistoryRecord).where(
                    StockReportHistoryRecord.workspace_id == workspace_id,
                    StockReportHistoryRecord.type.in_(
                        (
                            StockReportHistoryRecordTypeEnum.PRIORITY_CHANGE,
                            StockReportHistoryRecordTypeEnum.PRIORITY_ORDER_CHANGE,
                        )
                    ),
                )
            )
        )
        .scalars()
        .all()
    )


async def _row(session, client_id):
    return (
        await session.execute(
            select(StockReportItem)
            .where(StockReportItem.client_id == client_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


def _seller(session, seeded):
    """The identity of `S`, a permitted role, captured **once** while the seed's ORM
    instances are live: `session.rollback()` expires them, and a later attribute read
    from a sync helper would attempt IO outside the greenlet context.
    """
    return make_ctx(session, seeded, role_name="seller").identity


def _ctx(session, identity, incoming_data):
    return ServiceContext(
        identity=identity, incoming_data=incoming_data, session=session
    )


async def _SO(session, identity, client_id, target, *, monkeypatch=None):
    captured = (
        capture_dispatch(monkeypatch, ORDER_SITE) if monkeypatch is not None else None
    )
    ctx = _ctx(session, identity, {"client_id": client_id, "priority_order": target})
    result = await set_stock_report_item_priority_order(ctx)
    return (result, ctx, captured)


async def _SP(session, identity, client_id, priority, *, monkeypatch=None):
    captured = (
        capture_dispatch(monkeypatch, PRIORITY_SITE)
        if monkeypatch is not None
        else None
    )
    ctx = _ctx(session, identity, {"client_id": client_id, "priority": priority})
    result = await set_stock_report_item_priority(ctx)
    return (result, ctx, captured)


# ---------------------------------------------------------------------------
# The in-group move (MC-7 rows 1-5)
# ---------------------------------------------------------------------------


async def test_move_up_shifts_only_the_block_it_enters(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    S = _seller(db_session, seeded)
    try:
        g = await _seed_groups(db_session, workspace_id)

        _result, ctx, captured = await _SO(
            db_session, S, g.C, 1, monkeypatch=monkeypatch
        )

        state = await _state(db_session, workspace_id)
        assert [state[client_id] for client_id in g.high] == [
            ("high", 2),
            ("high", 3),
            ("high", 1),
            ("high", 4),
        ]
        # One record, for the mover only.
        records = await _records(db_session, workspace_id)
        assert [
            (r.stock_report_item_id, r.type, r.priority_order) for r in records
        ] == [
            (
                g.C,
                StockReportHistoryRecordTypeEnum.PRIORITY_ORDER_CHANGE,
                1,
            )
        ]
        # Exactly three `:updated` — the mover and the two shifted neighbours.
        assert [(e.event_name, e.client_id) for e in captured] == [
            ("stock_report_item:updated", g.C),
            ("stock_report_item:updated", g.A),
            ("stock_report_item:updated", g.B),
        ]
        assert captured[0].extra["priority_order"] == 1
        assert captured[0].extra["priority"] == "high"
        # Only the mover is stamped (MC-17).
        assert (await _row(db_session, g.C)).updated_at == ctx.now
        assert (await _row(db_session, g.A)).updated_at is None
        assert (await _row(db_session, g.D)).updated_at is None
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_move_down_shifts_only_the_block_it_leaves(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    S = _seller(db_session, seeded)
    try:
        g = await _seed_groups(db_session, workspace_id)

        await _SO(db_session, S, g.A, 3)

        state = await _state(db_session, workspace_id)
        assert [state[client_id] for client_id in g.high] == [
            ("high", 3),
            ("high", 1),
            ("high", 2),
            ("high", 4),
        ]
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_move_to_the_held_position_writes_nothing(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    S = _seller(db_session, seeded)
    try:
        g = await _seed_groups(db_session, workspace_id)
        before = await _state(db_session, workspace_id)

        result, _ctx, captured = await _SO(
            db_session, S, g.B, 2, monkeypatch=monkeypatch
        )

        assert await _state(db_session, workspace_id) == before
        assert await _records(db_session, workspace_id) == []
        assert captured == []
        assert (await _row(db_session, g.B)).updated_at is None
        assert result["stock_report_item"]["priority_order"] == 2
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


@pytest.mark.parametrize("target", [0, 5])
async def test_target_outside_the_group_is_refused(db_session, target):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    S = _seller(db_session, seeded)
    try:
        g = await _seed_groups(db_session, workspace_id)
        before = await _state(db_session, workspace_id)

        with pytest.raises(ValidationError) as excinfo:
            await _SO(db_session, S, g.A, target)
        assert str(excinfo.value).startswith("STOCK_REPORT_TARGET_OUT_OF_RANGE:")

        await db_session.rollback()
        assert await _state(db_session, workspace_id) == before
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_last_position_of_the_group_is_a_noop_not_a_refusal(db_session):
    """The upper boundary `t == p == n` is inside the range, not outside it."""
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    S = _seller(db_session, seeded)
    try:
        g = await _seed_groups(db_session, workspace_id)
        before = await _state(db_session, workspace_id)

        await _SO(db_session, S, g.D, 4)

        assert await _state(db_session, workspace_id) == before
        assert await _records(db_session, workspace_id) == []
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_row_without_a_priority_cannot_be_ordered(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    S = _seller(db_session, seeded)
    try:
        g = await _seed_groups(db_session, workspace_id)

        with pytest.raises(ValidationError) as excinfo:
            await _SO(db_session, S, g.N, 1)
        assert str(excinfo.value).startswith("STOCK_REPORT_ROW_HAS_NO_PRIORITY:")
        await db_session.rollback()
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_non_integer_target_is_a_validation_error(db_session):
    """`priority_order` is `StrictInt`: the string "2" is a 422, never coerced."""
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    S = _seller(db_session, seeded)
    try:
        g = await _seed_groups(db_session, workspace_id)
        with pytest.raises(ValidationError):
            await _SO(db_session, S, g.B, "2")
        await db_session.rollback()
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# The priority change (MC-7 rows 6-9)
# ---------------------------------------------------------------------------


async def test_priority_change_closes_the_source_gap_and_appends(
    db_session, monkeypatch
):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    actor = seeded.manager.client_id
    S = _seller(db_session, seeded)
    try:
        g = await _seed_groups(db_session, workspace_id)

        _result, ctx, captured = await _SP(
            db_session, S, g.B, "low", monkeypatch=monkeypatch
        )

        state = await _state(db_session, workspace_id)
        assert state[g.A] == ("high", 1)
        assert state[g.C] == ("high", 2)
        assert state[g.D] == ("high", 3)
        assert state[g.X] == ("low", 1)
        assert state[g.Y] == ("low", 2)
        assert state[g.B] == ("low", 3)

        records = await _records(db_session, workspace_id)
        assert len(records) == 1
        record = records[0]
        assert record.stock_report_item_id == g.B
        assert record.type == StockReportHistoryRecordTypeEnum.PRIORITY_CHANGE
        assert record.priority == StockReportPriorityEnum.LOW
        assert record.priority_order == 3
        assert record.quantity_requested == 10
        assert record.quantity_awaiting == 0
        assert record.created_by_id == actor
        assert record.created_at == ctx.now

        assert [(e.event_name, e.client_id) for e in captured] == [
            ("stock_report_item:updated", g.B),
            ("stock_report_item:updated", g.C),
            ("stock_report_item:updated", g.D),
        ]
        assert captured[0].extra["priority"] == "low"
        # Only the mover is stamped (MC-17).
        assert (await _row(db_session, g.B)).updated_by_id == actor
        assert (await _row(db_session, g.C)).updated_at is None
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_priority_cleared_nulls_the_order_too(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    S = _seller(db_session, seeded)
    try:
        g = await _seed_groups(db_session, workspace_id)

        await _SP(db_session, S, g.B, None)

        state = await _state(db_session, workspace_id)
        assert state[g.B] == (None, None)
        assert [state[client_id] for client_id in (g.A, g.C, g.D)] == [
            ("high", 1),
            ("high", 2),
            ("high", 3),
        ]
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_null_row_given_a_priority_is_appended_last(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    S = _seller(db_session, seeded)
    try:
        g = await _seed_groups(db_session, workspace_id)

        await _SP(db_session, S, g.N, "high")

        state = await _state(db_session, workspace_id)
        assert state[g.N] == ("high", 5)
        assert [state[client_id] for client_id in g.high] == [
            ("high", 1),
            ("high", 2),
            ("high", 3),
            ("high", 4),
        ]
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


@pytest.mark.parametrize("label,value", [("B", "high"), ("N", None)])
async def test_setting_the_priority_a_row_already_has_writes_nothing(
    db_session, monkeypatch, label, value
):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    S = _seller(db_session, seeded)
    try:
        g = await _seed_groups(db_session, workspace_id)
        before = await _state(db_session, workspace_id)
        client_id = getattr(g, label)

        _result, _ctx, captured = await _SP(
            db_session, S, client_id, value, monkeypatch=monkeypatch
        )

        assert await _state(db_session, workspace_id) == before
        assert await _records(db_session, workspace_id) == []
        assert captured == []
        assert (await _row(db_session, client_id)).updated_at is None
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_unknown_priority_token_is_a_validation_error(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    S = _seller(db_session, seeded)
    try:
        g = await _seed_groups(db_session, workspace_id)
        with pytest.raises(ValidationError):
            await _SP(db_session, S, g.B, "urgent")
        await db_session.rollback()
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_priority_lookup_refuses_foreign_deleted_and_absent_rows(db_session):
    """The tenancy and visibility boundary: the foreign row is a cross-workspace
    reference — same category name, same properties, same `high` group with the same
    orders — so tenancy is the only reason the call refuses."""
    seeded = await seed_stock_report_workspace(db_session)
    foreign = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    foreign_id = foreign.workspace.client_id
    S = _seller(db_session, seeded)
    try:
        g = await _seed_groups(db_session, workspace_id)
        fg = await _seed_groups(db_session, foreign_id)
        await db_session.execute(
            text(
                "UPDATE stock_report_items SET is_deleted = true "
                "WHERE client_id = :client_id"
            ),
            {"client_id": g.N},
        )
        await db_session.commit()
        foreign_before = await _state(db_session, foreign_id)

        for client_id in (fg.B, g.N, "sri_absent"):
            with pytest.raises(NotFound):
                await _SP(db_session, S, client_id, "low")
            await db_session.rollback()

        assert await _state(db_session, foreign_id) == foreign_before
        assert await _records(db_session, foreign_id) == []
        assert await _records(db_session, workspace_id) == []
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await purge_stock_report_workspace(db_session, foreign_id)
        await db_session.commit()
