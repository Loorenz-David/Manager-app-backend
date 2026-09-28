"""Draft versions, step 4 (2026-09-28; plan §4.5, §5, §7's schedule kind): the
PATCH-version route, the delayed-scheduler row behind a schedule, the scheduler
chain end to end, the supersede rules of a scheduled fire, and the
`schedule_scheduler_mismatch` consistency kind with its repair.

Every test here is a committing test, like `test_draft_versions.py` (whose
helpers it reuses): `seed -> commit -> … -> finally purge + commit`. **Scheduler
hygiene** (plan §9, Q-11): `delayed_schedulers` and the execution tables have no
workspace column, and the runner's and router's queries are global (`limit`, no
`ORDER BY`), so `purge_stock_report_workspace` deletes the scheduler rows whose
`event_client_id` is one of the workspace's versions, and the execution tasks and
payloads they produced — every test here purges in `finally`. The runner and the
router therefore run on their own sessions against the worker database and are
driven **until our row moves** (each call advances up to its batch), never on the
assumption that no neighbour exists.

The handler runs the command on its own session with the real clock, so the
schedules it fires are built on the real clock too: a draft is created with the
request clock two hours back and a schedule half an hour back — the create
command's "after now" is judged against the request's own `now`, so an overdue
schedule is built through the API, with its scheduler row, and consistency is
clean from the start (Q-12).
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from beyo_manager.domain.execution.enums import ExecutionTaskStateEnum, TaskType
from beyo_manager.domain.schedulers.enums import (
    DelayedSchedulerTypeEnum,
    SchedulerStateEnum,
)
from beyo_manager.domain.stock_report.enums import (
    StockReportHistoryRecordTypeEnum,
    StockReportRepairTargetKindEnum,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.execution.execution_payload import ExecutionPayload
from beyo_manager.models.tables.execution.execution_task import ExecutionTask
from beyo_manager.models.tables.schedulers.delayed_scheduler import DelayedScheduler
from beyo_manager.models.tables.stock_report.stock_report_repair_record import (
    StockReportRepairRecord,
)
from beyo_manager.services.commands.stock_report.activate_stock_report_snapshot_version import (
    activate_stock_report_snapshot_version,
)
from beyo_manager.services.commands.stock_report.delete_stock_report_snapshot_version import (
    delete_stock_report_snapshot_version,
)
from beyo_manager.services.commands.stock_report.repair_stock_report import (
    repair_stock_report,
)
from beyo_manager.services.commands.stock_report.update_stock_report_snapshot_version import (
    update_stock_report_snapshot_version,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.execution.task_router import _route_open_tasks
from beyo_manager.services.infra.schedulers.delayed_scheduler_runner import (
    _fire_due_schedulers,
)
from beyo_manager.services.infra.schedulers.scheduler_factory import (
    create_delayed_scheduler,
)
from beyo_manager.services.queries.stock_report.consistency import (
    compute_stock_report_divergences,
)
from beyo_manager.services.tasks.stock_report.handle_activate_stock_report_snapshot_version import (
    handle_activate_stock_report_snapshot_version,
)
from beyo_manager.workers.tasks_worker import HANDLER_MAP
from tests.helpers.statement_listener import record_statements
from tests.helpers.stock_report import (
    assert_stock_report_clean,
    capture_dispatch,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)
from tests.integration.services.commands.stock_report.test_draft_versions import (
    NOW,
    _AD,
    _COMMANDS,
    _CV,
    _SM,
    _SP,
    _SR,
    _activate,
    _by_token,
    _ctx,
    _draft,
    _entry,
    _pin,
    _records,
    _snapshots_of,
    _version_row,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

_ACTIVATION = DelayedSchedulerTypeEnum.STOCK_REPORT_VERSION_ACTIVATION
_ACTIVATE_DISPATCH = f"{_COMMANDS}.activate_stock_report_snapshot_version.dispatch"
_BLOCKED_FOR = 0.5
_PLUS_TWO = timezone(timedelta(hours=2))


def _clock():
    """The real clock, to the second: what the handler's `ServiceContext` reads."""
    return datetime.now(timezone.utc).replace(microsecond=0)


