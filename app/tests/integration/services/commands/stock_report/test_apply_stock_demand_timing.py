"""Plan 6 — C7: the demand webhook's time budget (intention §8B MC-9 rule-10
instrument; master plan §9 rule 10).

C7(b) is the project's **only** test that sleeps past the default (~8s wall time).
It lives in its own file so it can be excluded from L1 loops **by file, never by
`-k`** (H25).
"""

import asyncio
import time
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from beyo_manager.config import Settings
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
    normalize_stock_criteria,
)
from beyo_manager.errors.stock_report import StockDemandDeadlineExceeded
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.services.commands.stock_report import apply_stock_demand as apply_stock_demand_module
from beyo_manager.services.commands.stock_report.stock_demand_entries import DemandEntry
from tests.helpers.statement_listener import record_statement_calls
from tests.helpers.stock_report import (
    assert_stock_report_clean,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
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
    return await apply_stock_demand_module.apply_stock_demand(
        session,
        workspace_id=workspace_id,
        entries=entries,
        now=now if now is not None else NOW,
        deadline=deadline if deadline is not None else time.monotonic() + 60,
        timeout_ms=timeout_ms if timeout_ms is not None else _DEFAULT_TIMEOUT_MS,
    )


async def test_c7a_default_timeout_is_the_first_statement_with_both_params(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        async with record_statement_calls(db_session) as calls:
            await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", {"wood_group": ["teak"]}, 5)])

        assert calls, "expected at least one recorded statement"
        first_statement, first_params = calls[0]
        assert "set_config" in first_statement
        expected = str(_DEFAULT_TIMEOUT_MS)
        assert tuple(first_params) == (expected, expected)

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c7b_statement_timeout_fires_before_the_holder_releases(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        properties_raw = {"wood_group": ["teak"]}
        first = await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 5)])
        row_id = first.events[0].client_id

        hold_seconds = (_DEFAULT_TIMEOUT_MS + 3000) / 1000
        holder_locked = asyncio.Event()

        async def _holder():
            async for session in get_db_session():
                await session.execute(
                    select(StockReportItem)
                    .where(StockReportItem.client_id == row_id)
                    .with_for_update()
                )
                holder_locked.set()
                await asyncio.sleep(hold_seconds)
                await session.commit()
                return
            raise AssertionError("Database session generator yielded no session")

        holder_task = asyncio.create_task(_holder())
        await asyncio.wait_for(holder_locked.wait(), timeout=5)

        started = time.monotonic()
        with pytest.raises(DBAPIError) as excinfo:
            await _AD(db_session, workspace_id, [_entry(0, "Dining Chairs", properties_raw, 9)])
        elapsed = time.monotonic() - started

        assert excinfo.value.orig.sqlstate == "57014"
        assert elapsed >= (_DEFAULT_TIMEOUT_MS - 250) / 1000
        assert not holder_task.done()

        await asyncio.wait_for(holder_task, timeout=10)

        row = await db_session.scalar(
            select(StockReportItem).where(StockReportItem.client_id == row_id)
        )
        assert row.quantity_requested == 5

        history = (
            await db_session.execute(
                select(StockReportHistoryRecord).where(
                    StockReportHistoryRecord.stock_report_item_id == row_id
                )
            )
        ).scalars().all()
        assert len(history) == 1
        assert history[0].quantity_requested == 5

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c7c_deadline_exceeded_raises_before_commit(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        deadline = time.monotonic() + 60
        monkeypatch.setattr(
            apply_stock_demand_module,
            "time",
            SimpleNamespace(monotonic=lambda: deadline + 1),
        )

        with pytest.raises(StockDemandDeadlineExceeded) as excinfo:
            await apply_stock_demand_module.apply_stock_demand(
                db_session,
                workspace_id=workspace_id,
                entries=[_entry(0, "Dining Chairs", {"wood_group": ["teak"]}, 5)],
                now=NOW,
                deadline=deadline,
                timeout_ms=_DEFAULT_TIMEOUT_MS,
            )
        assert excinfo.value.http_status == 503

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
