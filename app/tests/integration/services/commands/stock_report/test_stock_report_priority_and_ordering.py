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

import itertools
import time
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from beyo_manager.config import Settings
from beyo_manager.domain.items.enums import ItemStateEnum
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
    normalize_stock_criteria,
)
from beyo_manager.domain.stock_report.enums import (
    StockReportHistoryRecordTypeEnum,
    StockReportPriorityEnum,
    StockTaskAssignmentStateEnum,
)
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.stock_report._move_assignment import move_assignment
from beyo_manager.services.commands.stock_report.apply_stock_demand import (
    apply_stock_demand,
)
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from beyo_manager.services.commands.stock_report.set_stock_report_item_priority import (
    set_stock_report_item_priority,
)
from beyo_manager.services.commands.stock_report.set_stock_report_item_priority_order import (
    set_stock_report_item_priority_order,
)
from beyo_manager.services.commands.stock_report.stock_demand_entries import DemandEntry
from beyo_manager.services.context import ServiceContext
from tests.helpers.statement_listener import count_writes, record_statements
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
# The four tables plan 12 C1(c)/C1(k) count writes on (the project's established
# set, `test_apply_stock_demand.py:WRITE_TABLES`).
WRITE_TABLES = {
    "stock_report_items",
    "stock_task_assignments",
    "stock_report_history_records",
    "tasks",
}

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


_scalar_ids = itertools.count(2)


async def _awaiting_assignment(session, seeded, row_client_id, quantity):
    """Give a row a real `awaiting` assignment of `quantity`, so its live
    `quantity_awaiting` counter is non-zero **without planting drift** (plan 12
    C3(d): the record's `quantity_awaiting` clause cannot discriminate at 0).

    `CR` sets `quantity = max(item.quantity, 1)`, so the item is seeded at the
    intended quantity rather than edited afterwards.
    """
    suffix = uuid4().hex[:10]
    item = Item(
        client_id=f"itm_sr_{suffix}",
        workspace_id=seeded.workspace.client_id,
        article_number=f"SR-{suffix}",
        state=ItemStateEnum.PENDING,
        quantity=quantity,
        item_category_id=seeded.categories[0].client_id,
        properties={"wood_type": "Teak", "upholstery": "Down"},
    )
    task = Task(
        client_id=f"tsk_sr_{suffix}",
        workspace_id=seeded.workspace.client_id,
        task_scalar_id=next(_scalar_ids),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=seeded.manager.client_id,
    )
    session.add_all([item, task])
    await session.flush()
    session.add(
        TaskItem(
            client_id=f"tim_sr_{suffix}",
            workspace_id=seeded.workspace.client_id,
            task_id=task.client_id,
            item_id=item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=seeded.manager.client_id,
        )
    )
    await session.flush()
    created = await create_stock_task_assignments(
        make_ctx(
            session,
            seeded,
            role_name="worker",
            incoming_data={
                "entries": [
                    {
                        "stock_report_item_id": row_client_id,
                        "task_id": task.client_id,
                        "item_id": item.client_id,
                        "override_property_mismatch": True,
                    }
                ]
            },
        )
    )
    assignment_id = created["stock_task_assignments"][0]["client_id"]
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
        StockTaskAssignmentStateEnum.AWAITING,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="test",
    )
    await session.commit()
    return assignment_id


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
        # Every payload carries the position **after** the move (C6(a)), not the one
        # the row held when the command started.
        assert [
            (event.extra["priority"], event.extra["priority_order"])
            for event in captured
        ] == [("high", 1), ("high", 2), ("high", 3)]
        # Only the mover is stamped (MC-17): A and B are shifted and must not be,
        # D is untouched.
        assert (await _row(db_session, g.C)).updated_at == ctx.now
        assert (await _row(db_session, g.A)).updated_at is None
        assert (await _row(db_session, g.B)).updated_at is None
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

        async with record_statements(db_session) as statements:
            result, _ctx, captured = await _SO(
                db_session, S, g.B, 2, monkeypatch=monkeypatch
            )

        assert await _state(db_session, workspace_id) == before
        assert await _records(db_session, workspace_id) == []
        assert captured == []
        assert (await _row(db_session, g.B)).updated_at is None
        # B2: not one write reaches any of the four tables.
        assert count_writes(statements, WRITE_TABLES) == 0
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
        # C5(a): the mover is stamped and nothing else in the workspace is —
        # neither the shifted rows (C, D) nor the untouched ones (A, X, Y).
        mover = await _row(db_session, g.B)
        assert mover.updated_by_id == actor
        assert mover.updated_at == ctx.now
        for label in ("A", "C", "D", "X", "Y"):
            other = await _row(db_session, getattr(g, label))
            assert other.updated_at is None, label
            assert other.updated_by_id is None, label
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_the_priority_record_snapshots_the_live_awaiting_counter(db_session):
    """Plan 12 C3(d) — `SP(B, low)` with B's `quantity_awaiting = 4`.

    MC-6 "Timing and values": the record is inserted **after** all row mutations
    and snapshots `priority_order` (3, the appended position) and the row's **live**
    `quantity_awaiting` (4). A record built before the append would read
    `priority_order` NULL.

    **This test is currently RED on the unmutated tree, and that is the finding**
    (tester, batch D1 — routed `BLOCKED-PRODUCTION`):

      input     `SP(B, low)` on a row carrying one `awaiting` assignment of q = 4,
                a scenario that plants no drift (§9 rule 2 therefore requires
                `assert_stock_report_clean`).
      expected  the record snapshots `quantity_awaiting = 4` (MC-6) **and** the
                workspace is consistent.
      observed  the record is correct, but `compute_stock_report_divergences`
                answers `[{'kind': 'goal_total', 'client_id': <the new
                priority_change record>, 'field': 'quantity_awaiting',
                'stored': 4, 'expected': 0}]`.

    Cause: `consistency.py:compute_stock_report_divergences` applies the
    `goal_total` check to **every** history record, while intention §14C defines it
    as "`quantity_awaiting` of each **goal record**" — a goal record being a
    `quantity_requested_change` (§6.2/MC-5). A `priority_change` record legitimately
    snapshots a non-zero live counter that nothing credits, so it can never satisfy
    the check. `repair_stock_report.py`'s `goal_total` branch would then overwrite
    that snapshot with 0, contradicting §6.2's "Priority records are never touched
    after they are written". The fix is in APPROVED phase 3's files, not phase 12's.
    """
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    S = _seller(db_session, seeded)
    try:
        g = await _seed_groups(db_session, workspace_id)
        await _awaiting_assignment(db_session, seeded, g.B, 4)
        assert (await _row(db_session, g.B)).quantity_awaiting == 4

        _result, _ctx, _captured = await _SP(db_session, S, g.B, "low")

        records = await _records(db_session, workspace_id)
        assert len(records) == 1
        # The row's own clauses — these pass today.
        assert records[0].priority_order == 3
        assert records[0].quantity_awaiting == 4
        # §9 rule 2 — this is the clause that fails.
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

        async with record_statements(db_session) as statements:
            _result, _ctx, captured = await _SP(
                db_session, S, client_id, value, monkeypatch=monkeypatch
            )

        assert await _state(db_session, workspace_id) == before
        assert await _records(db_session, workspace_id) == []
        assert captured == []
        assert (await _row(db_session, client_id)).updated_at is None
        # B2: zero writes (plan 12 C1(k)/C1(l)).
        assert count_writes(statements, WRITE_TABLES) == 0
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