async def _PV(session, seeded, version_id, body, *, now=NOW, monkeypatch=None):
    captured = (
        capture_dispatch(
            monkeypatch, f"{_COMMANDS}.update_stock_report_snapshot_version.dispatch"
        )
        if monkeypatch is not None
        else None
    )
    result = await update_stock_report_snapshot_version(
        _ctx(session, seeded, incoming_data={**body, "client_id": version_id}, now=now)
    )
    await session.commit()
    return result, captured


async def _scheduled(session, seeded, at, *, now, title=None, keep=False):
    body = {
        "draft": True,
        "scheduled_activation_at": at.isoformat(),
        "scheduled_activation_keeps_active_missing": keep,
    }
    if title is not None:
        body["title"] = title
    version, _ = await _CV(session, seeded, body=body, now=now)
    return version


async def _schedulers(session, version_id):
    rows = (
        (
            await session.execute(
                select(DelayedScheduler)
                .where(
                    DelayedScheduler.event_client_id == version_id,
                    DelayedScheduler.type == _ACTIVATION,
                )
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    await session.commit()
    return rows


async def _active_scheduler(session, version_id):
    active = [
        row
        for row in await _schedulers(session, version_id)
        if row.state == SchedulerStateEnum.ACTIVE
    ]
    assert len(active) <= 1, active
    return active[0] if active else None


async def _fire(version_payload, *, monkeypatch=None):
    """The worker hop alone: the handler with the payload the scheduler row
    carries (what the runner copies into the execution payload verbatim)."""
    captured = (
        capture_dispatch(monkeypatch, _ACTIVATE_DISPATCH)
        if monkeypatch is not None
        else None
    )
    await handle_activate_stock_report_snapshot_version(version_payload, "tsk_test")
    return captured


async def _divergences(session, workspace_id):
    found = await compute_stock_report_divergences(session, workspace_id)
    await session.commit()
    return found


class _RecordingRedis:
    """The router's Redis seam: records `rpush`, answers `llen` for its log line."""

    def __init__(self):
        self.pushed = []

    def rpush(self, name, value):
        self.pushed.append((name, value))

    def llen(self, name):
        return sum(1 for queue, _ in self.pushed if queue == name)


async def _run_the_chain(session, scheduler_id):
    """Hop 1 — the runner fires the due row into an OPEN execution task; hop 2 —
    the router pushes it onto its queue; hop 3 — the worker's handler map runs it.
    Each hop is driven until **our** row moves: the runner and the router are
    global and batched."""
    for _ in range(20):
        await _fire_due_schedulers()
        state = await session.scalar(
            select(DelayedScheduler.state)
            .where(DelayedScheduler.client_id == scheduler_id)
            .execution_options(populate_existing=True)
        )
        await session.commit()
        if state == SchedulerStateEnum.FIRED:
            break
    assert state == SchedulerStateEnum.FIRED
    task_id, payload = (
        await session.execute(
            select(ExecutionPayload.execution_task_id, ExecutionPayload.payload).where(
                ExecutionPayload.origin_id == scheduler_id
            )
        )
    ).one()
    task = await session.scalar(
        select(ExecutionTask).where(ExecutionTask.client_id == task_id)
    )
    assert task.task_type is TaskType.STOCK_REPORT_VERSION_ACTIVATION
    assert task.state is ExecutionTaskStateEnum.OPEN
    await session.commit()

    redis = _RecordingRedis()
    for _ in range(20):
        await _route_open_tasks(redis)
        if ("queue:tasks", task_id) in redis.pushed:
            break
    assert ("queue:tasks", task_id) in redis.pushed

    await HANDLER_MAP[TaskType.STOCK_REPORT_VERSION_ACTIVATION](payload, task_id)


# ---------------------------------------------------------------------------
# The schedule and its scheduler row (§4.1, §4.5, §5.2)
# ---------------------------------------------------------------------------


async def test_a_schedule_keeps_exactly_one_active_scheduler_row_in_utc(
    db_session, monkeypatch
):
    raw = await seed_stock_report_workspace(db_session)
    seeded = _pin(db_session, raw)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    user_id = seeded.identity["user_id"]
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10)])
        active, _ = await _CV(db_session, seeded)

        # Create with a `+02:00` schedule: stored, echoed and fired in UTC.
        draft = await _scheduled(
            db_session,
            seeded,
            datetime(2026, 10, 5, 6, 0, tzinfo=_PLUS_TWO),
            now=NOW,
        )
        assert draft["scheduled_activation_at"] == "2026-10-05T04:00:00+00:00"
        first = await _active_scheduler(db_session, draft["client_id"])
        assert first.scheduled_for == datetime(2026, 10, 5, 4, 0, tzinfo=timezone.utc)
        assert first.payload_snapshot == {
            "workspace_id": workspace_id,
            "version_id": draft["client_id"],
            "scheduled_by_user_id": user_id,
            "scheduled_for": "2026-10-05T04:00:00+00:00",
        }
        await assert_stock_report_clean(db_session, workspace_id)

        # The missing flag alone: stored, read at fire time — no scheduler change.
        result, events = await _PV(
            db_session,
            seeded,
            draft["client_id"],
            {"scheduled_activation_keeps_active_missing": True},
            monkeypatch=monkeypatch,
        )
        assert set(result) == {"stock_report_snapshot_version"}
        assert (
            result["stock_report_snapshot_version"][
                "scheduled_activation_keeps_active_missing"
            ]
            is True
        )
        assert [
            row.client_id for row in await _schedulers(db_session, draft["client_id"])
        ] == [first.client_id]
        assert (await _active_scheduler(db_session, draft["client_id"])).client_id == (
            first.client_id
        )
        assert [(e.event_name, e.client_id, e.extra) for e in events] == [
            (
                "stock_report_snapshot_version:updated",
                draft["client_id"],
                {
                    "title": None,
                    "scheduled_activation_at": "2026-10-05T04:00:00+00:00",
                    "scheduled_activation_keeps_active_missing": True,
                },
            )
        ]

        # Moving the date cancels the row and creates one at the new instant.
        _, events = await _PV(
            db_session,
            seeded,
            draft["client_id"],
            {"scheduled_activation_at": "2026-10-06T08:30:00+02:00"},
            monkeypatch=monkeypatch,
        )
        rows = {
            row.client_id: row
            for row in await _schedulers(db_session, draft["client_id"])
        }
        assert rows[first.client_id].state is SchedulerStateEnum.CANCELED
        moved = await _active_scheduler(db_session, draft["client_id"])
        assert moved.client_id != first.client_id
        assert moved.scheduled_for == datetime(2026, 10, 6, 6, 30, tzinfo=timezone.utc)
        assert moved.payload_snapshot["scheduled_for"] == "2026-10-06T06:30:00+00:00"
        assert [e.extra["scheduled_activation_at"] for e in events] == [
            "2026-10-06T06:30:00+00:00"
        ]
        await assert_stock_report_clean(db_session, workspace_id)

        # The same instant again, and `{}`: nothing changes, nothing is emitted.
        _, same_events = await _PV(
            db_session,
            seeded,
            draft["client_id"],
            {"scheduled_activation_at": "2026-10-06T06:30:00+00:00"},
            monkeypatch=monkeypatch,
        )
        unchanged, empty_events = await _PV(
            db_session, seeded, draft["client_id"], {}, monkeypatch=monkeypatch
        )
        assert (same_events, empty_events) == ([], [])
        assert len(await _schedulers(db_session, draft["client_id"])) == 2
        assert unchanged["stock_report_snapshot_version"][
            "scheduled_activation_at"
        ] == ("2026-10-06T06:30:00+00:00")

        # A title, then `title: null` clears the title only.
        await _PV(db_session, seeded, draft["client_id"], {"title": "  Monday push "})
        assert (
            await _version_row(db_session, draft["client_id"])
        ).title == "Monday push"
        cleared, _ = await _PV(db_session, seeded, draft["client_id"], {"title": None})
        version = cleared["stock_report_snapshot_version"]
        assert version["title"] is None
        assert version["scheduled_activation_at"] == "2026-10-06T06:30:00+00:00"
        assert version["scheduled_activation_keeps_active_missing"] is True

        # Clearing the date cancels the row.
        _, events = await _PV(
            db_session,
            seeded,
            draft["client_id"],
            {"scheduled_activation_at": None},
            monkeypatch=monkeypatch,
        )
        assert await _active_scheduler(db_session, draft["client_id"]) is None
        assert (
            await _version_row(db_session, draft["client_id"])
        ).scheduled_activation_at is None
        assert [e.extra["scheduled_activation_at"] for e in events] == [None]
        await assert_stock_report_clean(db_session, workspace_id)

        # Refusals, each writing nothing.
        for body in (
            {"scheduled_activation_at": NOW.isoformat()},
            {"scheduled_activation_at": "2026-09-28T11:00:00+00:00"},
        ):
            with pytest.raises(
                ValidationError, match="STOCK_REPORT_SCHEDULE_IN_THE_PAST"
            ):
                await _PV(db_session, seeded, draft["client_id"], body)
            await db_session.rollback()
            with pytest.raises(
                ValidationError, match="STOCK_REPORT_SCHEDULE_IN_THE_PAST"
            ):
                await _CV(db_session, seeded, body={"draft": True, **body})
            await db_session.rollback()
        with pytest.raises(ValidationError, match="scheduled_activation_at"):
            await _PV(
                db_session,
                seeded,
                draft["client_id"],
                {"scheduled_activation_at": "2026-10-06T06:30:00"},
            )
        await db_session.rollback()
        for body in (
            {"scheduled_activation_at": None},
            {"scheduled_activation_keeps_active_missing": False},
            {"scheduled_activation_at": "2026-10-06T06:30:00+00:00"},
        ):
            with pytest.raises(ValidationError, match="STOCK_REPORT_VERSION_NOT_DRAFT"):
                await _PV(db_session, seeded, active["client_id"], body)
            await db_session.rollback()
        with pytest.raises(NotFound):
            await _PV(db_session, seeded, "srv_absent", {"title": "x"})
        await db_session.rollback()
        assert await _active_scheduler(db_session, draft["client_id"]) is None

        # A title on the active version is fine (any state).
        titled, _ = await _PV(
            db_session, seeded, active["client_id"], {"title": "Board"}
        )
        assert titled["stock_report_snapshot_version"]["title"] == "Board"

        # The flag without a date at create: stored, no scheduler row (FQ-16).
        flag_only, _ = await _CV(
            db_session,
            seeded,
            body={"draft": True, "scheduled_activation_keeps_active_missing": True},
        )
        assert flag_only["scheduled_activation_keeps_active_missing"] is True
        assert await _schedulers(db_session, flag_only["client_id"]) == []
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_deleting_or_activating_a_scheduled_draft_by_hand_cancels_its_row(
    db_session,
):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10)])
        await _CV(db_session, seeded)
        doomed = await _scheduled(
            db_session, seeded, datetime(2026, 10, 5, 4, tzinfo=timezone.utc), now=NOW
        )
        kept = await _scheduled(
            db_session, seeded, datetime(2026, 10, 6, 4, tzinfo=timezone.utc), now=NOW
        )

        await delete_stock_report_snapshot_version(
            _ctx(db_session, seeded, incoming_data={"client_id": doomed["client_id"]})
        )
        await db_session.commit()
        assert [
            row.state for row in await _schedulers(db_session, doomed["client_id"])
        ] == [SchedulerStateEnum.CANCELED]

        # R-2: by hand, before its time — 200, the schedule cleared in the same
        # statement as `active_at`, the row cancelled.
        activated, _ = await _activate(db_session, seeded, kept["client_id"])
        assert activated["state"] == "active"
        assert activated["scheduled_activation_at"] is None
        assert [
            row.state for row in await _schedulers(db_session, kept["client_id"])
        ] == [SchedulerStateEnum.CANCELED]
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# The chain, end to end (P-10, R-1, R-8, Q-5)
# ---------------------------------------------------------------------------


