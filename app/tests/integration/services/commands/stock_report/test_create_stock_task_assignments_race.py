"""Plan 8 C5(a) — the Item lock serializes two concurrent `CR` calls naming the same
item on two different rows/tasks (MC-4 error contract). Precedent:
`test_apply_stock_demand.py`'s C5 tests (`asyncio.Barrier`, a second `get_db_session()`).

C5(b) (opposite-order two-item lock acquisition, owner card C / L-29) is built below
by the tester: two sessions, two items, opposite request order, one barrier.
"""

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.errors.stock_report import (
    StockAssignmentPropertyMismatch,
    StockAssignmentRefused,
)
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from tests.helpers.statement_listener import count_writes, record_statements
from tests.helpers.stock_report import (
    assert_stock_report_clean,
    make_ctx,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)


async def _make_row(session, seeded, suffix, *, criteria=None):
    criteria = criteria if criteria is not None else {"wood_group": ["teak"]}
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties=criteria,
        properties_signature=compute_stock_criteria_signature(criteria),
        quantity_requested=1,
        client_id=f"sri_race_{suffix}_{seeded.workspace.client_id}",
    )
    session.add(row)
    await session.flush()
    return row


async def _second_task(session, seeded, suffix, *, item=None):
    from sqlalchemy import func

    from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
    from beyo_manager.models.tables.tasks.task import Task
    from beyo_manager.models.tables.tasks.task_item import TaskItem
    from beyo_manager.domain.tasks.enums import TaskItemRoleEnum

    next_scalar_id = (
        await session.scalar(
            select(func.max(Task.task_scalar_id)).where(
                Task.workspace_id == seeded.workspace.client_id
            )
        )
        or 0
    ) + 1
    task = Task(
        client_id=f"tsk_race_{suffix}_{seeded.workspace.client_id}",
        workspace_id=seeded.workspace.client_id,
        task_scalar_id=next_scalar_id,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=seeded.manager.client_id,
    )
    session.add(task)
    await session.flush()
    session.add(
        TaskItem(
            client_id=f"tim_race_{suffix}_{seeded.workspace.client_id}",
            workspace_id=seeded.workspace.client_id,
            task_id=task.client_id,
            item_id=(item or seeded.item).client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=seeded.manager.client_id,
        )
    )
    await session.flush()
    return task


async def _second_item(session, seeded, suffix):
    from beyo_manager.domain.items.enums import ItemStateEnum
    from beyo_manager.models.tables.items.item import Item

    item = Item(
        client_id=f"itm_race_{suffix}_{seeded.workspace.client_id}",
        workspace_id=seeded.workspace.client_id,
        article_number=f"race-{suffix}-{seeded.workspace.client_id}",
        state=ItemStateEnum.PENDING,
        quantity=4,
        item_category_id=seeded.categories[0].client_id,
        properties={"wood_type": "Teak", "upholstery": "Down"},
    )
    session.add(item)
    await session.flush()
    return item


