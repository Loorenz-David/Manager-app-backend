"""`quantity_missing` (2026-09-26): the manual route
`set_stock_report_item_snapshot_missing_quantity` and the automatic clamp that
`move_assignment` runs on an assignment's creation.

Rows are created through `AD`, so these are committing tests (see
`test_snapshot_versions.py`).
"""

import time
from datetime import datetime, timezone

from types import SimpleNamespace

import pytest
from sqlalchemy import select, text

from beyo_manager.config import Settings, settings
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
    normalize_stock_criteria,
)
from beyo_manager.domain.stock_report.enums import StockTaskAssignmentStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.domain.items.enums import ItemStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.stock_report._move_assignment import move_assignment
from beyo_manager.services.commands.stock_report.apply_stock_demand import (
    apply_stock_demand,
)
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from beyo_manager.services.commands.stock_report.delete_stock_task_assignments import (
    delete_stock_task_assignments,
)
from beyo_manager.services.commands.stock_report.process_items_processed import (
    process_items_processed,
)
from beyo_manager.services.queries.stock_report.consistency import (
    compute_stock_report_divergences,
)
from beyo_manager.services.commands.stock_report.set_stock_report_item_snapshot_missing_quantity import (
    set_stock_report_item_snapshot_missing_quantity,
)
from beyo_manager.services.commands.stock_report.stock_demand_entries import DemandEntry
from beyo_manager.services.context import ServiceContext
from tests.helpers.statement_listener import count_writes, record_statements
from tests.helpers.stock_report import (
    active_snapshot,
    assert_stock_report_clean,
    capture_dispatch,
    create_snapshot_version,
    make_ctx,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


def _pin(session, seeded):
    """Everything a test reads from the seed, captured **once** while the ORM
    instances are live: `session.rollback()` expires them and a later attribute read
    would attempt IO outside the greenlet context (the `_seller` precedent)."""
    return SimpleNamespace(
        identity=make_ctx(session, seeded).identity,
        worker_identity=make_ctx(session, seeded, role_name="worker").identity,
        workspace=SimpleNamespace(client_id=seeded.workspace.client_id),
        manager=SimpleNamespace(client_id=seeded.manager.client_id),
        task=SimpleNamespace(client_id=seeded.task.client_id),
        item=SimpleNamespace(
            client_id=seeded.item.client_id, article_number=seeded.item.article_number
        ),
    )

NOW = datetime(2026, 9, 26, 12, 0, 0, tzinfo=timezone.utc)
_TIMEOUT_MS = Settings.model_fields["stock_demand_webhook_timeout_ms"].default
MISSING_SITE = (
    "beyo_manager.services.commands.stock_report"
    ".set_stock_report_item_snapshot_missing_quantity.dispatch"
)
CREATE_SITE = (
    "beyo_manager.services.commands.stock_report.create_stock_task_assignments.dispatch"
)
WRITE_TABLES = {
    "stock_report_items",
    "stock_report_item_snapshots",
    "stock_task_assignments",
    "stock_report_history_records",
    "tasks",
}


def _entry(index, token, quantity=10):
    raw = {"wood_group": [token]}
    return DemandEntry(
        index=index,
        item_category_raw="Dining Chairs",
        properties_raw=raw,
        properties_normalized=normalize_stock_criteria(raw),
        properties_signature=compute_stock_criteria_signature(raw),
        quantity_requested=quantity,
    )


async def _row_with_version(session, seeded, *, quantity=10):
    """One row of `quantity` requested, under an active version. Committed."""
    workspace_id = seeded.workspace.client_id
    await apply_stock_demand(
        session,
        workspace_id=workspace_id,
        entries=[_entry(0, "teak", quantity)],
        now=NOW,
        deadline=time.monotonic() + 60,
        timeout_ms=_TIMEOUT_MS,
    )
    await session.commit()
    row_id = await session.scalar(
        select(StockReportItem.client_id).where(
            StockReportItem.workspace_id == workspace_id
        )
    )
    await create_snapshot_version(
        session, workspace_id, now=NOW, user_id=seeded.manager.client_id
    )
    await session.commit()
    return row_id


def _ctx(session, seeded, incoming_data, *, role_name="worker"):
    return ServiceContext(
        identity=seeded.worker_identity if role_name == "worker" else seeded.identity,
        incoming_data=incoming_data,
        session=session,
        now=NOW,
    )


async def _SM(session, seeded, row_id, value, *, monkeypatch=None):
    captured = (
        capture_dispatch(monkeypatch, MISSING_SITE) if monkeypatch is not None else None
    )
    ctx = _ctx(session, seeded, {"client_id": row_id, "quantity_missing": value})
    result = await set_stock_report_item_snapshot_missing_quantity(ctx)
    await session.commit()
    return result, ctx, captured


async def _assign_seeded_item(session, seeded, row_id, *, monkeypatch=None):
    """The seeded item (quantity 4) on the seeded task (PRIMARY): in_queue += 4."""
    captured = (
        capture_dispatch(monkeypatch, CREATE_SITE) if monkeypatch is not None else None
    )
    result = await create_stock_task_assignments(
        _ctx(
            session,
            seeded,
            {
                "entries": [
                    {
                        "stock_report_item_id": row_id,
                        "task_id": seeded.task.client_id,
                        "item_id": seeded.item.client_id,
                        "override_property_mismatch": True,
                    }
                ]
            },
        )
    )
    await session.commit()
    return result["stock_task_assignments"][0]["client_id"], captured


# ---------------------------------------------------------------------------
# The manual route
# ---------------------------------------------------------------------------


async def test_set_missing_writes_the_active_snapshot_and_emits_one_event(
    db_session, monkeypatch
):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        row_id = await _row_with_version(db_session, seeded)
        # A worker, not only a manager.
        result, ctx, captured = await _SM(db_session, seeded, row_id, 3, monkeypatch=monkeypatch)

        snapshot = await active_snapshot(db_session, row_id)
        assert snapshot.quantity_missing == 3
        assert snapshot.updated_at == NOW
        assert snapshot.updated_by_id == seeded.manager.client_id
        assert result["stock_report_item"]["snapshot"]["quantity_missing"] == 3
        assert result["stock_report_item"]["client_id"] == row_id
        assert [(e.event_name, e.client_id, e.extra) for e in captured] == [
            (
                "stock_report_item_snapshot:updated",
                snapshot.client_id,
                {
                    "stock_report_item_id": row_id,
                    "version_id": snapshot.version_id,
                    "priority": None,
                    "priority_order": None,
                    "quantity_missing": 3,
                    "quantity_resolved": 0,
                },
            )
        ]
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


@pytest.mark.parametrize("value", [-1, 7, 11])
async def test_set_missing_refuses_values_outside_the_ceiling(db_session, value):
    """Requested 10 (frozen), 4 covered by an assignment: ceiling 6. Negative, 7 and
    11 are all refused with the identity; nothing is written."""
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        row_id = await _row_with_version(db_session, seeded)
        await _assign_seeded_item(db_session, seeded, row_id)
        assert (await active_snapshot(db_session, row_id)).quantity_missing == 0

        with pytest.raises(ValidationError) as excinfo:
            await _SM(db_session, seeded, row_id, value)
        await db_session.rollback()

        assert str(excinfo.value).startswith("STOCK_REPORT_MISSING_EXCEEDS_CEILING:")
        assert "6" in str(excinfo.value)
        assert (await active_snapshot(db_session, row_id)).quantity_missing == 0
        # The ceiling itself is accepted.
        await _SM(db_session, seeded, row_id, 6)
        assert (await active_snapshot(db_session, row_id)).quantity_missing == 6
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_set_missing_to_the_held_value_writes_nothing(db_session, monkeypatch):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        row_id = await _row_with_version(db_session, seeded)
        await _SM(db_session, seeded, row_id, 2)
        async with record_statements(db_session) as statements:
            result, _ctx, captured = await _SM(
                db_session, seeded, row_id, 2, monkeypatch=monkeypatch
            )
        assert count_writes(statements, WRITE_TABLES) == 0
        assert captured == []
        assert result["stock_report_item"]["snapshot"]["quantity_missing"] == 2
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_set_missing_boundaries_no_snapshot_deleted_foreign_absent(db_session):
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    foreign = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id, foreign_id = seeded.workspace.client_id, foreign.workspace.client_id
    try:
        row_id = await _row_with_version(db_session, seeded)
        # A row created after the version has no snapshot.
        await apply_stock_demand(
            db_session,
            workspace_id=workspace_id,
            entries=[_entry(1, "late", 5)],
            now=NOW,
            deadline=time.monotonic() + 60,
            timeout_ms=_TIMEOUT_MS,
        )
        await db_session.commit()
        late = await db_session.scalar(
            select(StockReportItem.client_id).where(
                StockReportItem.workspace_id == workspace_id,
                StockReportItem.client_id != row_id,
            )
        )
        with pytest.raises(ValidationError) as excinfo:
            await _SM(db_session, seeded, late, 1)
        await db_session.rollback()
        assert str(excinfo.value).startswith("STOCK_REPORT_NO_ACTIVE_SNAPSHOT:")

        foreign_row = await _row_with_version(db_session, foreign)
        await db_session.execute(
            text("UPDATE stock_report_items SET is_deleted = true WHERE client_id = :id"),
            {"id": late},
        )
        await db_session.commit()
        for client_id in (foreign_row, late, "sri_absent"):
            with pytest.raises(NotFound):
                await _SM(db_session, seeded, client_id, 1)
            await db_session.rollback()
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await purge_stock_report_workspace(db_session, foreign_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# The automatic clamp on assignment creation
# ---------------------------------------------------------------------------


async def test_creation_clamps_missing_down_to_the_new_remainder(db_session, monkeypatch):
    """Requested 10, all 10 marked missing; assigning the seeded item (4) leaves 6
    uncovered, so missing falls to 6, stamped by the assigning user, with one
    snapshot event beside the row's and the assignment's."""
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        row_id = await _row_with_version(db_session, seeded)
        await _SM(db_session, seeded, row_id, 10)

        assignment_id, captured = await _assign_seeded_item(
            db_session, seeded, row_id, monkeypatch=monkeypatch
        )

        snapshot = await active_snapshot(db_session, row_id)
        assert snapshot.quantity_missing == 6
        assert snapshot.updated_by_id == seeded.manager.client_id
        names = sorted(e.event_name for e in captured)
        assert names == [
            "stock_report_item:updated",
            "stock_report_item_snapshot:updated",
            "stock_task_assignment:created",
        ]
        snapshot_event = next(
            e for e in captured if e.event_name == "stock_report_item_snapshot:updated"
        )
        assert snapshot_event.client_id == snapshot.client_id
        assert snapshot_event.extra["quantity_missing"] == 6
        assert snapshot_event.extra["stock_report_item_id"] == row_id
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_creation_leaves_missing_alone_when_it_still_fits(db_session, monkeypatch):
    """Requested 10, missing 2; assigning 4 leaves 6 uncovered >= 2: untouched, no
    snapshot event, no stamp."""
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        row_id = await _row_with_version(db_session, seeded)
        await _SM(db_session, seeded, row_id, 2)
        before = await active_snapshot(db_session, row_id)

        _assignment_id, captured = await _assign_seeded_item(
            db_session, seeded, row_id, monkeypatch=monkeypatch
        )

        after = await active_snapshot(db_session, row_id)
        assert after.quantity_missing == 2
        assert after.updated_at == before.updated_at
        assert "stock_report_item_snapshot:updated" not in {e.event_name for e in captured}
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_moves_and_removals_never_clamp(db_session):
    """Only creation raises the covered quantity. A sync move between active states
    keeps it; a removal lowers it. Neither touches `quantity_missing`, and the
    remainder growing back after a removal does not raise it either."""
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        row_id = await _row_with_version(db_session, seeded)
        assignment_id, _ = await _assign_seeded_item(db_session, seeded, row_id)
        await _SM(db_session, seeded, row_id, 6)  # the full remainder

        assignment = (
            await db_session.execute(
                select(StockTaskAssignment)
                .where(StockTaskAssignment.client_id == assignment_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        await move_assignment(
            db_session,
            assignment,
            StockTaskAssignmentStateEnum.AWAITING,
            workspace_id=workspace_id,
            actor_user_id=seeded.manager.client_id,
            now=NOW,
            trigger="test",
        )
        await db_session.commit()
        assert (await active_snapshot(db_session, row_id)).quantity_missing == 6

        await delete_stock_task_assignments(
            _ctx(db_session, seeded, {"client_ids": [assignment_id]})
        )
        await db_session.commit()
        assert (await active_snapshot(db_session, row_id)).quantity_missing == 6
        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# Resolved units are covered (addendum 2026-09-26): the ceiling, the clamp and the
# consistency kind all subtract the snapshot's `quantity_resolved`.
# ---------------------------------------------------------------------------

PROCESSED_API_KEY = "test-missing-processed-key"


async def _resolve_seeded_item(session, seeded, monkeypatch):
    """Scanner processes the seeded item's open assignment (the real webhook)."""
    monkeypatch.setattr(
        settings, "manager_api_key_to_location_tracker_app", PROCESSED_API_KEY
    )
    monkeypatch.setattr(
        settings, "location_tracker_webhook_workspace_id", seeded.workspace.client_id
    )
    body = ('[{"article_number": "%s"}]' % seeded.item.article_number).encode("utf-8")
    result = await process_items_processed(
        ServiceContext(
            identity={},
            incoming_data={"raw_body": body, "headers": {"x-api-key": PROCESSED_API_KEY}},
            session=session,
            now=NOW,
        )
    )
    assert result["results"][0]["outcome"] == "resolved"


async def test_resolved_units_lower_the_ceiling_for_the_route_and_the_checker(
    db_session, monkeypatch
):
    """Requested 10; the seeded item (4) is assigned and then processed by Scanner:
    the row's counters are back to 0, yet only 6 units can be missing."""
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        row_id = await _row_with_version(db_session, seeded)
        await _assign_seeded_item(db_session, seeded, row_id)
        await _resolve_seeded_item(db_session, seeded, monkeypatch)
        snapshot = await active_snapshot(db_session, row_id)
        assert snapshot.quantity_resolved == 4

        result, _ctx_, _ = await _SM(db_session, seeded, row_id, 6)
        assert result["stock_report_item"]["snapshot"]["quantity_missing"] == 6
        # The wire awaiting keeps the processed units even though the row's is 0.
        assert result["stock_report_item"]["snapshot"]["quantity_awaiting"] == 4
        assert result["stock_report_item"]["quantity_awaiting"] == 0

        with pytest.raises(ValidationError) as refused:
            await _SM(db_session, seeded, row_id, 7)
        assert str(refused.value).startswith("STOCK_REPORT_MISSING_EXCEEDS_CEILING:")
        await db_session.rollback()

        await db_session.execute(
            text(
                "UPDATE stock_report_item_snapshots SET quantity_missing = 8 "
                "WHERE stock_report_item_id = :id AND closed_at IS NULL"
            ),
            {"id": row_id},
        )
        await db_session.commit()
        divergences = [
            d
            for d in await compute_stock_report_divergences(db_session, workspace_id)
            if d["kind"] == "missing_over_ceiling"
        ]
        assert [(d["stored"], d["expected"]) for d in divergences] == [(8, 6)]
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def _second_pair(session, seeded, *, quantity=4):
    """A second task + PRIMARY item (a processed item cannot be assigned again on
    its task — the `processed_pairs` refusal). Committed."""
    workspace_id = seeded.workspace.client_id
    suffix = workspace_id[-8:]
    task = Task(
        client_id=f"tsk_mq_{suffix}",
        workspace_id=workspace_id,
        task_scalar_id=2,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=seeded.manager.client_id,
    )
    item = Item(
        client_id=f"itm_mq_{suffix}",
        workspace_id=workspace_id,
        article_number=f"MQ-{suffix}",
        state=ItemStateEnum.PENDING,
        quantity=quantity,
        item_category_id=(
            await session.scalar(
                select(StockReportItem.item_category_id).where(
                    StockReportItem.workspace_id == workspace_id
                )
            )
        ),
        properties={"wood_type": "Teak", "upholstery": "Down"},
    )
    session.add_all([task, item])
    await session.flush()
    session.add(
        TaskItem(
            client_id=f"tim_mq_{suffix}",
            workspace_id=workspace_id,
            task_id=task.client_id,
            item_id=item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=seeded.manager.client_id,
        )
    )
    await session.commit()
    return task.client_id, item.client_id


async def test_creation_clamp_counts_resolved_units_as_covered(db_session, monkeypatch):
    """Requested 10; 4 processed (resolved), missing set to the remaining 6; assigning
    a second item (4 more) leaves 2 uncovered — the clamp must see the 4 resolved
    units, or it would leave missing at 6 (ceiling 6 without them)."""
    seeded = _pin(db_session, await seed_stock_report_workspace(db_session))
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        row_id = await _row_with_version(db_session, seeded)
        await _assign_seeded_item(db_session, seeded, row_id)
        await _resolve_seeded_item(db_session, seeded, monkeypatch)
        await _SM(db_session, seeded, row_id, 6)
        task_id, item_id = await _second_pair(db_session, seeded)

        captured = capture_dispatch(monkeypatch, CREATE_SITE)
        await create_stock_task_assignments(
            _ctx(
                db_session,
                seeded,
                {
                    "entries": [
                        {
                            "stock_report_item_id": row_id,
                            "task_id": task_id,
                            "item_id": item_id,
                            "override_property_mismatch": True,
                        }
                    ]
                },
            )
        )
        await db_session.commit()

        snapshot = await active_snapshot(db_session, row_id)
        assert snapshot.quantity_missing == 2
        assert snapshot.quantity_resolved == 4
        snapshot_event = next(
            e for e in captured if e.event_name == "stock_report_item_snapshot:updated"
        )
        assert snapshot_event.extra["quantity_missing"] == 2
        assert snapshot_event.extra["quantity_resolved"] == 4
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()