async def test_a_due_schedule_goes_through_all_three_hops_and_activates(
    db_session, monkeypatch
):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    user_id = seeded.identity["user_id"]
    clock = _clock()
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10), _entry(1, "b", 5)])
        rows = await _by_token(db_session, workspace_id)
        board, _ = await _CV(db_session, seeded, now=clock - timedelta(hours=2))
        await _SM(db_session, seeded, rows["b"], 2)
        # Sent with a `+02:00` offset: a string comparison at fire time would
        # call it moved and skip it (Q-5). The stored flag says "carry the closing
        # board's missing" — a scheduled fire reads it at fire time (R-6, P-5).
        due = (clock - timedelta(minutes=30)).astimezone(_PLUS_TWO)
        draft = await _scheduled(
            db_session,
            seeded,
            due,
            now=clock - timedelta(hours=2),
            title="Early",
            keep=True,
        )
        await _SP(db_session, seeded, rows["a"], "high", version_id=draft["client_id"])
        await _SR(db_session, seeded, rows["b"], 7, version_id=draft["client_id"])
        # Scanner moves after the draft was scheduled: the fire freezes this.
        await _AD(db_session, workspace_id, [_entry(0, "a", 12)])
        scheduler = await _active_scheduler(db_session, draft["client_id"])
        events = capture_dispatch(monkeypatch, _ACTIVATE_DISPATCH)

        await _run_the_chain(db_session, scheduler.client_id)

        version = await _version_row(db_session, draft["client_id"])
        assert version.active_at is not None and version.closed_at is None
        # The fire time, never the scheduled time (R-15).
        assert version.active_at > due
        assert version.scheduled_activation_at is None
        previous = await _version_row(db_session, board["client_id"])
        assert previous.closed_at == version.active_at
        # Stamped with the user who set the schedule.
        assert previous.closed_by_id == user_id
        snapshots = await _snapshots_of(db_session, draft["client_id"])
        assert snapshots[rows["a"]].quantity_requested_scanner == 12
        assert snapshots[rows["b"]].quantity_requested_scanner == 5
        assert snapshots[rows["b"]].quantity_requested_manual == 7
        assert snapshots[rows["b"]].quantity_missing == 2
        assert snapshots[rows["a"]].quantity_missing == 0
        [record] = [
            r
            for r in await _records(db_session, workspace_id)
            if r.type == StockReportHistoryRecordTypeEnum.PRIORITY_CHANGE
            and r.created_at == version.active_at
        ]
        assert (record.stock_report_item_id, record.created_by_id) == (
            rows["a"],
            user_id,
        )
        assert [
            (e.event_name, e.extra.get("scheduled"), e.extra.get("keep_active_missing"))
            for e in events
        ] == [
            ("stock_report_snapshot_version:closed", None, None),
            ("stock_report_snapshot_version:activated", True, True),
        ]
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# A scheduled fire that must not publish (§4.2 step 2, P-6, card 4, card 5)
# ---------------------------------------------------------------------------


