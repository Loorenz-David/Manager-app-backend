"""Plan 9 — `process_items_processed` (master plan §6.5; intention §8B MC-8/MC-9/
MC-10, §14F F1-F8).

F0 (master plan §6.8): workspace W, manager U, category K, item I (`quantity 4`,
`properties {"wood_type": "Teak", "upholstery": "Down"}`), task T (`pending`,
PRIMARY = I), row R (identity K + `{"wood_group": ["teak"]}`). `CR(entries)` creates
assignments through the real command (plan 8 §6: assignments in fixtures come from
the command); `PR(numbers, headers=...)` = `process_items_processed` called
directly with a raw JSON body, exactly as the router builds `ctx`.

This file builds the behaviour and exercises one representative row per distinct
code path; it is not a row-by-row transcription of plan 9's criteria table (that
discipline and the mutation ledger belong to the tester — see the phase's Review
log and the implementer handoff for the rows this file does not exercise).
"""

import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from beyo_manager.config import settings
from beyo_manager.domain.items.enums import ItemStateEnum
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.domain.stock_report.enums import (
    StockReportHistoryRecordTypeEnum,
    StockTaskAssignmentStateEnum as S,
)
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.errors.stock_report import LocationTrackerWebhookAuthError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_repair_record import (
    StockReportRepairRecord,
)
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.stock_report._move_assignment import (
    move_assignment,
    resolve_processed_group,
)
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from beyo_manager.services.commands.stock_report.process_items_processed import (
    process_items_processed,
)
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

API_KEY = "test-processed-key"
NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)

WRITE_TABLES = {
    "stock_report_items",
    "stock_task_assignments",
    "stock_report_history_records",
    "tasks",
}


def _configure(monkeypatch, *, api_key=API_KEY, workspace_id):
    monkeypatch.setattr(settings, "manager_api_key_to_location_tracker_app", api_key)
    monkeypatch.setattr(settings, "location_tracker_webhook_workspace_id", workspace_id)


def _body(numbers) -> bytes:
    return json.dumps([{"article_number": n} for n in numbers]).encode("utf-8")


def _ctx(session, *, raw_body=b"[]", headers=None):
    headers = {"x-api-key": API_KEY} if headers is None else headers
    return ServiceContext(
        identity={},
        incoming_data={"raw_body": raw_body, "headers": headers},
        session=session,
        now=NOW,
    )


async def _PR(session, numbers, *, headers=None):
    return await process_items_processed(
        _ctx(session, raw_body=_body(numbers), headers=headers)
    )


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


async def _CR(db_session, seeded, row, task, item):
    ctx = make_ctx(
        db_session,
        seeded,
        role_name="worker",
        incoming_data={
            "entries": [
                {
                    "stock_report_item_id": row.client_id,
                    "task_id": task.client_id,
                    "item_id": item.client_id,
                    "override_property_mismatch": False,
                }
            ]
        },
    )
    result = await create_stock_task_assignments(ctx)
    return result["stock_task_assignments"][0]["client_id"]


