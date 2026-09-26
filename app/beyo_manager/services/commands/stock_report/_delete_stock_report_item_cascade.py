"""`cascade_delete_stock_report_item` — MC-16's row-deletion cascade as a
subordinate operation (master plan §6.5, phase 13; intention §5A MC-16, MC-1's
second self-heal trigger and instrument (c), MC-5, MC-17, MC-19).

**One owner in the tree, two callers.** `delete_stock_report_item` (phase 13,
`actor_user_id=ctx.user_id`, `trigger="delete_stock_report_item"`) and phase 13A's
Scanner delete webhook (`actor_user_id=None`, `trigger="stock_demand_deleted"`). It
therefore takes **every stamp value from its arguments and never from `ctx`** — this
module does not import `ctx` and cannot: with `actor_user_id=None` it stamps NULL
everywhere (MC-17), the path 13A exercises.

The caller holds the advisory lock and the tasks → row → active snapshot + its
priority group → assignments locks, and has re-read the row. This operation never
commits and never dispatches; it returns the pending events (`06_commands_local`).
"""

from __future__ import annotations

from sqlalchemy import select, update

from beyo_manager.domain.stock_report.enums import StockReportRepairTargetKindEnum
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.stock_report._events import (
    build_stock_report_item_snapshot_updated_event,
)
from beyo_manager.services.commands.stock_report._ordering import close_priority_gap
from beyo_manager.services.commands.stock_report._remove_assignment import (
    remove_assignment,
)
from beyo_manager.services.commands.stock_report._repair_records import (
    write_repair_record,
)
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent

_COUNTER_COLUMNS = (
    "quantity_in_queue",
    "quantity_in_progress",
    "quantity_awaiting",
)


def build_stock_report_item_deleted_event(*, client_id, workspace_id):
    """MC-19's `stock_report_item:deleted`, `extra` `{}`.

    It is built here rather than in `_events.py` because `_events.py` belongs to
    APPROVED phase 8 and is outside plan 13's §4 perimeter; the inline precedent is
    `apply_stock_demand.py`, which builds `stock_report_item:created` the same way.
    `WorkspaceEvent` is constructed directly, as both `_events.py` builders do
    (`build_workspace_event` wants an object carrying `.client_id`, and this is a
    bare id). Registered with the coordinator in the same act (§9 rule 18).
    """
    return WorkspaceEvent(
        event_name="stock_report_item:deleted",
        client_id=client_id,
        workspace_id=workspace_id,
        extra={},
    )


