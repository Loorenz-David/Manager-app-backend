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
from beyo_manager.domain.stock_report.enums import ACTIVE_ASSIGNMENT_STATES
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

    scanner_events: list = []

    async def _capture_scanner(events):
        scanner_events.extend(events)

    monkeypatch.setattr(
        "beyo_manager.services.commands.stock_report.process_items_processed.dispatch",
        _capture_scanner,
    )
    sync_events: list = []

    async def _capture_task_side(events):
        sync_events.extend(events)

    monkeypatch.setattr(
        "beyo_manager.services.commands.tasks.fail_task.event_bus.dispatch",
        _capture_task_side,
    )

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
        ).scalar_one() == 1  # kept: resolved work stays counted (MC-5)
        assert assignment.credited_history_record_id == goal.client_id  # mem == G

        # Session 1 (Scanner, first) emits the transition and the row update.
        assert [event.event_name for event in scanner_events] == [
            "stock_task_assignment:state-changed",
            "stock_report_item:updated",
        ]
        assert scanner_events[0].extra["state"] == "resolved"
        # Session 2 (the task sync, second) finds the assignment already terminal
        # under its own lock and emits NOTHING on the stock side.
        assert [
            event for event in sync_events if event.event_name.startswith("stock_")
        ] == []

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


# ---------------------------------------------------------------------------
# Shared kit for C5(b) and C5(c): the §6 referee-lock choreography, a task step,
# and the workspace teardown these rows' commands need.
# ---------------------------------------------------------------------------


async def _section_and_step(db_session, seeded, name, *, step_state):
    from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
    from beyo_manager.models.tables.tasks.task_step import TaskStep
    from beyo_manager.models.tables.working_sections.working_section import WorkingSection

    section = WorkingSection(
        workspace_id=seeded.workspace.client_id,
        name=name,
        allows_batch_working=False,
        created_by_id=seeded.manager.client_id,
    )
    db_session.add(section)
    await db_session.flush()
    step = TaskStep(
        workspace_id=seeded.workspace.client_id,
        task_id=seeded.task.client_id,
        working_section_id=section.client_id,
        working_section_name_snapshot=section.name,
        allows_batch_working=False,
        state=step_state,
        readiness_status="ready",
        total_dependencies=0,
        completed_dependencies=0,
        sequence_order=1,
        created_by_id=seeded.manager.client_id,
    )
    db_session.add(step)
    await db_session.flush()
    record = StepStateRecord(
        workspace_id=seeded.workspace.client_id,
        step_id=step.client_id,
        state=step_state,
        entered_at=NOW,
        exited_at=None,
        created_by_id=seeded.manager.client_id,
    )
    db_session.add(record)
    await db_session.flush()
    step.latest_state_record_id = record.client_id
    await db_session.flush()
    return section, step


async def _set_task_state(db_session, task, state):
    from beyo_manager.models.tables.tasks.task import Task

    await db_session.execute(
        Task.__table__.update().where(Task.client_id == task.client_id).values(state=state)
    )
    task.state = state
    await db_session.flush()


async def _purge_everything(db_session, workspace_id, user_ids):
    from sqlalchemy import delete as _delete

    from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
    from beyo_manager.models.tables.tasks.task_step import TaskStep
    from beyo_manager.models.tables.working_sections.working_section import WorkingSection

    history_record_ids = (
        await db_session.execute(
            select(HistoryRecord.client_id).where(
                HistoryRecord.created_by_id.in_(user_ids)
            )
        )
    ).scalars().all()
    if history_record_ids:
        await db_session.execute(
            _delete(HistoryRecordLink).where(
                HistoryRecordLink.history_record_id.in_(history_record_ids)
            )
        )
        await db_session.execute(
            _delete(HistoryRecord).where(HistoryRecord.client_id.in_(history_record_ids))
        )
    await db_session.execute(
        TaskStep.__table__.update()
        .where(TaskStep.workspace_id == workspace_id)
        .values(latest_state_record_id=None)
    )
    await db_session.execute(
        _delete(StepStateRecord).where(StepStateRecord.workspace_id == workspace_id)
    )
    await db_session.execute(_delete(TaskStep).where(TaskStep.workspace_id == workspace_id))
    await db_session.execute(
        _delete(WorkingSection).where(WorkingSection.workspace_id == workspace_id)
    )
    await purge_stock_report_workspace(db_session, workspace_id)
    await db_session.commit()


