"""Plan 12 C2(c) — the deterministic proof that the ordering commands take the
workspace advisory lock before they read any position (master plan §6.5 `_locks.py`;
intention §7A "Serialization").

C2(a) and C2(b) — two real ordering operations released from a barrier — are
declared **class 3** by the plan: their interleaving is unforced, so no mutant can
force them and they are invariant checks, not the serialization proof. This file
holds the one row that *is* deterministic: a second session holding
`pg_advisory_xact_lock(hashtext('stock_report_order:' || W))` blocks the move until
it commits.

Second sessions follow §9 rule 9: opened with `get_db_session()`, synchronised with
`asyncio.Event`, every wait bounded by `asyncio.wait_for`, always released and
purged.
"""

import asyncio
import time
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from beyo_manager.config import Settings
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
    normalize_stock_criteria,
)
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.services.commands.stock_report.apply_stock_demand import (
    apply_stock_demand,
)
from beyo_manager.services.commands.stock_report.set_stock_report_item_priority_order import (
    set_stock_report_item_priority_order,
)
from beyo_manager.services.commands.stock_report.stock_demand_entries import DemandEntry
from beyo_manager.services.context import ServiceContext
from tests.helpers.stock_report import (
    assert_stock_report_clean,
    make_ctx,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
_TIMEOUT_MS = Settings.model_fields["stock_demand_webhook_timeout_ms"].default
BLOCKED_FOR = 0.5


async def _seed_high_group(session, workspace_id):
    """`high` = A1 B2 C3 D4, with `priority_order` ascending disagreeing with
    `client_id` ascending (plan 12 §6)."""
    entries = [
        DemandEntry(
            index=index,
            item_category_raw="Dining Chairs",
            properties_raw={"wood_group": [f"teak{index}"]},
            properties_normalized=normalize_stock_criteria(
                {"wood_group": [f"teak{index}"]}
            ),
            properties_signature=compute_stock_criteria_signature(
                {"wood_group": [f"teak{index}"]}
            ),
            quantity_requested=10,
        )
        for index in range(4)
    ]
    await apply_stock_demand(
        session,
        workspace_id=workspace_id,
        entries=entries,
        now=NOW,
        deadline=time.monotonic() + 60,
        timeout_ms=_TIMEOUT_MS,
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
    for order, client_id in enumerate(ids, 1):
        await session.execute(
            text(
                "UPDATE stock_report_items SET priority = 'high', "
                "priority_order = :order WHERE client_id = :client_id"
            ),
            {"order": order, "client_id": client_id},
        )
    await session.commit()
    return ids  # A, B, C, D


async def test_the_move_waits_for_the_workspace_ordering_lock(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    identity = make_ctx(db_session, seeded, role_name="seller").identity
    holder_released = asyncio.Event()
    try:
        A, B, C, D = await _seed_high_group(db_session, workspace_id)

        async for holder in get_db_session():
            async for mover_session in get_db_session():
                move = None
                try:
                    # Session H takes the ordering lock of W and keeps it.
                    await holder.execute(
                        text(
                            "SELECT pg_advisory_xact_lock("
                            "hashtext('stock_report_order:' || :workspace_id))"
                        ),
                        {"workspace_id": workspace_id},
                    )

                    move = asyncio.create_task(
                        set_stock_report_item_priority_order(
                            ServiceContext(
                                identity=identity,
                                incoming_data={"client_id": C, "priority_order": 1},
                                session=mover_session,
                            )
                        )
                    )
                    # It must not complete while H holds the lock.
                    with pytest.raises(asyncio.TimeoutError):
                        await asyncio.wait_for(
                            asyncio.shield(move), timeout=BLOCKED_FOR
                        )
                    assert not move.done()

                    await holder.rollback()  # releases the xact lock
                    holder_released.set()

                    await asyncio.wait_for(move, timeout=10)
                finally:
                    if not holder_released.is_set():
                        await holder.rollback()
                        if move is not None:
                            move.cancel()
                break
            break

        await db_session.rollback()
        state = {
            client_id: order
            for client_id, order in (
                await db_session.execute(
                    select(
                        StockReportItem.client_id, StockReportItem.priority_order
                    ).where(StockReportItem.workspace_id == workspace_id)
                )
            ).all()
        }
        assert [state[client_id] for client_id in (A, B, C, D)] == [2, 3, 1, 4]
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()
