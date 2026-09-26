"""Plan 9 — C8(a): `process_items_processed` commits in one owning transaction
(master plan §6.5; intention §8B MC-9 "one owning transaction, nothing before it").

C8(b) (two concurrent requests, interleaving not forced) is not exercised here —
the plan itself declares its interleaving unforceable and routes the structural
check (one ascending-lock statement) to the reviewer.
"""

import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from beyo_manager.config import settings
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.domain.stock_report.enums import StockTaskAssignmentStateEnum as S
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from beyo_manager.services.commands.stock_report.process_items_processed import (
    process_items_processed,
)
from beyo_manager.services.context import ServiceContext
from tests.helpers.stock_report import (
    make_ctx,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

API_KEY = "test-processed-locks-key"
NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)


def _configure(monkeypatch, *, workspace_id):
    monkeypatch.setattr(settings, "manager_api_key_to_location_tracker_app", API_KEY)
    monkeypatch.setattr(settings, "location_tracker_webhook_workspace_id", workspace_id)


def _pr_ctx(session, *, numbers):
    body = json.dumps([{"article_number": n} for n in numbers]).encode("utf-8")
    return ServiceContext(
        identity={},
        incoming_data={"raw_body": body, "headers": {"x-api-key": API_KEY}},
        session=session,
        now=NOW,
    )


async def test_c8a_fresh_session_reads_the_committed_resolve(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    criteria = {"wood_group": ["teak"]}
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties=criteria,
        properties_signature=compute_stock_criteria_signature(criteria),
        quantity_requested=10,
    )
    db_session.add(row)
    await db_session.flush()
    workspace_id = seeded.workspace.client_id

    cr_ctx = make_ctx(
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
    created = await create_stock_task_assignments(cr_ctx)
    assignment_id = created["stock_task_assignments"][0]["client_id"]
    await db_session.commit()

    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        await process_items_processed(
            _pr_ctx(db_session, numbers=[seeded.item.article_number])
        )

        # A fresh session — not the one the command ran on — must see the commit:
        # this is what X3's "one owning transaction, nothing before it" buys.
        async for fresh_session in get_db_session():
            assignment = (
                await fresh_session.execute(
                    select(StockTaskAssignment).where(
                        StockTaskAssignment.client_id == assignment_id
                    )
                )
            ).scalar_one()
            assert assignment.state == S.RESOLVED_EARLY
            break
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_lock_order_is_rows_then_active_snapshots_then_assignments(
    db_session, monkeypatch
):
    """Addendum 2026-09-26: the resolve credits the row's active snapshot, so the
    webhook takes the snapshot lock class between rows and assignments (MC-1 order:
    stock_report_items -> stock_report_item_snapshots -> stock_task_assignments)."""
    from tests.helpers.statement_listener import record_statements
    from tests.helpers.stock_report import create_snapshot_version

    seeded = await seed_stock_report_workspace(db_session)
    criteria = {"wood_group": ["teak"]}
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties=criteria,
        properties_signature=compute_stock_criteria_signature(criteria),
        quantity_requested=10,
    )
    db_session.add(row)
    await db_session.flush()
    workspace_id = seeded.workspace.client_id
    await create_stock_task_assignments(
        make_ctx(
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
    )
    await create_snapshot_version(
        db_session, workspace_id, now=NOW, user_id=seeded.manager.client_id
    )
    await db_session.commit()

    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        async with record_statements(db_session) as statements:
            await process_items_processed(
                _pr_ctx(db_session, numbers=[seeded.item.article_number])
            )
        locked_tables = []
        for statement in statements:
            if "FOR UPDATE" not in statement.upper():
                continue
            for table in (
                "stock_report_items",
                "stock_report_item_snapshots",
                "stock_task_assignments",
            ):
                if f"FROM {table}" in statement:
                    locked_tables.append(table)
        assert locked_tables == [
            "stock_report_items",
            "stock_report_item_snapshots",
            "stock_task_assignments",
        ], statements
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()