async def test_c5a_concurrent_create_on_the_same_item_leaves_exactly_one_active(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        row1 = await _make_row(db_session, seeded, "r1", criteria={"wood_group": ["teak"]})
        row2 = await _make_row(db_session, seeded, "r2", criteria={})
        task2 = await _second_task(db_session, seeded, "t2")
        item_client_id = seeded.item.client_id
        task1_client_id = seeded.task.client_id
        task2_client_id = task2.client_id
        row1_client_id = row1.client_id
        row2_client_id = row2.client_id
        await db_session.commit()

        barrier = asyncio.Barrier(2)

        entries_a = [
            {
                "stock_report_item_id": row1_client_id,
                "task_id": task1_client_id,
                "item_id": item_client_id,
                "override_property_mismatch": False,
            }
        ]
        entries_b = [
            {
                "stock_report_item_id": row2_client_id,
                "task_id": task2_client_id,
                "item_id": item_client_id,
                "override_property_mismatch": False,
            }
        ]

        async def _run_a():
            ctx = make_ctx(
                db_session, seeded, role_name="worker", incoming_data={"entries": entries_a}
            )
            await barrier.wait()
            try:
                return await create_stock_task_assignments(ctx), None
            except (StockAssignmentRefused, StockAssignmentPropertyMismatch) as exc:
                return None, exc

        async def _run_b():
            async for session2 in get_db_session():
                seeded_for_b = seeded
                ctx = make_ctx(
                    session2,
                    seeded_for_b,
                    role_name="worker",
                    incoming_data={"entries": entries_b},
                )
                await barrier.wait()
                try:
                    return await create_stock_task_assignments(ctx), None
                except (StockAssignmentRefused, StockAssignmentPropertyMismatch) as exc:
                    return None, exc
            raise AssertionError("Database session generator yielded no session")

        # C5(a) (owner card 1, 2026-09-21; master plan §9 rule 7): the losing call
        # must write nothing — the only clause that distinguishes the Item lock
        # from the unique-index backstop, since both answer the same reason.
        # `record_statements` listens at the shared engine (both sessions use the
        # one process-wide `_engine`), so a per-call recorder cannot be scoped to
        # only the loser's own connection; recording across the whole barrier-
        # released race and asserting the *total* write count is 1 is the
        # equivalent, race-scoped form of the same measurement — exactly one
        # participant is ever the winner, so "the loser wrote nothing" and "the
        # race wrote exactly once" are the same fact. Documented judgment call.
        async with record_statements(db_session) as statements:
            (result_a, error_a), (result_b, error_b) = await asyncio.wait_for(
                asyncio.gather(_run_a(), _run_b()), timeout=10
            )

        outcomes = [(result_a, error_a), (result_b, error_b)]
        winners = [r for r, e in outcomes if r is not None]
        losers = [e for r, e in outcomes if e is not None]
        assert len(winners) == 1
        assert len(losers) == 1
        assert losers[0].details == [{"index": 0, "reason": "item_already_assigned"}]

        active = (
            (
                await db_session.execute(
                    select(StockTaskAssignment).where(
                        StockTaskAssignment.workspace_id == workspace_id,
                        StockTaskAssignment.item_id == item_client_id,
                        StockTaskAssignment.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(active) == 1
        assert count_writes(statements, {"stock_task_assignments"}) == 1

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c5b_two_sessions_crossing_two_items_never_deadlock(db_session):
    """Plan 8 C5(b) (owner card C / L-29). Two sessions each create **two**
    assignments naming the same two items in **opposite request order**. If the two
    Item locks were taken in the order the entries arrive, the crossing pair would
    deadlock; `_locks.py:_lock` takes them in one `SELECT ... ORDER BY client_id ...
    FOR UPDATE`, so both sessions acquire ascending and neither can.

    Outcome per the row: both calls complete (the loser refuses, it does not raise a
    deadlock), each item ends with exactly one active assignment, and both rows'
    counters are correct.
    """
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        item1 = seeded.item
        item2 = await _second_item(db_session, seeded, "i2")
        row1 = await _make_row(db_session, seeded, "c5b1", criteria={"wood_group": ["teak"]})
        row2 = await _make_row(db_session, seeded, "c5b2", criteria={"upholstery": ["down"]})
        task_a1 = seeded.task                                        # PRIMARY item1
        task_a2 = await _second_task(db_session, seeded, "a2", item=item2)
        task_b1 = await _second_task(db_session, seeded, "b1", item=item1)
        task_b2 = await _second_task(db_session, seeded, "b2", item=item2)

        def _entry(row, task, item):
            return {
                "stock_report_item_id": row.client_id,
                "task_id": task.client_id,
                "item_id": item.client_id,
                "override_property_mismatch": False,
            }

        entries_a = [_entry(row1, task_a1, item1), _entry(row2, task_a2, item2)]
        entries_b = [_entry(row2, task_b2, item2), _entry(row1, task_b1, item1)]
        item1_id, item2_id = item1.client_id, item2.client_id
        row1_id, row2_id = row1.client_id, row2.client_id
        await db_session.commit()

        barrier = asyncio.Barrier(2)

        async def _call(session):
            ctx_entries = entries_a if session is db_session else entries_b
            ctx = make_ctx(
                session, seeded, role_name="worker", incoming_data={"entries": ctx_entries}
            )
            await barrier.wait()
            try:
                return await create_stock_task_assignments(ctx), None
            except (StockAssignmentRefused, StockAssignmentPropertyMismatch) as exc:
                return None, exc

        async def _run_b():
            async for session2 in get_db_session():
                return await _call(session2)
            raise AssertionError("Database session generator yielded no session")

        # Any deadlock surfaces here as a DBAPI error out of `gather`, and any
        # lock cycle that does not resolve surfaces as the bounded timeout.
        (result_a, error_a), (result_b, error_b) = await asyncio.wait_for(
            asyncio.gather(_call(db_session), _run_b()), timeout=15
        )

        outcomes = [(result_a, error_a), (result_b, error_b)]
        winners = [r for r, e in outcomes if r is not None]
        losers = [e for r, e in outcomes if e is not None]
        assert len(winners) == 1
        assert len(losers) == 1
        assert losers[0].details == [
            {"index": 0, "reason": "item_already_assigned"},
            {"index": 1, "reason": "item_already_assigned"},
        ]

        for item_id in (item1_id, item2_id):
            active = (
                (
                    await db_session.execute(
                        select(StockTaskAssignment).where(
                            StockTaskAssignment.workspace_id == workspace_id,
                            StockTaskAssignment.item_id == item_id,
                            StockTaskAssignment.is_deleted.is_(False),
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(active) == 1

        for row_id in (row1_id, row2_id):
            counters = (
                await db_session.execute(
                    select(
                        StockReportItem.quantity_in_queue,
                        StockReportItem.quantity_in_progress,
                        StockReportItem.quantity_awaiting,
                    ).where(StockReportItem.client_id == row_id)
                )
            ).one()
            # One item is one unit: the winner's single assignment per row.
            assert counters == (1, 0, 0)

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()
