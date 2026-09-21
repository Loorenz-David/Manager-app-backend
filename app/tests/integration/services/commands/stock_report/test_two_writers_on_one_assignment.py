"""Plan 10 — C5(a): the two-writer race between Scanner (the processed webhook)
and the task-side sync (master plan §6 preamble; intention §5A MC-11 "Scanner
first"; §9 rule 9).

The order is forced by a third **referee** session holding the row's `FOR UPDATE`
lock (never a barrier — a barrier expresses a race, not an order). Both
participants run whole production commands that take and release their own locks
inside `maybe_begin`, so neither can be made to hold one open for the other; the
referee is what makes "session 1 first" true rather than "session 1 usually first".
Precedent: `test_apply_stock_demand.py:test_c5c_concurrent_soft_delete_under_lock_raises_and_heals`.

C5(b) (the mirror order, session 2 first) and C5(c) (Scanner first while
`in_progress`) are not built in this round — named plainly in the implementer
handoff for the tester, which owns the rest of plan 10's criteria table.
"""

import asyncio
import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from sqlalchemy import delete

from beyo_manager.config import settings
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.domain.stock_report.enums import StockTaskAssignmentStateEnum as S
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.history.history_record import HistoryRecord
from beyo_manager.models.tables.history.history_record_link import HistoryRecordLink
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.stock_report._move_assignment import (
    move_assignment,
)
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from beyo_manager.services.commands.stock_report.process_items_processed import (
    process_items_processed,
)
from beyo_manager.services.commands.tasks.fail_task import fail_task
from beyo_manager.services.context import ServiceContext
from tests.helpers.stock_report import (
    assert_stock_report_clean,
    make_ctx,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

API_KEY = "test-two-writers-key"
NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)


async def _make_row(db_session, seeded, *, criteria=None, quantity_requested=10):
    criteria = criteria if criteria is not None else {"wood_group": ["teak"]}
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties=criteria,
        properties_signature=compute_stock_criteria_signature(criteria),
        quantity_requested=quantity_requested,
    )
    db_session.add(row)
    await db_session.flush()
    return row


async def _make_goal(db_session, seeded, row, *, quantity_requested=None):
    from beyo_manager.domain.stock_report.enums import StockReportHistoryRecordTypeEnum

    record = StockReportHistoryRecord(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        type=StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
        quantity_requested=quantity_requested
        if quantity_requested is not None
        else row.quantity_requested,
        quantity_awaiting=0,
        created_at=NOW,
    )
    db_session.add(record)
    await db_session.flush()
    return record


async def _fresh_assignment(session, client_id):
    return (
        await session.execute(
            select(StockTaskAssignment)
            .where(StockTaskAssignment.client_id == client_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


def _pr_ctx(session, *, numbers):
    body = json.dumps([{"article_number": n} for n in numbers]).encode("utf-8")
    return ServiceContext(
        identity={},
        incoming_data={"raw_body": body, "headers": {"x-api-key": API_KEY}},
        session=session,
        now=NOW,
    )


async def test_c5a_scanner_first_task_sync_second_skips_the_resolved_assignment(
    db_session, monkeypatch
):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row, quantity_requested=8)

    ctx = make_ctx(
        db_session,
        seeded,
        role_name="worker",
        incoming_data={
            "entries": [
                {
                    "stock_report_item_id": row.client_id,
                    "task_id": seeded.task.client_id,
                    "item_id": seeded.item.client_id,
                    "override_property_mismatch": False,
                }
            ]
        },
    )
    result = await create_stock_task_assignments(ctx)
    assignment_id = result["stock_task_assignments"][0]["client_id"]
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.AWAITING,
        workspace_id=seeded.workspace.client_id, actor_user_id=seeded.manager.client_id,
        now=NOW, trigger="test",
    )
    await db_session.commit()

    monkeypatch.setattr(settings, "manager_api_key_to_location_tracker_app", API_KEY)
    monkeypatch.setattr(settings, "location_tracker_webhook_workspace_id", seeded.workspace.client_id)

    workspace_id = seeded.workspace.client_id
    row_id = row.client_id
    held = asyncio.Event()
    release = asyncio.Event()

    async def _referee():
        async for session in get_db_session():
            await session.execute(
                select(StockReportItem).where(StockReportItem.client_id == row_id).with_for_update()
            )
            held.set()
            await asyncio.wait_for(release.wait(), timeout=5)
            await session.commit()
            return
        raise AssertionError("referee session generator yielded no session")

    async def _session1_scanner():
        return await process_items_processed(_pr_ctx(db_session, numbers=[seeded.item.article_number]))

    async def _session2_task_sync():
        async for session2 in get_db_session():
            ctx2 = ServiceContext(
                identity={
                    "workspace_id": seeded.workspace.client_id,
                    "user_id": seeded.manager.client_id,
                    "role_name": "manager",
                },
                incoming_data={"client_id": seeded.task.client_id},
                session=session2,
            )
            await fail_task(ctx2)
            await session2.commit()
            return
        raise AssertionError("session2 generator yielded no session")

    referee_task = asyncio.create_task(_referee())
    await asyncio.wait_for(held.wait(), timeout=5)

    try:
        session1_task = asyncio.create_task(_session1_scanner())
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(session1_task), timeout=0.5)

        session2_task = asyncio.create_task(_session2_task_sync())
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(session2_task), timeout=0.5)

        release.set()
        await asyncio.wait_for(referee_task, timeout=5)

        session1_result = await asyncio.wait_for(session1_task, timeout=10)
        await asyncio.wait_for(session2_task, timeout=10)

        assert session1_result["results"] == [
            {"article_number": seeded.item.article_number, "outcome": "resolved", "reason": None}
        ]

        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.RESOLVED
        row_after = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.client_id == row_id)
            )
        ).scalar_one()
        assert (
            row_after.quantity_in_queue,
            row_after.quantity_in_progress,
            row_after.quantity_awaiting,
        ) == (0, 0, 0)
        assert (
            await db_session.execute(
                select(StockReportHistoryRecord.quantity_awaiting).where(
                    StockReportHistoryRecord.client_id == goal.client_id
                )
            )
        ).scalar_one() == 4  # kept: resolved work stays counted (MC-5)

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        history_record_ids = (
            await db_session.execute(
                select(HistoryRecord.client_id).where(
                    HistoryRecord.created_by_id.in_(
                        [seeded.manager.client_id, seeded.worker.client_id]
                    )
                )
            )
        ).scalars().all()
        if history_record_ids:
            await db_session.execute(
                delete(HistoryRecordLink).where(
                    HistoryRecordLink.history_record_id.in_(history_record_ids)
                )
            )
            await db_session.execute(
                delete(HistoryRecord).where(HistoryRecord.client_id.in_(history_record_ids))
            )
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()