async def test_a_moved_or_cleared_schedule_never_fires_at_the_old_time(
    db_session, monkeypatch
):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    clock = _clock()
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10)])
        await _CV(db_session, seeded, now=clock - timedelta(hours=2))
        moved = await _scheduled(
            db_session,
            seeded,
            clock - timedelta(minutes=30),
            now=clock - timedelta(hours=2),
        )
        cleared = await _scheduled(
            db_session,
            seeded,
            clock - timedelta(minutes=20),
            now=clock - timedelta(hours=2),
        )
        # The runner read these rows before the edits below (the stale fire).
        stale_moved = (
            await _active_scheduler(db_session, moved["client_id"])
        ).payload_snapshot
        stale_cleared = (
            await _active_scheduler(db_session, cleared["client_id"])
        ).payload_snapshot
        later = clock + timedelta(days=1)
        await _PV(
            db_session,
            seeded,
            moved["client_id"],
            {"scheduled_activation_at": later.isoformat()},
            now=clock - timedelta(hours=1),
        )
        await _PV(
            db_session,
            seeded,
            cleared["client_id"],
            {"scheduled_activation_at": None},
            now=clock - timedelta(hours=1),
        )

        events = await _fire(stale_moved, monkeypatch=monkeypatch)
        await _fire(stale_cleared)

        assert events == []
        version = await _version_row(db_session, moved["client_id"])
        assert version.active_at is None
        assert version.scheduled_activation_at == later
        pending = await _active_scheduler(db_session, moved["client_id"])
        assert pending.scheduled_for == later
        assert (await _version_row(db_session, cleared["client_id"])).active_at is None
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_a_board_published_by_hand_after_the_scheduled_time_stands(
    db_session, monkeypatch
):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    clock = _clock()
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10)])
        await _CV(db_session, seeded, now=clock - timedelta(hours=2))
        late = await _scheduled(
            db_session,
            seeded,
            clock - timedelta(minutes=30),
            now=clock - timedelta(hours=2),
            title="Late",
        )
        payload = (
            await _active_scheduler(db_session, late["client_id"])
        ).payload_snapshot
        by_hand, _ = await _draft(db_session, seeded, now=clock - timedelta(hours=2))
        await _activate(
            db_session, seeded, by_hand["client_id"], now=clock - timedelta(minutes=10)
        )

        events = await _fire(payload, monkeypatch=monkeypatch)

        version = await _version_row(db_session, late["client_id"])
        assert (version.active_at, version.scheduled_activation_at) == (None, None)
        assert [
            row.state for row in await _schedulers(db_session, late["client_id"])
        ] == [SchedulerStateEnum.CANCELED]
        assert (await _version_row(db_session, by_hand["client_id"])).closed_at is None
        assert [(e.event_name, e.client_id, e.extra) for e in events] == [
            (
                "stock_report_snapshot_version:updated",
                late["client_id"],
                {
                    "title": "Late",
                    "scheduled_activation_at": None,
                    "scheduled_activation_keeps_active_missing": False,
                },
            )
        ]
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


