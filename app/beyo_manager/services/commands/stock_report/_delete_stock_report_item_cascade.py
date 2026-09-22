"""`cascade_delete_stock_report_item` — MC-16's row-deletion cascade as a
subordinate operation (master plan §6.5, phase 13; intention §5A MC-16, MC-1's
second self-heal trigger and instrument (c), MC-5, MC-17, MC-19).

**One owner in the tree, two callers.** `delete_stock_report_item` (phase 13,
`actor_user_id=ctx.user_id`, `trigger="delete_stock_report_item"`) and phase 13A's
Scanner delete webhook (`actor_user_id=None`, `trigger="stock_demand_deleted"`). It
therefore takes **every stamp value from its arguments and never from `ctx`** — this
module does not import `ctx` and cannot: with `actor_user_id=None` it stamps NULL
everywhere (MC-17), the path 13A exercises.

The caller holds the advisory lock and the tasks → row+group → assignments locks,
and has re-read the row. This operation never commits and never dispatches; it
returns the pending events (`06_commands_local`).
"""

from __future__ import annotations

from sqlalchemy import select, update

from beyo_manager.domain.stock_report.enums import StockReportRepairTargetKindEnum
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.stock_report._events import (
    build_stock_report_item_updated_event,
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

    # ── (iii) The gap close, then the two soft-deletes.
    #
    # `priority`/`priority_order` come from a **fresh `SELECT`**, never from the ORM
    # instance loaded at the lock.
    #
    # CORRECTED 2026-09-22 — this comment previously claimed the held instance goes
    # **stale** after the first cascade's shift, and that claim is false. Measured on
    # the production shape (PostgreSQL, asyncpg, `AsyncSession`, SQLAlchemy 2.0.40):
    # `update()` here is ORM-enabled, `synchronize_session="auto"` resolves to
    # `"evaluate"`, and every term of `close_priority_gap`'s WHERE clause evaluates
    # the same way in Python as in SQL **when the caller passes an enum member** —
    # which it does (`priority=position["priority"]`). The identity map is therefore
    # SYNCHRONISED and the read below is **not** load-bearing today. The earlier
    # measurement that said otherwise had passed the plain string `"high"`, and
    # `StockReportItem.priority == "high"` is true in SQL but false in Python.
    #
    # The `SELECT` stays: it is correct defensive code, recorded "unobservable, not
    # unnecessary", and it becomes load-bearing again if a criterion is added that
    # Python cannot evaluate (a SQL function, subquery or JSON operator), if a caller
    # passes a plain string, if the instance is detached or expired rather than live
    # in the identity map, or if SQLAlchemy's default strategy changes. **Do not
    # delete it for being inert.** (§9 rule 3; master plan L-40 as corrected, L-49.)
    position = (
        (
            await session.execute(
                select(
                    StockReportItem.priority, StockReportItem.priority_order
                ).where(
                    StockReportItem.workspace_id == workspace_id,
                    StockReportItem.client_id == row.client_id,
                )
            )
        )
        .mappings()
        .one()
    )
    if position["priority"] is not None:
        shifted = await close_priority_gap(
            session,
            workspace_id=workspace_id,
            priority=position["priority"],
            removed_order=position["priority_order"],
        )
        events.extend(
            build_stock_report_item_updated_event(
                client_id=neighbour["client_id"],
                workspace_id=workspace_id,
                values=neighbour,
            )
            # The shift statement's RETURNING order is not guaranteed; neighbours
            # follow their new position.
            for neighbour in sorted(shifted, key=lambda r: r["priority_order"])
        )

    # The deleted row keeps its own `priority`/`priority_order` — it is outside every
    # group now (MC-7 "Delete C"), and `close_priority_gap` shifts only orders
    # strictly after it.
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