async def cascade_delete_stock_report_item(
    session, row, *, workspace_id, actor_user_id, now, trigger
):
    events = []

    # ── (i) The assignment loop. Nothing else happens inside it (MC-16: the row is
    # never soft-deleted before its assignments).
    assignments = (
        (
            await session.execute(
                select(StockTaskAssignment)
                .where(
                    StockTaskAssignment.workspace_id == workspace_id,
                    StockTaskAssignment.stock_report_item_id == row.client_id,
                    StockTaskAssignment.is_deleted.is_(False),
                )
                .order_by(StockTaskAssignment.client_id)
            )
        )
        .scalars()
        .all()
    )
    for assignment in assignments:
        events.extend(
            await remove_assignment(
                session,
                assignment,
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                now=now,
                trigger=trigger,
            )
        )

    # ── (ii) MC-1's second self-heal trigger, **once** after the loop ends. Every
    # assignment is gone, so each counter's recomputed value is 0; a non-zero one is
    # drift, repaired with a record, and the deletion proceeds (§14C C39, P36).
    # `stored_before` is a fresh `SELECT`: the loop's guarded Core statements leave
    # the ORM instance stale (§9 rule 3).
    stored_counters = (
        (
            await session.execute(
                select(
                    StockReportItem.quantity_in_queue,
                    StockReportItem.quantity_in_progress,
                    StockReportItem.quantity_awaiting,
                ).where(
                    StockReportItem.workspace_id == workspace_id,
                    StockReportItem.client_id == row.client_id,
                )
            )
        )
        .mappings()
        .one()
    )
    for field in _COUNTER_COLUMNS:
        stored_before = stored_counters[field]
        if stored_before == 0:
            continue
        await session.execute(
            update(StockReportItem)
            .where(
                StockReportItem.workspace_id == workspace_id,
                StockReportItem.client_id == row.client_id,
            )
            .values(**{field: 0})
        )
        await write_repair_record(
            session,
            workspace_id=workspace_id,
            target_kind=StockReportRepairTargetKindEnum.STOCK_REPORT_ITEM,
            target_client_id=row.client_id,
            field=field,
            stored_value=stored_before,
            recomputed_value=0,
            trigger=f"inline:{trigger}",
            created_by_id=None,
            now=now,
        )

    # ── (iii) The active snapshot: close its priority gap, then close it. Since
    # 2026-09-26 the row itself holds no position; the snapshot does. Its position
    # comes from a fresh `SELECT` (§9 rule 3 — the caller's locked instance is not
    # relied on after the shifts above). The closed snapshot keeps its own
    # `priority`/`priority_order` — it is outside every group now (MC-7 "Delete C"),
    # and `close_priority_gap` shifts only orders strictly after it. Its counters are
    # frozen at 0: every assignment is gone by (i). The version stays open.
    snapshot = (
        await session.execute(
            select(
                StockReportItemSnapshot.client_id,
                StockReportItemSnapshot.priority,
                StockReportItemSnapshot.priority_order,
            ).where(
                StockReportItemSnapshot.workspace_id == workspace_id,
                StockReportItemSnapshot.stock_report_item_id == row.client_id,
                StockReportItemSnapshot.closed_at.is_(None),
            )
        )
    ).first()
    if snapshot is not None:
        if snapshot.priority is not None:
            shifted = await close_priority_gap(
                session,
                workspace_id=workspace_id,
                priority=snapshot.priority,
                removed_order=snapshot.priority_order,
            )
            events.extend(
                build_stock_report_item_snapshot_updated_event(
                    client_id=neighbour["client_id"],
                    workspace_id=workspace_id,
                    values=neighbour,
                )
                # The shift statement's RETURNING order is not guaranteed;
                # neighbours follow their new position.
                for neighbour in sorted(shifted, key=lambda r: r["priority_order"])
            )
        await session.execute(
            update(StockReportItemSnapshot)
            .where(
                StockReportItemSnapshot.workspace_id == workspace_id,
                StockReportItemSnapshot.client_id == snapshot.client_id,
            )
            .values(
                closed_at=now,
                quantity_in_queue=0,
                quantity_in_progress=0,
                quantity_awaiting=0,
                updated_at=now,
                updated_by_id=actor_user_id,
            )
        )

    # ── (iv) The two soft-deletes.
    await session.execute(
        update(StockReportItem)
        .where(
            StockReportItem.workspace_id == workspace_id,
            StockReportItem.client_id == row.client_id,
        )
        .values(
            is_deleted=True,
            deleted_at=now,
            deleted_by_id=actor_user_id,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
    )
    # History records get `deleted_*` only — they carry no `updated_*` columns.
    await session.execute(
        update(StockReportHistoryRecord)
        .where(
            StockReportHistoryRecord.workspace_id == workspace_id,
            StockReportHistoryRecord.stock_report_item_id == row.client_id,
            StockReportHistoryRecord.is_deleted.is_(False),
        )
        .values(is_deleted=True, deleted_at=now, deleted_by_id=actor_user_id)
    )

    # No `:updated` for the row itself: the coalescer drops every `:updated` of a
    # row that also carries a `:deleted` in the same request (MC-19).
    events.append(
        build_stock_report_item_deleted_event(
            client_id=row.client_id, workspace_id=workspace_id
        )
    )
    return events
