"""Plan 13A — the two contention rows (master plan §9 rule 9; intention §5A MC-1,
§4A MC-4).

`C5(a)` — the webhook takes tasks **before** rows, so a session already holding a
task row can still take the stock-report row and no cycle forms. `C5(g)` — two
concurrent *demand* batches with overlapping new identities do not deadlock, which
is what MC-4's sorted VALUES and sorted `FOR UPDATE` buy; the row lives here because
this file owns the two-session machinery (plan 13A §4, projection r0 F-10).

Both rows are deterministic: a held lock plus a bounded wait, never an unforced
interleaving. Under either mutation the cycle is detected after `deadlock_timeout`
(1 s on the installed PostgreSQL 18.6) and one side raises
`sqlalchemy.exc.DBAPIError` with `exc.orig.sqlstate == "40P01"` — the asyncpg
dialect maps `DeadlockDetectedError` at `PostgresError`, i.e. to the **base** DBAPI
error class, so a test written against `OperationalError` would not catch it.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from beyo_manager.config import Settings, settings
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
    normalize_stock_criteria,
)
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.services.commands.stock_report.apply_stock_demand import (
    apply_stock_demand,
)
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from beyo_manager.services.commands.stock_report.process_stock_demand_deleted import (
    process_stock_demand_deleted,
)
from beyo_manager.services.commands.stock_report.stock_demand_entries import DemandEntry
from beyo_manager.services.context import ServiceContext
from tests.helpers.stock_report import (
    make_ctx,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

API_KEY = "test-stock-demand-deleted-locks-key"
NOW = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
CRITERIA = {"wood_group": ["teak"]}
CATEGORY = "Dining Chairs"
TIMEOUT_MS = Settings.model_fields["stock_demand_webhook_timeout_ms"].default


def _entry(index, properties_raw, quantity=10, category=CATEGORY):
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
        timeout_ms=TIMEOUT_MS,
    )


def _dd_ctx(session):
    body = json.dumps([{"itemCategory": CATEGORY, "properties": CRITERIA}]).encode(
        "utf-8"
    )
    return ServiceContext(
        identity={},
        incoming_data={"raw_body": body, "headers": {"x-api-key": API_KEY}},
        session=session,
        now=NOW,
    )


async def test_c5a_the_webhook_waits_on_the_task_before_it_takes_the_row(
    db_session, monkeypatch
):
    """C5(a), §14E carried question (1). A second session holds task T's row lock the
    way a task command's own `Task.state` UPDATE does (MC-1 class 3). The webhook is
    started and is **still waiting** half a second later; the holder can then take
    R's row lock immediately, which is only true because the webhook takes **tasks
    before rows**. With the two classes swapped the two sessions hold each other's
    next lock and PostgreSQL raises `40P01`.
    """
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    monkeypatch.setattr(settings, "manager_api_key_to_location_tracker_app", API_KEY)
    monkeypatch.setattr(
        settings, "location_tracker_webhook_workspace_id", workspace_id
    )
    try:
        demand = await _AD(db_session, workspace_id, [_entry(0, CRITERIA)])
        row_id = demand.events[0].client_id
        ctx = make_ctx(
            db_session,
            seeded,
            role_name="worker",
            incoming_data={
                "entries": [
                    {
                        "stock_report_item_id": row_id,
                        "task_id": seeded.task.client_id,
                        "item_id": seeded.item.client_id,
                        "override_property_mismatch": False,
                    }
                ]
            },
        )
        await create_stock_task_assignments(ctx)
        await db_session.commit()

        async for holder in get_db_session():
            # H holds T's row lock, exactly as a task command's own UPDATE does.
            await holder.execute(
                text(
                    "UPDATE tasks SET updated_at = updated_at WHERE client_id = :task_id"
                ),
                {"task_id": seeded.task.client_id},
            )

            dd_task = asyncio.create_task(
                process_stock_demand_deleted(_dd_ctx(db_session))
            )
            # It must NOT have returned: it is waiting on T at the class-3 lock.
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(asyncio.shield(dd_task), timeout=0.5)

            # R is not locked yet — rows come after tasks.
            locked = await asyncio.wait_for(
                holder.execute(
                    select(StockReportItem.client_id)
                    .where(StockReportItem.client_id == row_id)
                    .with_for_update()
                ),
                timeout=0.5,
            )
            assert locked.scalar_one() == row_id
            await holder.commit()

            result = await asyncio.wait_for(dd_task, timeout=5)
            assert [entry["outcome"] for entry in result["results"]] == ["deleted"]
            break
        else:  # pragma: no cover - the generator always yields one session
            raise AssertionError("Database session generator yielded no session")

        deleted = (
            await db_session.execute(
                select(StockReportItem)
                .where(StockReportItem.client_id == row_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        assert deleted.is_deleted is True
    finally:
        await db_session.rollback()
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c5g_two_demand_batches_with_overlapping_new_identities_do_not_deadlock(
    db_session,
):
    """C5(g), owner-authored (batch B2 card 1, CF-2). Two demand batches name the same
    two **new** identities in opposite request order and are released together. The
    sorted VALUES and the sorted `FOR UPDATE` make both sessions take the two row
    locks in the same order, so neither waits on the other's first lock: both
    complete, one row exists per identity, and each identity is created exactly once.

    Measured 2026-09-21: removing **both** sorts leaves all 28 phase-6 tests green —
    nothing existing contends, which is why this row had to be written.

    **This test does not arm the two sorts, and that is measured, not assumed.**
    Batch D2 ran both named mutations against it — `sorted()` dropped from
    `absent_identities`, and `.order_by(StockReportItem.client_id)` dropped from the
    locking `SELECT` — at two identities and again at forty, twice each: **green every
    time.** The reason is structural, not a fixture size: each batch's absent
    identities go in as **one** multi-row `INSERT … ON CONFLICT DO NOTHING`, and a
    backend runs that statement to completion unless it blocks. The second session's
    client-side work (statement compilation) costs more than the first session's whole
    insert, so the first always holds every new row before the second touches one, and
    the second then blocks on a single row while holding none. No cycle can form, in
    either sort order. What this test does prove is the positive half: both batches
    complete, exactly one live row exists per identity, each identity is created
    exactly once, and neither side raises. The sorts themselves are checked
    structurally — they are present at `apply_stock_demand.py`'s `absent_identities`
    and on its `FOR UPDATE` select — per master plan §9 rule 9.
    """
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        properties_x = {"wood_group": ["teak"]}
        properties_y = {"wood_group": ["oak"]}
        entries_a = [_entry(0, properties_x, 1), _entry(1, properties_y, 2)]
        entries_b = [_entry(0, properties_y, 2), _entry(1, properties_x, 1)]
        barrier = asyncio.Barrier(2)

        async def _run_main():
            await barrier.wait()
            return await _AD(db_session, workspace_id, entries_a)

        async def _run_second():
            async for session2 in get_db_session():
                await barrier.wait()
                return await _AD(session2, workspace_id, entries_b)
            raise AssertionError("Database session generator yielded no session")

        result_a, result_b = await asyncio.wait_for(
            asyncio.gather(_run_main(), _run_second()), timeout=15
        )

        assert [outcome.outcome.value for outcome in result_a.outcomes] == [
            "applied",
            "applied",
        ]
        assert [outcome.outcome.value for outcome in result_b.outcomes] == [
            "applied",
            "applied",
        ]

        rows = (
            (
                await db_session.execute(
                    select(StockReportItem).where(
                        StockReportItem.workspace_id == workspace_id,
                        StockReportItem.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 2
        signatures = sorted(row.properties_signature for row in rows)
        assert signatures == sorted(
            [
                compute_stock_criteria_signature(properties_x),
                compute_stock_criteria_signature(properties_y),
            ]
        )

        created = [
            event
            for event in result_a.events + result_b.events
            if event.event_name == "stock_report_item:created"
        ]
        assert sorted(event.client_id for event in created) == sorted(
            row.client_id for row in rows
        )
        assert len(created) == 2
    finally:
        await db_session.rollback()
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()