@pytest.mark.parametrize("order", ["earlier_first", "later_first"])
@pytest.mark.parametrize("tie", [False, True], ids=["later_time", "same_time"])
async def test_the_later_plan_wins_in_either_processing_order(db_session, order, tie):
    """Card 4: Monday's and Tuesday's drafts both overdue → Tuesday's. Card 5: two
    drafts at the same instant → the one created later. Either way, whichever fire
    the worker happens to process first."""
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    clock = _clock()
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10)])
        await _CV(db_session, seeded, now=clock - timedelta(hours=3))
        earlier_at = clock - timedelta(minutes=50)
        later_at = earlier_at if tie else clock - timedelta(minutes=20)
        # The winner is created first in wall time — the smaller ULID — but with
        # the later request clock, so only `created_at` can name it the draft
        # "created later" (card 5); a tie broken on `client_id` would pick the loser.
        winner = await _scheduled(
            db_session,
            seeded,
            later_at,
            now=clock - timedelta(hours=2) + timedelta(minutes=1),
        )
        loser = await _scheduled(
            db_session, seeded, earlier_at, now=clock - timedelta(hours=2)
        )
        assert winner["client_id"] < loser["client_id"]
        payloads = {
            name: (
                await _active_scheduler(db_session, version["client_id"])
            ).payload_snapshot
            for name, version in (("loser", loser), ("winner", winner))
        }

        for name in (
            ("loser", "winner") if order == "earlier_first" else ("winner", "loser")
        ):
            await _fire(payloads[name])

        won = await _version_row(db_session, winner["client_id"])
        lost = await _version_row(db_session, loser["client_id"])
        assert (won.active_at is not None, won.closed_at) == (True, None)
        assert (lost.active_at, lost.scheduled_activation_at) == (None, None)
        assert [
            row.state for row in await _schedulers(db_session, loser["client_id"])
        ] == [SchedulerStateEnum.CANCELED]
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_a_fire_for_a_deleted_or_hand_activated_draft_completes_without_retry(
    db_session,
):
    """P-6: a `DomainError` (404, not a draft) is logged and the task completes —
    the handler returns instead of raising, so the worker does not retry."""
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    clock = _clock()
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10)])
        await _CV(db_session, seeded, now=clock - timedelta(hours=2))
        deleted = await _scheduled(
            db_session,
            seeded,
            clock - timedelta(minutes=30),
            now=clock - timedelta(hours=2),
        )
        activated = await _scheduled(
            db_session,
            seeded,
            clock - timedelta(minutes=20),
            now=clock - timedelta(hours=2),
        )
        deleted_payload = (
            await _active_scheduler(db_session, deleted["client_id"])
        ).payload_snapshot
        activated_payload = (
            await _active_scheduler(db_session, activated["client_id"])
        ).payload_snapshot
        await delete_stock_report_snapshot_version(
            _ctx(db_session, seeded, incoming_data={"client_id": deleted["client_id"]})
        )
        await db_session.commit()
        by_hand, _ = await _activate(
            db_session, seeded, activated["client_id"], now=clock - timedelta(minutes=5)
        )

        await _fire(deleted_payload)
        await _fire(activated_payload)

        version = await _version_row(db_session, activated["client_id"])
        assert version.active_at == clock - timedelta(minutes=5)
        assert version.closed_at is None
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_a_manual_and_a_fired_activation_serialize_and_the_fire_skips(db_session):
    """§5.3: the handler's activation takes the same advisory lock; the fire queued
    behind a manual activation of the same draft sees "not a draft" and completes."""
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    clock = _clock()
    released = asyncio.Event()
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10)])
        await _CV(db_session, seeded, now=clock - timedelta(hours=2))
        draft = await _scheduled(
            db_session,
            seeded,
            clock - timedelta(minutes=30),
            now=clock - timedelta(hours=2),
        )
        payload = (
            await _active_scheduler(db_session, draft["client_id"])
        ).payload_snapshot
        manual_at = clock - timedelta(minutes=1)

        async for holder in get_db_session():
            fire = None
            try:
                # The manual activation runs inside a transaction it does not own
                # (`maybe_begin` joins it), so its locks are held until we commit.
                await holder.execute(select(1))
                await activate_stock_report_snapshot_version(
                    ServiceContext(
                        identity=seeded.identity,
                        incoming_data={"client_id": draft["client_id"]},
                        session=holder,
                        now=manual_at,
                    )
                )
                fire = asyncio.create_task(_fire(payload))
                with pytest.raises(asyncio.TimeoutError):
                    await asyncio.wait_for(asyncio.shield(fire), timeout=_BLOCKED_FOR)
                assert not fire.done()
                await holder.commit()
                released.set()
                await asyncio.wait_for(fire, timeout=10)
            finally:
                if not released.is_set():
                    await holder.rollback()
                    if fire is not None:
                        fire.cancel()
            break

        version = await _version_row(db_session, draft["client_id"])
        assert version.active_at == manual_at
        assert version.closed_at is None
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# schedule_scheduler_mismatch (plan §7, R-4, Q-13)
# ---------------------------------------------------------------------------