async def _fresh_assignment(db_session, client_id):
    return (
        await db_session.execute(
            select(StockTaskAssignment)
            .where(StockTaskAssignment.client_id == client_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


async def _create_at(db_session, seeded, row, task, item, target_states):
    """Create A through `CR` (state `in_queue`, T `pending`) then walk it to the
    given target with phase 4's `move_assignment` (plan 9's own webhook exists but
    only produces terminal states)."""
    assignment_id = await _CR(db_session, seeded, row, task, item)
    for state in target_states:
        assignment = await _fresh_assignment(db_session, assignment_id)
        await move_assignment(
            db_session,
            assignment,
            state,
            workspace_id=seeded.workspace.client_id,
            actor_user_id=seeded.manager.client_id,
            now=NOW,
            trigger="test",
        )
    return assignment_id


async def _make_goal(db_session, seeded, row, *, quantity_requested=None, created_at=NOW):
    record = StockReportHistoryRecord(
        workspace_id=seeded.workspace.client_id,
        stock_report_item_id=row.client_id,
        type=StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
        quantity_requested=quantity_requested
        if quantity_requested is not None
        else row.quantity_requested,
        quantity_awaiting=0,
        created_at=created_at,
    )
    db_session.add(record)
    await db_session.flush()
    return record


async def _counters(db_session, row_id):
    return (
        await db_session.execute(
            select(
                StockReportItem.quantity_in_queue,
                StockReportItem.quantity_in_progress,
                StockReportItem.quantity_awaiting,
            ).where(StockReportItem.client_id == row_id)
        )
    ).one()


async def _goal_awaiting(db_session, goal_id):
    return await db_session.scalar(
        select(StockReportHistoryRecord.quantity_awaiting).where(
            StockReportHistoryRecord.client_id == goal_id
        )
    )


# ---------------------------------------------------------------------------
# C1 — auth order (shared verifier, already proven in phase 7; a smoke test here
# confirms this command actually calls it before any write)
# ---------------------------------------------------------------------------


async def test_c1a_no_key_is_401_and_writes_nothing(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, api_key=None, workspace_id=workspace_id)
        async with record_statements(db_session) as statements:
            with pytest.raises(LocationTrackerWebhookAuthError) as excinfo:
                await _PR(db_session, ["SR-x"])
        assert excinfo.value.http_status == 401
        assert count_writes(statements, WRITE_TABLES) == 0
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c1e_blank_workspace_setting_is_401_zero_statements(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id="   ")
        async with record_statements(db_session) as statements:
            with pytest.raises(LocationTrackerWebhookAuthError):
                await _PR(db_session, ["SR-x"])
        assert len(statements) == 0
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c1c_workspace_setting_names_no_workspace_is_401(db_session, monkeypatch):
    _configure(monkeypatch, workspace_id="ws_items_processed_does_not_exist")
    with pytest.raises(LocationTrackerWebhookAuthError):
        await _PR(db_session, ["SR-x"])


# ---------------------------------------------------------------------------
# C3 — resolution / no-match rows
# ---------------------------------------------------------------------------


async def test_c3a_unmatched_number_is_ignored_item_not_found(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        response = await _PR(db_session, ["does-not-exist"])
        assert response["results"] == [
            {"article_number": "does-not-exist", "outcome": "ignored", "reason": "item_not_found"}
        ]
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c3b_item_never_assigned_is_ignored_no_open_assignment(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        response = await _PR(db_session, [seeded.item.article_number])
        assert response["results"] == [
            {
                "article_number": seeded.item.article_number,
                "outcome": "ignored",
                "reason": "no_open_assignment",
            }
        ]
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c3c_terminal_only_assignment_is_ignored_no_open_assignment(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _create_at(db_session, seeded, row, seeded.task, seeded.item, [S.FAILED])
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        response = await _PR(db_session, [seeded.item.article_number])
        assert response["results"][0]["reason"] == "no_open_assignment"
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c3g_outer_whitespace_matches_and_echoes_untouched(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _create_at(db_session, seeded, row, seeded.task, seeded.item, [S.AWAITING])
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        padded = f" {seeded.item.article_number} "
        response = await _PR(db_session, [padded])
        assert response["results"] == [
            {"article_number": padded, "outcome": "resolved", "reason": None}
        ]
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c3i_case_sensitive_no_match(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _create_at(db_session, seeded, row, seeded.task, seeded.item, [S.AWAITING])
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        response = await _PR(db_session, [seeded.item.article_number.lower()])
        assert response["results"][0]["reason"] == "item_not_found"
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c3k_foreign_workspace_item_is_item_not_found(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    foreign = await seed_stock_report_workspace(db_session, suffix="foreign9c3k")
    frow = await _make_row(db_session, foreign)
    await _create_at(db_session, foreign, frow, foreign.task, foreign.item, [S.AWAITING])
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        response = await _PR(db_session, [foreign.item.article_number])
        assert response["results"][0]["reason"] == "item_not_found"
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await purge_stock_report_workspace(db_session, foreign.workspace.client_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C4 — the full resolve, both exits (awaiting -> resolved; in_queue -> resolved_early)
# ---------------------------------------------------------------------------


async def test_c4_awaiting_resolves_credit_kept_task_untouched(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row, quantity_requested=8)
    await db_session.flush()
    assignment_id = await _create_at(
        db_session, seeded, row, seeded.task, seeded.item, [S.AWAITING]
    )
    # Credit memory: awaiting entry credited G in _create_at's own move_assignment.
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        captured = capture_dispatch(
            monkeypatch,
            "beyo_manager.services.commands.stock_report.process_items_processed.dispatch",
        )
        task_state_before = seeded.task.state  # T is pending and untouched by _create_at

        response = await _PR(db_session, [seeded.item.article_number])

        assert response["results"] == [
            {"article_number": seeded.item.article_number, "outcome": "resolved", "reason": None}
        ]
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.RESOLVED
        assert assignment.updated_by_id is None
        assert assignment.updated_at == NOW
        assert await _counters(db_session, row.client_id) == (0, 0, 0)
        # I's quantity is F0's default (4), so the awaiting entry credited G by 4
        # (not `goal.quantity_requested`, 8) — MC-5's credit is `G.quantity_awaiting
        # += q`, and Scanner's resolve from awaiting keeps it unchanged (no-op).
        assert await _goal_awaiting(db_session, goal.client_id) == 4
        assert assignment.credited_history_record_id == goal.client_id

        task_after = (
            await db_session.execute(select(Task).where(Task.client_id == seeded.task.client_id))
        ).scalar_one()
        assert task_after.state == task_state_before
        assert task_after.is_stock_assignment is True

        event_names = {event.event_name for event in captured}
        assert event_names == {"stock_task_assignment:state-changed", "stock_report_item:updated"}

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c4_in_queue_resolves_early_and_credits_goal(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row)
    await db_session.flush()
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)

        response = await _PR(db_session, [seeded.item.article_number])

        assert response["results"] == [
            {"article_number": seeded.item.article_number, "outcome": "resolved", "reason": "early"}
        ]
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.RESOLVED_EARLY
        assert await _counters(db_session, row.client_id) == (0, 0, 0)
        assert await _goal_awaiting(db_session, goal.client_id) == assignment.quantity
        assert assignment.credited_history_record_id == goal.client_id

        task_after = (
            await db_session.execute(select(Task).where(Task.client_id == seeded.task.client_id))
        ).scalar_one()
        assert task_after.state == seeded.task.state  # untouched

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c4f_no_goal_record_nothing_credited(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        response = await _PR(db_session, [seeded.item.article_number])
        assert response["results"][0]["outcome"] == "resolved"
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.RESOLVED_EARLY
        assert assignment.credited_history_record_id is None

        history_rows = (
            await db_session.execute(
                select(StockReportHistoryRecord).where(
                    StockReportHistoryRecord.stock_report_item_id == row.client_id
                )
            )
        ).scalars().all()
        assert history_rows == []

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C5 — a duplicate number within one request decides on the earlier one's effect
# ---------------------------------------------------------------------------


async def test_c5a_duplicate_in_one_request_awaiting(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _create_at(db_session, seeded, row, seeded.task, seeded.item, [S.AWAITING])
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        response = await _PR(
            db_session, [seeded.item.article_number, seeded.item.article_number]
        )
        assert response["results"] == [
            {"article_number": seeded.item.article_number, "outcome": "resolved", "reason": None},
            {
                "article_number": seeded.item.article_number,
                "outcome": "ignored",
                "reason": "no_open_assignment",
            },
        ]
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c5b_duplicate_in_one_request_in_queue_applies_delta_once(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        response = await _PR(
            db_session, [seeded.item.article_number, seeded.item.article_number]
        )
        assert response["results"] == [
            {"article_number": seeded.item.article_number, "outcome": "resolved", "reason": "early"},
            {
                "article_number": seeded.item.article_number,
                "outcome": "ignored",
                "reason": "no_open_assignment",
            },
        ]
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.RESOLVED_EARLY
        assert await _counters(db_session, row.client_id) == (0, 0, 0)

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C6 — replay (MC-9)
# ---------------------------------------------------------------------------


async def test_c6a_replay_awaiting_resolve_is_zero_statements(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _create_at(db_session, seeded, row, seeded.task, seeded.item, [S.AWAITING])
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        first = await _PR(db_session, [seeded.item.article_number])
        assert first["results"][0]["outcome"] == "resolved"

        captured = capture_dispatch(
            monkeypatch,
            "beyo_manager.services.commands.stock_report.process_items_processed.dispatch",
        )
        async with record_statements(db_session) as statements:
            second = await _PR(db_session, [seeded.item.article_number])
        assert second["results"][0] == {
            "article_number": seeded.item.article_number,
            "outcome": "ignored",
            "reason": "no_open_assignment",
        }
        assert count_writes(statements, WRITE_TABLES) == 0
        assert captured == []

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c6b_replay_after_early_resolve_goal_unchanged(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row)
    await db_session.flush()
    await _CR(db_session, seeded, row, seeded.task, seeded.item)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        first = await _PR(db_session, [seeded.item.article_number])
        assert first["results"][0]["reason"] == "early"
        g_after_first = await _goal_awaiting(db_session, goal.client_id)
        await db_session.commit()

        async with record_statements(db_session) as statements:
            second = await _PR(db_session, [seeded.item.article_number])
        assert second["results"][0]["outcome"] == "ignored"
        assert count_writes(statements, WRITE_TABLES) == 0
        assert await _goal_awaiting(db_session, goal.client_id) == g_after_first

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C7 — grouped, per-row summed delta over several assignments
# ---------------------------------------------------------------------------


async def test_c7a_three_awaiting_assignments_on_one_row_sum_and_one_updated_event(
    db_session, monkeypatch
):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    tasks_items = []
    for i, quantity in enumerate((1, 2, 3)):
        task, item = await _second_pair(db_session, seeded, f"c7a{i}", quantity=quantity)
        tasks_items.append((task, item))
        await _create_at(db_session, seeded, row, task, item, [S.AWAITING])
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        captured = capture_dispatch(
            monkeypatch,
            "beyo_manager.services.commands.stock_report.process_items_processed.dispatch",
        )
        numbers = [item.article_number for _task, item in tasks_items]

        response = await _PR(db_session, numbers)

        assert all(result["outcome"] == "resolved" for result in response["results"])
        row_after = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.client_id == row.client_id)
            )
        ).scalar_one()
        assert row_after.quantity_awaiting == 0
        updated_events = [
            event
            for event in captured
            if event.event_name == "stock_report_item:updated" and event.client_id == row.client_id
        ]
        assert len(updated_events) == 1

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def _second_pair(db_session, seeded, suffix, *, quantity=4):
    next_scalar_id = (
        await db_session.scalar(
            select(func.max(Task.task_scalar_id)).where(
                Task.workspace_id == seeded.workspace.client_id
            )
        )
        or 0
    ) + 1
    task = Task(
        client_id=f"tsk_{suffix}_{seeded.workspace.client_id}",
        workspace_id=seeded.workspace.client_id,
        task_scalar_id=next_scalar_id,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=seeded.manager.client_id,
    )
    item = Item(
        client_id=f"itm_{suffix}_{seeded.workspace.client_id}",
        workspace_id=seeded.workspace.client_id,
        article_number=f"{suffix}-{seeded.workspace.client_id}",
        state=ItemStateEnum.PENDING,
        quantity=quantity,
        item_category_id=seeded.categories[0].client_id,
        properties={"wood_type": "Teak", "upholstery": "Down"},
    )
    db_session.add_all([task, item])
    await db_session.flush()
    db_session.add(
        TaskItem(
            client_id=f"tim_{suffix}_{seeded.workspace.client_id}",
            workspace_id=seeded.workspace.client_id,
            task_id=task.client_id,
            item_id=item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=seeded.manager.client_id,
        )
    )
    await db_session.flush()
    return task, item


async def test_c7c_grouped_repair_carries_the_summed_delta(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    tasks_items = []
    for i, quantity in enumerate((1, 2, 3)):
        task, item = await _second_pair(db_session, seeded, f"c7c{i}", quantity=quantity)
        tasks_items.append((task, item))
        await _create_at(db_session, seeded, row, task, item, [S.AWAITING])
    # Plant drift: raw quantity_awaiting = 2 (truth 6).
    await db_session.execute(
        StockReportItem.__table__.update()
        .where(StockReportItem.client_id == row.client_id)
        .values(quantity_awaiting=2)
    )
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        numbers = [item.article_number for _task, item in tasks_items]

        response = await _PR(db_session, numbers)
        assert all(result["outcome"] == "resolved" for result in response["results"])

        row_after = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.client_id == row.client_id)
            )
        ).scalar_one()
        assert row_after.quantity_awaiting == 0

        repairs = (
            await db_session.execute(
                select(StockReportRepairRecord).where(
                    StockReportRepairRecord.workspace_id == workspace_id
                )
            )
        ).scalars().all()
        assert len(repairs) == 1
        assert repairs[0].field == "quantity_awaiting"
        assert repairs[0].stored_value == "2"
        assert repairs[0].recomputed_value == "0"
        assert repairs[0].trigger == "inline:items_processed"

        # The drift-then-repair is this row's own outcome, so no
        # `assert_stock_report_clean` here — `purge_stock_report_workspace` (below)
        # already removes `StockReportRepairRecord` rows for this workspace.
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C8(c) — resolve_processed_group's own contract (rule 18)
# ---------------------------------------------------------------------------


async def test_c8c_resolve_processed_group_contract(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    task2, item2 = await _second_pair(db_session, seeded, "c8c", quantity=2)
    a1_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    a2_id = await _CR(db_session, seeded, row, task2, item2)
    # Plant drift: raw quantity_in_queue = 2, truth 6 (4 + 2) — the combined -6
    # delta would go negative, so the group call must self-heal (MC-1) rather
    # than raise.
    await db_session.execute(
        StockReportItem.__table__.update()
        .where(StockReportItem.client_id == row.client_id)
        .values(quantity_in_queue=2)
    )
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        a1 = await _fresh_assignment(db_session, a1_id)
        a2 = await _fresh_assignment(db_session, a2_id)
        row_obj = (
            await db_session.execute(
                select(StockReportItem)
                .where(StockReportItem.client_id == row.client_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()

        events = await resolve_processed_group(
            db_session,
            [a1, a2],
            row=row_obj,
            workspace_id=workspace_id,
            now=NOW,
            trigger="test_c8c",
        )

        event_names = [event.event_name for event in events]
        assert event_names.count("stock_report_item:updated") == 1
        assert event_names.count("stock_task_assignment:state-changed") == 2
        assert len(events) == 3

        # This row asserts the direct call's contract only (plan 9 C8(c)); the
        # planted drift's own repair record is removed by the purge below.
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()
