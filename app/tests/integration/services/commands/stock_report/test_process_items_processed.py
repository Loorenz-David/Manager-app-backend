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
from beyo_manager.errors.validation import ValidationError
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
from beyo_manager.models.tables.tasks.task_step import TaskStep
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


async def _PR_raw(session, raw_body, *, headers=None):
    """`PR(body_bytes)` of plan 9 §6 — the command with the raw bytes verbatim."""
    return await process_items_processed(
        _ctx(session, raw_body=raw_body, headers=headers)
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


async def _create_walk(db_session, seeded, assignment_id, target_states):
    """Walk an already-created assignment on with phase 4's `move_assignment`."""
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


async def _task_fingerprint(db_session, task_id):
    """Everything §14F F3 says this command never writes on the task side."""
    task = (
        await db_session.execute(
            select(Task)
            .where(Task.client_id == task_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    step_count = await db_session.scalar(
        select(func.count()).select_from(TaskStep).where(TaskStep.task_id == task_id)
    )
    return (
        task.state,
        task.updated_at,
        task.updated_by_id,
        task.is_stock_assignment,
        step_count,
    )


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


async def test_c1b_wrong_key_is_401(db_session, monkeypatch):
    """C1(b): a wrong but non-empty `x-api-key` is refused (401)."""
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        with pytest.raises(LocationTrackerWebhookAuthError) as excinfo:
            await _PR(db_session, ["SR-x"], headers={"x-api-key": "wrong-key"})
        assert excinfo.value.http_status == 401
        assert str(excinfo.value) == "Unauthorized."
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c1d_wrong_key_and_malformed_body_is_401_not_422(db_session, monkeypatch):
    """C1(d): auth is decided before the body is parsed (MC-8 order)."""
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        with pytest.raises(LocationTrackerWebhookAuthError) as excinfo:
            await _PR_raw(db_session, b"{not json", headers={"x-api-key": "wrong-key"})
        assert excinfo.value.http_status == 401
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


@pytest.mark.parametrize(
    "blank_setting",
    ["workspace_id", "api_key"],
    ids=["blank-workspace-setting", "blank-api-key-setting"],
)
async def test_c1e_blank_setting_is_401_zero_statements(
    db_session, monkeypatch, blank_setting
):
    """C1(e): a blank workspace setting (and its API-key twin) is refused **before
    any DB read** — the zero-statement clause, not the 401, is what makes the shared
    verifier's guard observable on this command's path (plan 9 §8, batch B2 CF-3)."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _create_at(
        db_session, seeded, row, seeded.task, seeded.item, [S.AWAITING]
    )
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        headers = None
        if blank_setting == "workspace_id":
            _configure(monkeypatch, workspace_id="   ")
        else:
            # The header carries the *same* blank value as the setting, so the
            # blank-key guard is the ONLY reason this request is refused — a
            # mismatched header would refuse it at `compare_digest` too (rule 2's
            # companion: one sufficient cause per row).
            _configure(monkeypatch, api_key="   ", workspace_id=workspace_id)
            headers = {"x-api-key": "   "}
        captured = capture_dispatch(
            monkeypatch,
            "beyo_manager.services.commands.stock_report.process_items_processed.dispatch",
        )
        async with record_statements(db_session) as statements:
            with pytest.raises(LocationTrackerWebhookAuthError) as excinfo:
                await _PR(db_session, [seeded.item.article_number], headers=headers)
        assert excinfo.value.http_status == 401
        assert str(excinfo.value) == "Unauthorized."
        assert len(statements) == 0
        assert captured == []
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.AWAITING
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c1c_workspace_setting_names_no_workspace_is_401(db_session, monkeypatch):
    _configure(monkeypatch, workspace_id="ws_items_processed_does_not_exist")
    with pytest.raises(LocationTrackerWebhookAuthError):
        await _PR(db_session, ["SR-x"])


# ---------------------------------------------------------------------------
# C2 — the parse contract at the row's own boundary (`PR(body_bytes)`, plan 9 §6).
# The per-shape defect messages are `test_items_processed_request.py`'s; this row
# set's outcome is "422 / 200 through the command, nothing written" — the same
# split the shipped plan-7 precedent ships
# (`test_receive_stock_demand_webhook.py::test_c2a_c2x_...`).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_body",
    [
        pytest.param(b"{}", id="c2a-object-not-array"),
        pytest.param(b"[]", id="c2b-empty-array"),
        pytest.param(b'["0000612"]', id="c2c-entry-not-an-object"),
        pytest.param(b"[{}]", id="c2d-article-number-missing"),
        pytest.param(b'[{"article_number": 612}]', id="c2e-article-number-not-a-string"),
        pytest.param(b'[{"article_number": "  "}]', id="c2f-article-number-blank"),
        pytest.param(
            b'[{"article_number": 1}, {"article_number": "SR-x"}, {"article_number": ""}]',
            id="c2h-two-malformed-entries",
        ),
    ],
)
async def test_c2_malformed_body_is_422_through_the_command_and_writes_nothing(
    db_session, monkeypatch, raw_body
):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _create_at(
        db_session, seeded, row, seeded.task, seeded.item, [S.AWAITING]
    )
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        async with record_statements(db_session) as statements:
            with pytest.raises(ValidationError) as excinfo:
                await _PR_raw(db_session, raw_body)
        assert excinfo.value.http_status == 422
        assert count_writes(statements, WRITE_TABLES) == 0
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.AWAITING
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c2h_the_422_names_every_offending_index(db_session, monkeypatch):
    """C2(h): entries 0 and 2 malformed — the message names **both**, not the first."""
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        with pytest.raises(ValidationError) as excinfo:
            await _PR_raw(
                db_session,
                b'[{"article_number": 1}, {"article_number": "SR-x"}, '
                b'{"article_number": ""}]',
            )
        message = str(excinfo.value)
        assert "entry 0" in message
        assert "entry 2" in message
        assert "entry 1" not in message
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c2g_unknown_entry_key_is_ignored_and_the_request_succeeds(
    db_session, monkeypatch
):
    """C2(g): an unknown key on an otherwise valid entry does not make the body
    malformed — the command returns a result for it (200, not 422)."""
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        response = await _PR_raw(
            db_session,
            json.dumps(
                [{"article_number": seeded.item.article_number, "location": "LC1"}]
            ).encode("utf-8"),
        )
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


@pytest.mark.parametrize(
    "walk",
    [
        pytest.param([S.AWAITING, S.RESOLVED], id="resolved"),
        pytest.param([S.FAILED], id="failed"),
        pytest.param([S.RESOLVED_EARLY], id="resolved-early"),
    ],
)
async def test_c3c_terminal_only_assignment_is_ignored_no_open_assignment(
    db_session, monkeypatch, walk
):
    """C3(c): all three terminal states — `resolved`, `failed` and (round 9)
    `resolved_early` — are "no open assignment". The `resolved_early` sub-case is
    the one a hand-typed `NOT IN (resolved, failed)` terminal list gets wrong
    (§9 rule 16)."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _create_at(db_session, seeded, row, seeded.task, seeded.item, walk)
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


async def test_c3e_in_progress_resolves_early(db_session, monkeypatch):
    """C3(e): an `in_progress` assignment resolves with reason `early` and lands in
    `resolved_early` — it must be *discovered* as active (rule 16's frozenset)."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _create_at(
        db_session, seeded, row, seeded.task, seeded.item, [S.IN_PROGRESS]
    )
    await db_session.execute(
        Task.__table__.update()
        .where(Task.client_id == seeded.task.client_id)
        .values(state=TaskStateEnum.WORKING)
    )
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        response = await _PR(db_session, [seeded.item.article_number])
        assert response["results"] == [
            {
                "article_number": seeded.item.article_number,
                "outcome": "resolved",
                "reason": "early",
            }
        ]
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.RESOLVED_EARLY
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c3h_leading_zeros_are_significant(db_session, monkeypatch):
    """C3(h): `"0000612"` does not match the stored `"000612"`."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    _task, item = await _second_pair(db_session, seeded, "c3h")
    item.article_number = "000612"
    await db_session.flush()
    await _create_at(db_session, seeded, row, _task, item, [S.AWAITING])
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        response = await _PR(db_session, ["0000612"])
        assert response["results"] == [
            {"article_number": "0000612", "outcome": "ignored", "reason": "item_not_found"}
        ]
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c3j_inner_spaces_are_significant(db_session, monkeypatch):
    """C3(j): `"04 2 001 0034"` does not match the stored `"042 001 0034"` — only
    the outer trim of C3(g) is applied, never an inner whitespace fold."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    _task, item = await _second_pair(db_session, seeded, "c3j")
    item.article_number = "042 001 0034"
    await db_session.flush()
    await _create_at(db_session, seeded, row, _task, item, [S.AWAITING])
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        response = await _PR(db_session, ["04 2 001 0034"])
        assert response["results"] == [
            {
                "article_number": "04 2 001 0034",
                "outcome": "ignored",
                "reason": "item_not_found",
            }
        ]
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c3l_the_result_vocabulary_is_closed_across_the_whole_f5_ladder(
    db_session, monkeypatch
):
    """C3(l): over every rung of the §14F F5 ladder in **one** request, `outcome` is
    drawn from `{resolved, ignored}`, `reason` from `{null, item_not_found,
    no_open_assignment, early}`, and `reason` is `null` **exactly** when the entry
    resolved from `awaiting` (v2 §4.3's closed vocabulary)."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)

    # C3(b) — item exists, never assigned.
    _t_never, i_never = await _second_pair(db_session, seeded, "c3lnv")
    # C3(c) — terminal only.
    t_term, i_term = await _second_pair(db_session, seeded, "c3ltm")
    await _create_at(db_session, seeded, row, t_term, i_term, [S.FAILED])
    # C3(d) — in_queue.
    t_queue, i_queue = await _second_pair(db_session, seeded, "c3lqu")
    await _CR(db_session, seeded, row, t_queue, i_queue)
    # C3(e) — in_progress.
    t_prog, i_prog = await _second_pair(db_session, seeded, "c3lpr")
    await _create_at(db_session, seeded, row, t_prog, i_prog, [S.IN_PROGRESS])
    # C3(f) — awaiting.
    t_await, i_await = await _second_pair(db_session, seeded, "c3law")
    await _create_at(db_session, seeded, row, t_await, i_await, [S.AWAITING])
    await db_session.commit()

    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        numbers = [
            "no-such-article",  # C3(a)
            i_never.article_number,  # C3(b)
            i_term.article_number,  # C3(c)
            i_queue.article_number,  # C3(d)
            i_prog.article_number,  # C3(e)
            i_await.article_number,  # C3(f)
        ]
        results = (await _PR(db_session, numbers))["results"]

        assert [result["outcome"] for result in results] == [
            "ignored",
            "ignored",
            "ignored",
            "resolved",
            "resolved",
            "resolved",
        ]
        assert [result["reason"] for result in results] == [
            "item_not_found",
            "no_open_assignment",
            "no_open_assignment",
            "early",
            "early",
            None,
        ]
        # `reason is null` <=> `outcome == "resolved"` from `awaiting`, in both
        # directions, over the whole ladder.
        assert [result["reason"] is None for result in results] == [
            False,
            False,
            False,
            False,
            False,
            True,
        ]
        assert {result["outcome"] for result in results} <= {"resolved", "ignored"}
        assert {result["reason"] for result in results} <= {
            None,
            "item_not_found",
            "no_open_assignment",
            "early",
        }
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
    seeded.item.quantity = 8  # plan 9 §6 preamble: a row stating `q = 8` sets I's quantity
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
        # MC-5 row 3: a resolve **from awaiting** keeps the credit — `G` is the `q`
        # the awaiting entry credited (8), and the memory still points at G.
        assert await _goal_awaiting(db_session, goal.client_id) == 8
        assert assignment.credited_history_record_id == goal.client_id

        # `populate_existing`: a raw Core UPDATE of `tasks` is invisible to the
        # identity-mapped instance, so a plain `select(Task)` cannot observe a
        # task write at all (§9 rule 3's ORM-staleness rule, on the read side).
        task_after = (
            await db_session.execute(
                select(Task)
                .where(Task.client_id == seeded.task.client_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        assert task_after.state == task_state_before
        assert task_after.is_stock_assignment is True  # C4(c)

        # C4(b): the exact dispatched list, in order, with its payloads.
        assert [event.event_name for event in captured] == [
            "stock_task_assignment:state-changed",
            "stock_report_item:updated",
        ]
        assert captured[0].client_id == assignment_id
        assert captured[0].extra["state"] == "resolved"
        assert captured[1].client_id == row.client_id
        assert captured[1].extra["quantity_awaiting"] == 0
        assert captured[1].extra["quantity_in_queue"] == 0
        assert captured[1].extra["quantity_in_progress"] == 0

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


@pytest.mark.parametrize(
    "walk,expected_counter_key,row_letter",
    [
        pytest.param([], "quantity_in_queue", "C4(d)", id="c4d-in-queue"),
        pytest.param([S.IN_PROGRESS], "quantity_in_progress", "C4(e)", id="c4e-in-progress"),
    ],
)
async def test_c4de_active_non_awaiting_resolves_early_credits_goal_task_untouched(
    db_session, monkeypatch, walk, expected_counter_key, row_letter
):
    """C4(d) (`in_queue`) and C4(e) (`in_progress`), `q = 8`: the assignment lands
    `resolved_early`, the goal is credited `+q` (§14F F4), and the **task is never
    written** (F3) — its state, `updated_at`, `updated_by_id` and step count are all
    byte-identical across the request. C4(g) adds the dispatched event list."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row)
    seeded.item.quantity = 8  # plan 9 §6 preamble: `q = 8`
    await db_session.flush()
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    if walk:
        await _create_walk(db_session, seeded, assignment_id, walk)
        await db_session.execute(
            Task.__table__.update()
            .where(Task.client_id == seeded.task.client_id)
            .values(state=TaskStateEnum.WORKING)
        )
    # Taken inside the setup transaction: after the commit below, `ctx.session`
    # must carry no open transaction (X3), so the request itself opens the first.
    task_id = seeded.task.client_id
    task_before = await _task_fingerprint(db_session, task_id)
    article_number = seeded.item.article_number
    goal_id = goal.client_id
    row_id = row.client_id
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        captured = capture_dispatch(
            monkeypatch,
            "beyo_manager.services.commands.stock_report.process_items_processed.dispatch",
        )

        response = await _PR(db_session, [article_number])

        assert response["results"] == [
            {"article_number": article_number, "outcome": "resolved", "reason": "early"}
        ]
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.RESOLVED_EARLY
        assert assignment.updated_by_id is None
        assert assignment.updated_at == NOW
        assert await _counters(db_session, row_id) == (0, 0, 0)
        assert await _goal_awaiting(db_session, goal_id) == 8
        assert assignment.credited_history_record_id == goal_id

        # F3 — the task is never touched by this command.
        assert await _task_fingerprint(db_session, task_id) == task_before

        # C4(g) — the dispatched list, exactly: the assignment's transition and the
        # row's one `:updated`, and **no** task event.
        assert [event.event_name for event in captured] == [
            "stock_task_assignment:state-changed",
            "stock_report_item:updated",
        ]
        assert captured[0].extra["state"] == "resolved_early"
        assert captured[1].extra[expected_counter_key] == 0

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
        async with record_statements(db_session) as statements:
            response = await _PR(db_session, [seeded.item.article_number])
        assert response["results"][0]["outcome"] == "resolved"
        assignment = await _fresh_assignment(db_session, assignment_id)
        assert assignment.state == S.RESOLVED_EARLY
        assert await _counters(db_session, row.client_id) == (0, 0, 0)
        assert assignment.credited_history_record_id is None
        # §14F F4: with no goal record, nothing is credited — and nothing is written
        # to the goal table at all (no record is created to carry the credit).
        assert count_writes(statements, {"stock_report_history_records"}) == 0

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

        captured = capture_dispatch(
            monkeypatch,
            "beyo_manager.services.commands.stock_report.process_items_processed.dispatch",
        )
        async with record_statements(db_session) as statements:
            second = await _PR(db_session, [seeded.item.article_number])
        assert second["results"] == [
            {
                "article_number": seeded.item.article_number,
                "outcome": "ignored",
                "reason": "no_open_assignment",
            }
        ]
        assert count_writes(statements, WRITE_TABLES) == 0
        assert captured == []
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


async def test_c7b_entries_across_two_rows_each_get_exactly_one_updated(
    db_session, monkeypatch
):
    """C7(b) (as re-stated by the owner, 2026-09-21, card 1): a request naming
    assignments on **two** rows leaves each row at its expected counters and emits
    **exactly one** `stock_report_item:updated` per row. No assertion on statement
    counts and none on runtime row ordering (`client_id` is not creation order)."""
    seeded = await seed_stock_report_workspace(db_session)
    row_a = await _make_row(db_session, seeded)
    row_b = await _make_row(db_session, seeded, criteria={"upholstery": ["down"]})
    numbers_by_row = {}
    for row, label in ((row_a, "a"), (row_b, "b")):
        numbers = []
        for index, quantity in enumerate((1, 2)):
            task, item = await _second_pair(
                db_session, seeded, f"c7b{label}{index}", quantity=quantity
            )
            await _create_at(db_session, seeded, row, task, item, [S.AWAITING])
            numbers.append(item.article_number)
        numbers_by_row[row.client_id] = numbers
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        captured = capture_dispatch(
            monkeypatch,
            "beyo_manager.services.commands.stock_report.process_items_processed.dispatch",
        )
        # Interleave the two rows' entries so neither row is "the last group".
        all_numbers = [
            numbers_by_row[row_a.client_id][0],
            numbers_by_row[row_b.client_id][0],
            numbers_by_row[row_a.client_id][1],
            numbers_by_row[row_b.client_id][1],
        ]

        response = await _PR(db_session, all_numbers)

        assert all(result["outcome"] == "resolved" for result in response["results"])
        for row in (row_a, row_b):
            assert await _counters(db_session, row.client_id) == (0, 0, 0)
            updated = [
                event
                for event in captured
                if event.event_name == "stock_report_item:updated"
                and event.client_id == row.client_id
            ]
            assert len(updated) == 1, f"row {row.client_id}: {len(updated)} :updated events"
            assert updated[0].extra["quantity_awaiting"] == 0

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def _mixed_state_row(db_session, seeded, label):
    """C7(d)'s fixture: one row R carrying A1 `awaiting` q=1 (credited), A2
    `in_queue` q=2 and A3 `in_progress` q=3 — counters `(2, 3, 1)`."""
    row = await _make_row(db_session, seeded)
    goal = await _make_goal(db_session, seeded, row)
    await db_session.flush()
    numbers = []
    walks = ([S.AWAITING], [], [S.IN_PROGRESS])
    for index, (quantity, walk) in enumerate(zip((1, 2, 3), walks)):
        task, item = await _second_pair(
            db_session, seeded, f"{label}{index}", quantity=quantity
        )
        await _create_at(db_session, seeded, row, task, item, walk)
        numbers.append(item.article_number)
    return row, goal, numbers


async def test_c7d_mixed_states_on_one_row_apply_every_column_delta(
    db_session, monkeypatch
):
    """C7(d): one grouped write per row carries the per-column sum — `awaiting`,
    `in_queue` **and** `in_progress` all land at 0, the two early exits credit the
    goal, and R emits one `:updated` with all three counters 0."""
    seeded = await seed_stock_report_workspace(db_session)
    row, goal, numbers = await _mixed_state_row(db_session, seeded, "c7d")
    # Inside the setup transaction (X3: the request opens the first one).
    assert await _counters(db_session, row.client_id) == (2, 3, 1)
    row_id, goal_id = row.client_id, goal.client_id
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        captured = capture_dispatch(
            monkeypatch,
            "beyo_manager.services.commands.stock_report.process_items_processed.dispatch",
        )

        response = await _PR(db_session, numbers)

        assert [
            (result["outcome"], result["reason"]) for result in response["results"]
        ] == [("resolved", None), ("resolved", "early"), ("resolved", "early")]
        assert await _counters(db_session, row_id) == (0, 0, 0)
        # A1 was already credited 1 from its `awaiting` entry (kept, MC-5 row 3);
        # A2 (+2) and A3 (+3) credit on entering `resolved_early` (§14F F4).
        assert await _goal_awaiting(db_session, goal_id) == 6

        updated = [
            event
            for event in captured
            if event.event_name == "stock_report_item:updated"
            and event.client_id == row_id
        ]
        assert len(updated) == 1
        assert updated[0].extra["quantity_in_queue"] == 0
        assert updated[0].extra["quantity_in_progress"] == 0
        assert updated[0].extra["quantity_awaiting"] == 0

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c7e_one_repair_record_per_wrong_column_not_per_assignment(
    db_session, monkeypatch
):
    """C7(e): with `quantity_in_queue` and `quantity_in_progress` both drifted (and
    `quantity_awaiting` correct), the grouped repair writes **exactly two** records —
    one per column where `stored + delta != recomputed` — never one per moved
    assignment (MC-1's trace rule, §12A)."""
    seeded = await seed_stock_report_workspace(db_session)
    row, _goal, numbers = await _mixed_state_row(db_session, seeded, "c7e")
    await db_session.execute(
        StockReportItem.__table__.update()
        .where(StockReportItem.client_id == row.client_id)
        .values(quantity_in_queue=0, quantity_in_progress=1)
    )
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)

        response = await _PR(db_session, numbers)
        assert all(result["outcome"] == "resolved" for result in response["results"])
        assert await _counters(db_session, row.client_id) == (0, 0, 0)

        repairs = (
            await db_session.execute(
                select(StockReportRepairRecord)
                .where(StockReportRepairRecord.workspace_id == workspace_id)
                .order_by(StockReportRepairRecord.field)
            )
        ).scalars().all()
        assert [
            (repair.field, repair.stored_value, repair.recomputed_value, repair.trigger)
            for repair in repairs
        ] == [
            ("quantity_in_progress", "1", "0", "inline:items_processed"),
            ("quantity_in_queue", "0", "0", "inline:items_processed"),
        ]
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