async def test_schedule_consistency_reports_and_repair_recovers(db_session):
    raw = await seed_stock_report_workspace(db_session)
    seeded = _pin(db_session, raw)
    repairer = raw.worker.client_id
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    clock = _clock()
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10)])
        board, _ = await _CV(db_session, seeded, now=clock - timedelta(hours=3))
        failed_at = clock - timedelta(minutes=40)
        failed = await _scheduled(
            db_session, seeded, failed_at, now=clock - timedelta(hours=2)
        )
        errored_at = clock - timedelta(minutes=45)
        errored = await _scheduled(
            db_session, seeded, errored_at, now=clock - timedelta(hours=2)
        )
        stray_target, _ = await _draft(
            db_session, seeded, now=clock - timedelta(hours=2)
        )

        # (a) fired, not yet processed — then its task fails for good.
        failed_row = await _active_scheduler(db_session, failed["client_id"])
        for _ in range(20):
            await _fire_due_schedulers()
            if (await _active_scheduler(db_session, failed["client_id"])) is None:
                break
        [task_id] = (
            await db_session.scalars(
                select(ExecutionPayload.execution_task_id).where(
                    ExecutionPayload.origin_id == failed_row.client_id
                )
            )
        ).all()
        await db_session.execute(
            update(ExecutionTask)
            .where(ExecutionTask.client_id == task_id)
            .values(state=ExecutionTaskStateEnum.FAIL)
        )
        # (b) a row that went to ERROR while due (never retried by the runner).
        # The runner fired it above too; put it back as the runner's error branch
        # leaves it.
        await db_session.execute(
            update(DelayedScheduler)
            .where(DelayedScheduler.event_client_id == errored["client_id"])
            .values(state=SchedulerStateEnum.ERROR)
        )
        # (c) an ACTIVE row no draft's column matches — on a draft without a
        # schedule, and on the (activated) board.
        stray_at = clock + timedelta(days=2)
        for version_id in (stray_target["client_id"], board["client_id"]):
            await create_delayed_scheduler(
                db_session,
                _ACTIVATION,
                stray_at,
                {"version_id": version_id},
                event_client_id=version_id,
            )
        await db_session.commit()

        schedule_rows = [
            d
            for d in await _divergences(db_session, workspace_id)
            if d["kind"] == "schedule_scheduler_mismatch"
        ]
        assert sorted(
            schedule_rows, key=lambda d: (d["client_id"], str(d["stored"]))
        ) == sorted(
            [
                {
                    "kind": "schedule_scheduler_mismatch",
                    "client_id": failed["client_id"],
                    "field": "scheduled_activation_at",
                    "stored": failed_at.isoformat(),
                    "expected": None,
                },
                {
                    "kind": "schedule_scheduler_mismatch",
                    "client_id": errored["client_id"],
                    "field": "scheduled_activation_at",
                    "stored": errored_at.isoformat(),
                    "expected": None,
                },
                {
                    "kind": "schedule_scheduler_mismatch",
                    "client_id": stray_target["client_id"],
                    "field": "scheduled_activation_at",
                    "stored": None,
                    "expected": stray_at.isoformat(),
                },
                {
                    "kind": "schedule_scheduler_mismatch",
                    "client_id": board["client_id"],
                    "field": "scheduled_activation_at",
                    "stored": None,
                    "expected": stray_at.isoformat(),
                },
            ],
            key=lambda d: (d["client_id"], str(d["stored"])),
        )

        result = await repair_stock_report(
            ServiceContext(
                identity={**seeded.identity, "user_id": repairer},
                incoming_data={},
                session=db_session,
                now=clock,
            )
        )
        await db_session.commit()
        assert sorted(
            (d["client_id"], d["stored"] is None) for d in result["repaired"]
        ) == sorted(
            [
                (failed["client_id"], False),
                (errored["client_id"], False),
                (stray_target["client_id"], True),
                (board["client_id"], True),
            ]
        )
        assert await _divergences(db_session, workspace_id) == []
        records = (
            await db_session.scalars(
                select(StockReportRepairRecord).where(
                    StockReportRepairRecord.workspace_id == workspace_id
                )
            )
        ).all()
        assert {r.target_kind for r in records} == {
            StockReportRepairTargetKindEnum.SNAPSHOT_VERSION
        }
        assert await _active_scheduler(db_session, stray_target["client_id"]) is None
        assert await _active_scheduler(db_session, board["client_id"]) is None
        # The re-armed rows are due at the stored instant, stamped with the
        # repairing user — and the late fire activates (card 3) or skips (card 4).
        rearmed = await _active_scheduler(db_session, failed["client_id"])
        assert rearmed.scheduled_for == failed_at
        assert rearmed.payload_snapshot["scheduled_by_user_id"] == repairer
        errored_rearmed = await _active_scheduler(db_session, errored["client_id"])
        assert errored_rearmed.scheduled_for == errored_at
        await _fire(errored_rearmed.payload_snapshot)
        await _fire(rearmed.payload_snapshot)
        # `failed` is scheduled later than `errored`: `errored` skipped as
        # superseded, `failed` activated, stamped by the repairing user.
        activated = await _version_row(db_session, failed["client_id"])
        assert activated.active_at is not None and activated.closed_at is None
        assert (
            await _version_row(db_session, board["client_id"])
        ).closed_by_id == repairer
        skipped = await _version_row(db_session, errored["client_id"])
        assert (skipped.active_at, skipped.scheduled_activation_at) == (None, None)
        assert await _divergences(db_session, workspace_id) == []
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# Lock order (plan §9): the scheduler row after every version row
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", ["patch", "activate", "delete"])
async def test_the_scheduler_row_is_locked_after_every_version_row(db_session, command):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        await _AD(db_session, workspace_id, [_entry(0, "a", 10)])
        await _CV(db_session, seeded)
        draft = await _scheduled(
            db_session, seeded, datetime(2026, 10, 5, 4, tzinfo=timezone.utc), now=NOW
        )
        async with record_statements(db_session) as statements:
            if command == "patch":
                await _PV(
                    db_session,
                    seeded,
                    draft["client_id"],
                    {"scheduled_activation_at": "2026-10-06T04:00:00+00:00"},
                )
            elif command == "activate":
                await _activate(db_session, seeded, draft["client_id"])
            else:
                await delete_stock_report_snapshot_version(
                    _ctx(
                        db_session,
                        seeded,
                        incoming_data={"client_id": draft["client_id"]},
                    )
                )
                await db_session.commit()
        classes = [
            "stock_report_items",
            "stock_report_item_snapshots",
            "stock_report_snapshot_versions",
            "delayed_schedulers",
        ]
        locked = [
            table
            for statement in statements
            if "FOR UPDATE" in statement.upper()
            for table in classes
            if f"FROM {table}" in statement
        ]
        assert locked[-1] == "delayed_schedulers", statements
        assert "stock_report_snapshot_versions" in locked, statements
        last_version = max(
            i
            for i, table in enumerate(locked)
            if table == "stock_report_snapshot_versions"
        )
        assert last_version < locked.index("delayed_schedulers"), statements
        if command != "delete":
            # The delete locks its version before its snapshots (plan §4.8).
            assert [classes.index(t) for t in locked] == sorted(
                classes.index(t) for t in locked
            ), statements
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()