async def _run_referee_ordered(row_id, first, second):
    """The §6 preamble's choreography, verbatim: a third **referee** session takes
    `SELECT ... FOR UPDATE` on R and holds it; `first` is started and **observed to
    block**; only then is `second` started and likewise observed to block; the
    referee commits and both are awaited. Postgres queues the two waiters on the
    row's tuple lock in arrival order, so `first` acquires first. Both observed
    blocks are assertions of the row, not setup: they prove the order was forced
    *and* that each session finished its unlocked discovery read before the other
    committed. A barrier is deliberately NOT used — it releases both sides at once
    and expresses a race, not an order."""
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

    referee_task = asyncio.create_task(_referee())
    await asyncio.wait_for(held.wait(), timeout=5)

    first_task = asyncio.create_task(first())
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(asyncio.shield(first_task), timeout=0.5)

    second_task = asyncio.create_task(second())
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(asyncio.shield(second_task), timeout=0.5)

    release.set()
    await asyncio.wait_for(referee_task, timeout=5)
    first_result = await asyncio.wait_for(first_task, timeout=10)
    second_result = await asyncio.wait_for(second_task, timeout=10)
    return first_result, second_result


async def test_c5b_task_reopen_first_then_scanner_resolves_early(db_session, monkeypatch):
    """C5(b) / §14F F6 (replaces MC-11 row 2): the **mirror** order — the S7 reopen
    acquires R first and drags the `awaiting` assignment back to `in_progress`
    (returning its goal credit); Scanner, second, then decides on the state the
    reopen left and resolves it **early**, re-crediting the current goal."""
    from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
    from beyo_manager.domain.tasks.enums import TaskStateEnum
    from beyo_manager.models.tables.tasks.task import Task
    from beyo_manager.services.commands.task_steps.add_task_steps import add_task_steps

    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row)
    section, _step = await _section_and_step(
        db_session, seeded, "C5b section", step_state=TaskStepStateEnum.COMPLETED
    )

    ctx = make_ctx(
        db_session, seeded, role_name="worker",
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
    await _set_task_state(db_session, seeded.task, TaskStateEnum.READY)
    await db_session.commit()

    monkeypatch.setattr(settings, "manager_api_key_to_location_tracker_app", API_KEY)
    monkeypatch.setattr(
        settings, "location_tracker_webhook_workspace_id", seeded.workspace.client_id
    )

    workspace_id = seeded.workspace.client_id
    user_ids = [seeded.manager.client_id, seeded.worker.client_id]
    row_id = row.client_id
    goal_id = goal.client_id
    task_id = seeded.task.client_id
    article_number = seeded.item.article_number
    section_id = section.client_id

    scanner_events: list = []
    reopen_events: list = []

    async def _capture_scanner(events):
        scanner_events.extend(events)

    async def _capture_reopen(events):
        reopen_events.extend(events)

    monkeypatch.setattr(
        "beyo_manager.services.commands.stock_report.process_items_processed.dispatch",
        _capture_scanner,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_steps.add_task_steps.event_bus.dispatch",
        _capture_reopen,
    )

    async def _session2_reopen():
        async for session2 in get_db_session():
            ctx2 = ServiceContext(
                identity={
                    "workspace_id": workspace_id,
                    "user_id": user_ids[0],
                    "role_name": "manager",
                },
                incoming_data={
                    "task_id": task_id,
                    "steps": [{"working_section_id": section_id}],
                },
                session=session2,
            )
            await add_task_steps(ctx2)
            await session2.commit()
            return
        raise AssertionError("session2 generator yielded no session")

    async def _session1_scanner():
        return await process_items_processed(_pr_ctx(db_session, numbers=[article_number]))

    try:
        # session 2 FIRST — the mirror of C5(a).
        _reopen_result, scanner_result = await _run_referee_ordered(
            row_id, _session2_reopen, _session1_scanner
        )

        assert scanner_result["results"] == [
            {"article_number": article_number, "outcome": "resolved", "reason": "early"}
        ]
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.RESOLVED_EARLY
        row_after = (
            await db_session.execute(
                select(StockReportItem)
                .where(StockReportItem.client_id == row_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        assert (
            row_after.quantity_in_queue,
            row_after.quantity_in_progress,
            row_after.quantity_awaiting,
        ) == (0, 0, 0)
        # The reopen returned the first credit (G -> 0); entering `resolved_early`
        # credited the current goal again (§14F F4).
        assert (
            await db_session.execute(
                select(StockReportHistoryRecord.quantity_awaiting).where(
                    StockReportHistoryRecord.client_id == goal_id
                )
            )
        ).scalar_one() == 1
        assert assignment.credited_history_record_id == goal_id

        reopen_stock = [
            event for event in reopen_events if event.event_name.startswith("stock_")
        ]
        assert [event.event_name for event in reopen_stock] == [
            "stock_task_assignment:state-changed",
            "stock_report_item:updated",
        ]
        assert reopen_stock[0].extra["state"] == "in_progress"
        assert reopen_stock[1].extra["quantity_in_progress"] == 1
        assert [event.event_name for event in scanner_events] == [
            "stock_task_assignment:state-changed",
            "stock_report_item:updated",
        ]
        assert scanner_events[0].extra["state"] == "resolved_early"
        assert scanner_events[1].extra["quantity_in_progress"] == 0

        task_after = (
            await db_session.execute(
                select(Task)
                .where(Task.client_id == task_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        assert task_after.state == TaskStateEnum.WORKING

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _purge_everything(db_session, workspace_id, user_ids)


async def test_c5c_scanner_first_while_in_progress_then_the_task_goes_ready(
    db_session, monkeypatch
):
    """C5(c) / §14F F6's third order: Scanner resolves an `in_progress` assignment
    **early** while the task is still working; the step completion that follows takes
    T to `ready` and its sync finds the assignment terminal under its own lock, so it
    emits nothing. Both orders end with no assignment in an active state and counters
    equal to the recomputation."""
    from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
    from beyo_manager.domain.tasks.enums import TaskStateEnum
    from beyo_manager.models.tables.tasks.task import Task
    from beyo_manager.services.commands.task_steps.transition_step_state import (
        transition_step_state,
    )

    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row)
    _section, step = await _section_and_step(
        db_session, seeded, "C5c section", step_state=TaskStepStateEnum.WORKING
    )

    ctx = make_ctx(
        db_session, seeded, role_name="worker",
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
        db_session, assignment, S.IN_PROGRESS,
        workspace_id=seeded.workspace.client_id, actor_user_id=seeded.manager.client_id,
        now=NOW, trigger="test",
    )
    await _set_task_state(db_session, seeded.task, TaskStateEnum.WORKING)
    await db_session.commit()

    monkeypatch.setattr(settings, "manager_api_key_to_location_tracker_app", API_KEY)
    monkeypatch.setattr(
        settings, "location_tracker_webhook_workspace_id", seeded.workspace.client_id
    )

    workspace_id = seeded.workspace.client_id
    user_ids = [seeded.manager.client_id, seeded.worker.client_id]
    row_id = row.client_id
    goal_id = goal.client_id
    task_id = seeded.task.client_id
    step_id = step.client_id
    article_number = seeded.item.article_number

    scanner_events: list = []
    step_events: list = []

    async def _capture_scanner(events):
        scanner_events.extend(events)

    async def _capture_step(events):
        step_events.extend(events)

    monkeypatch.setattr(
        "beyo_manager.services.commands.stock_report.process_items_processed.dispatch",
        _capture_scanner,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_steps.transition_step_state.event_bus.dispatch",
        _capture_step,
    )

    async def _session1_scanner():
        return await process_items_processed(_pr_ctx(db_session, numbers=[article_number]))

    async def _session2_complete_the_last_step():
        async for session2 in get_db_session():
            ctx2 = ServiceContext(
                identity={
                    "workspace_id": workspace_id,
                    "user_id": user_ids[0],
                    "role_name": "worker",
                },
                incoming_data={
                    "step_id": step_id,
                    "task_id": task_id,
                    "new_state": "completed",
                },
                session=session2,
            )
            await transition_step_state(ctx2)
            await session2.commit()
            return
        raise AssertionError("session2 generator yielded no session")

    try:
        scanner_result, _step_result = await _run_referee_ordered(
            row_id, _session1_scanner, _session2_complete_the_last_step
        )

        assert scanner_result["results"] == [
            {"article_number": article_number, "outcome": "resolved", "reason": "early"}
        ]
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.RESOLVED_EARLY
        row_after = (
            await db_session.execute(
                select(StockReportItem)
                .where(StockReportItem.client_id == row_id)
                .execution_options(populate_existing=True)
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
                    StockReportHistoryRecord.client_id == goal_id
                )
            )
        ).scalar_one() == 1
        assert assignment.credited_history_record_id == goal_id

        assert [event.event_name for event in scanner_events] == [
            "stock_task_assignment:state-changed",
            "stock_report_item:updated",
        ]
        assert scanner_events[0].extra["state"] == "resolved_early"
        assert [
            event for event in step_events if event.event_name.startswith("stock_")
        ] == []

        task_after = (
            await db_session.execute(
                select(Task)
                .where(Task.client_id == task_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        assert task_after.state == TaskStateEnum.READY

        # No assignment of this workspace is in an active state (§14F F6).
        active = (
            await db_session.execute(
                select(StockTaskAssignment).where(
                    StockTaskAssignment.workspace_id == workspace_id,
                    StockTaskAssignment.is_deleted.is_(False),
                    StockTaskAssignment.state.in_(ACTIVE_ASSIGNMENT_STATES),
                )
            )
        ).scalars().all()
        assert active == []

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await _purge_everything(db_session, workspace_id, user_ids)
