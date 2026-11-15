"""Backfill reconstructed upholstery inventory history from before the ledger existed.

The ledger (``upholstery_inventory_history_records``) starts at each inventory's
``opening_balance`` row, written by migration ``d7e2a9c4b1f6``. This script adds best-effort
*reconstructed* rows for what happened before that, from data the app already kept:

* ``upholstery_order_history_records``: order placed (ORDERED) and receipts
  (PARTIALLY_RECEIVED / RECEIVED). Per-receipt amounts were never stored. The amount is
  filled in only when the order has exactly one receipt; otherwise it is left empty.
* ``item_upholstery_requirements`` timestamps: ``created_at`` → need added, ``ordered_at``
  → state ORDERED, ``in_use_at`` → reserved for use, ``completed_at`` → used,
  ``failed_at`` → state FAILED. The quantities are the requirement's *current* amount
  (approximate), and the actor is unknown except at creation.

Every row has ``is_reconstructed = true``, ``trigger = 'reconstructed'``, no before/after
snapshot and no parent (causality is unknown). Only events strictly older than the
inventory's opening balance are written, so nothing recorded live is duplicated. Re-running is
safe: each row has a ``reconstruction_key`` and conflicts are skipped.

Dry-run by default; ``--execute`` writes. Undo:
``DELETE FROM upholstery_inventory_history_records WHERE is_reconstructed;``
"""

from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Annotated

import typer
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from beyo_manager.domain.items.enums import (
    ItemUpholsteryRequirementSourceEnum,
    ItemUpholsteryRequirementStateEnum,
)
from beyo_manager.domain.upholstery.enums import (
    InventoryMovementTriggerEnum,
    InventoryMovementTypeEnum,
    UpholsteryOrderStateEnum,
)
from beyo_manager.models.base.identity import generate_id
from beyo_manager.models.database import close_db, get_db_session, init_db
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.upholstery.upholstery_inventory_history_record import (
    UpholsteryInventoryHistoryRecord,
)
from beyo_manager.models.tables.upholstery.upholstery_order import UpholsteryOrder
from beyo_manager.models.tables.upholstery.upholstery_order_history_record import (
    UpholsteryOrderHistoryRecord,
)

app = typer.Typer(add_completion=False, no_args_is_help=True)

_RECEIPT_STATES = {UpholsteryOrderStateEnum.PARTIALLY_RECEIVED, UpholsteryOrderStateEnum.RECEIVED}


@dataclass(frozen=True)
class ReconstructedEvent:
    reconstruction_key: str
    workspace_id: str
    upholstery_inventory_id: str
    movement_type: InventoryMovementTypeEnum
    created_at: datetime
    quantity_meters: Decimal | None = None
    created_by_id: str | None = None
    requirement_id: str | None = None
    item_upholstery_id: str | None = None
    item_id: str | None = None
    task_id: str | None = None
    upholstery_order_id: str | None = None
    to_state: ItemUpholsteryRequirementStateEnum | None = None


async def _baselines(session, workspace_id: str | None) -> dict[str, datetime]:
    """inventory id → opening balance time (the cutoff)."""
    query = select(
        UpholsteryInventoryHistoryRecord.upholstery_inventory_id,
        func.min(UpholsteryInventoryHistoryRecord.created_at),
    ).where(UpholsteryInventoryHistoryRecord.movement_type == InventoryMovementTypeEnum.OPENING_BALANCE)
    if workspace_id is not None:
        query = query.where(UpholsteryInventoryHistoryRecord.workspace_id == workspace_id)
    rows = await session.execute(query.group_by(UpholsteryInventoryHistoryRecord.upholstery_inventory_id))
    return dict(rows.all())


async def _order_events(session, cutoffs: dict[str, datetime]) -> list[ReconstructedEvent]:
    if not cutoffs:
        return []
    rows = (
        await session.execute(
            select(UpholsteryOrderHistoryRecord, UpholsteryOrder)
            .join(UpholsteryOrder, UpholsteryOrder.client_id == UpholsteryOrderHistoryRecord.upholstery_order_id)
            .where(
                UpholsteryOrder.upholstery_inventory_id.in_(list(cutoffs)),
                UpholsteryOrderHistoryRecord.is_deleted.is_(False),
            )
        )
    ).all()
    receipts_per_order = Counter(uoh.upholstery_order_id for uoh, _ in rows if uoh.state in _RECEIPT_STATES)

    events: list[ReconstructedEvent] = []
    for uoh, order in rows:
        cutoff = cutoffs[order.upholstery_inventory_id]
        if uoh.changed_at >= cutoff:
            continue
        common = dict(
            workspace_id=order.workspace_id,
            upholstery_inventory_id=order.upholstery_inventory_id,
            created_at=uoh.changed_at,
            created_by_id=uoh.created_by_id,
            upholstery_order_id=order.client_id,
            reconstruction_key=f"uoh:{uoh.client_id}",
        )
        if uoh.state == UpholsteryOrderStateEnum.ORDERED:
            events.append(
                ReconstructedEvent(
                    movement_type=InventoryMovementTypeEnum.ORDER_PLACED,
                    quantity_meters=uoh.snapshot_order_amount_meters,
                    **common,
                )
            )
        elif uoh.state in _RECEIPT_STATES:
            single_receipt = receipts_per_order[order.client_id] == 1
            events.append(
                ReconstructedEvent(
                    movement_type=InventoryMovementTypeEnum.ORDER_RECEIVED,
                    quantity_meters=order.received_amount_meters if single_receipt else None,
                    **common,
                )
            )
    return events


async def _task_links(session, item_ids: set[str]) -> dict[str, list[tuple[datetime, str]]]:
    """item id → [(task created_at, task id)] sorted ascending."""
    if not item_ids:
        return {}
    rows = await session.execute(
        select(TaskItem.item_id, Task.created_at, Task.client_id)
        .join(Task, Task.client_id == TaskItem.task_id)
        .where(TaskItem.item_id.in_(item_ids))
    )
    links: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    for item_id, created_at, task_id in rows.all():
        links[item_id].append((created_at, task_id))
    for values in links.values():
        values.sort()
    return links


def _task_at(links: list[tuple[datetime, str]], at: datetime) -> str | None:
    """The newest task created at or before ``at``; else the oldest task the item was on."""
    if not links:
        return None
    eligible = [task_id for created_at, task_id in links if created_at <= at]
    return eligible[-1] if eligible else links[0][1]


async def _requirement_events(session, cutoffs: dict[str, datetime]) -> list[ReconstructedEvent]:
    if not cutoffs:
        return []
    rows = (
        await session.execute(
            select(ItemUpholsteryRequirement, ItemUpholstery.item_id)
            .join(ItemUpholstery, ItemUpholstery.client_id == ItemUpholsteryRequirement.item_upholstery_id)
            .where(
                ItemUpholsteryRequirement.upholstery_inventory_id.in_(list(cutoffs)),
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
    ).all()
    links = await _task_links(session, {item_id for _, item_id in rows})

    events: list[ReconstructedEvent] = []
    for req, item_id in rows:
        cutoff = cutoffs[req.upholstery_inventory_id]
        candidates: list[tuple[str, datetime | None, InventoryMovementTypeEnum, Decimal | None, str | None, ItemUpholsteryRequirementStateEnum | None]] = []
        if req.source != ItemUpholsteryRequirementSourceEnum.SURPLUS:
            candidates.append(("created", req.created_at, InventoryMovementTypeEnum.NEED_ADDED, req.amount_meters, req.created_by_id, None))
        candidates += [
            ("ordered", req.ordered_at, InventoryMovementTypeEnum.REQUIREMENT_STATE_CHANGED, req.amount_meters, None, ItemUpholsteryRequirementStateEnum.ORDERED),
            ("in_use", req.in_use_at, InventoryMovementTypeEnum.RESERVED_FOR_USE, req.amount_meters, None, ItemUpholsteryRequirementStateEnum.IN_USE),
            ("completed", req.completed_at, InventoryMovementTypeEnum.USE_FINISHED, req.amount_meters, None, ItemUpholsteryRequirementStateEnum.COMPLETED),
            ("failed", req.failed_at, InventoryMovementTypeEnum.REQUIREMENT_STATE_CHANGED, req.amount_meters, None, ItemUpholsteryRequirementStateEnum.FAILED),
        ]
        for label, at, movement_type, quantity, actor, to_state in candidates:
            if at is None or at >= cutoff:
                continue
            events.append(
                ReconstructedEvent(
                    reconstruction_key=f"iur:{req.client_id}:{label}",
                    workspace_id=req.workspace_id,
                    upholstery_inventory_id=req.upholstery_inventory_id,
                    movement_type=movement_type,
                    created_at=at,
                    quantity_meters=quantity,
                    created_by_id=actor,
                    requirement_id=req.client_id,
                    item_upholstery_id=req.item_upholstery_id,
                    item_id=item_id,
                    task_id=_task_at(links.get(item_id, []), at),
                    to_state=to_state,
                )
            )
    return events


async def collect_reconstructed_events(session, *, workspace_id: str | None = None) -> list[ReconstructedEvent]:
    cutoffs = await _baselines(session, workspace_id)
    events = await _order_events(session, cutoffs) + await _requirement_events(session, cutoffs)
    events.sort(key=lambda e: (e.upholstery_inventory_id, e.created_at, e.reconstruction_key))
    return events


async def apply_reconstructed_events(session, events: list[ReconstructedEvent]) -> int:
    """Insert the events; existing reconstruction keys are skipped. Returns rows inserted."""
    if not events:
        return 0
    table = UpholsteryInventoryHistoryRecord.__table__
    inserted = 0
    for start in range(0, len(events), 500):
        chunk = events[start : start + 500]
        stmt = (
            pg_insert(table)
            .values(
                [
                    {
                        "client_id": generate_id(UpholsteryInventoryHistoryRecord.CLIENT_ID_PREFIX),
                        "workspace_id": e.workspace_id,
                        "upholstery_inventory_id": e.upholstery_inventory_id,
                        "movement_type": e.movement_type,
                        "trigger": InventoryMovementTriggerEnum.RECONSTRUCTED.value,
                        "quantity_meters": e.quantity_meters,
                        "requirement_id": e.requirement_id,
                        "item_upholstery_id": e.item_upholstery_id,
                        "item_id": e.item_id,
                        "task_id": e.task_id,
                        "upholstery_order_id": e.upholstery_order_id,
                        "requirement_to_state": e.to_state,
                        "created_at": e.created_at,
                        "created_by_id": e.created_by_id,
                        "is_reconstructed": True,
                        "reconstruction_key": e.reconstruction_key,
                    }
                    for e in chunk
                ]
            )
            .on_conflict_do_nothing(
                index_elements=["reconstruction_key"],
                index_where=table.c.reconstruction_key.is_not(None),
            )
            .returning(table.c.client_id)
        )
        inserted += len((await session.execute(stmt)).all())
    return inserted


def _print_summary(mode: str, events: list[ReconstructedEvent], inserted: int | None) -> None:
    by_type = Counter(e.movement_type.value for e in events)
    typer.echo(
        "upholstery_inventory_history_backfill | "
        f"mode={mode} inventories={len({e.upholstery_inventory_id for e in events})} "
        f"events={len(events)}" + (f" inserted={inserted}" if inserted is not None else "")
    )
    for movement_type in sorted(by_type):
        typer.echo(f"upholstery_inventory_history_backfill_type | type={movement_type} count={by_type[movement_type]}")


async def backfill_upholstery_inventory_history(session, *, dry_run: bool, workspace_id: str | None) -> int:
    events = await collect_reconstructed_events(session, workspace_id=workspace_id)
    if dry_run:
        _print_summary("dry_run", events, None)
        return 0
    inserted = await apply_reconstructed_events(session, events)
    _print_summary("execute", events, inserted)
    return inserted


async def _run(*, dry_run: bool, workspace_id: str | None) -> None:
    await init_db()
    try:
        async for session in get_db_session():
            await backfill_upholstery_inventory_history(session, dry_run=dry_run, workspace_id=workspace_id)
            if dry_run:
                typer.echo("[dry-run] no changes committed")
                return
            await session.commit()
            typer.echo("upholstery_inventory_history_backfill | committed")
    finally:
        await close_db()


@app.command("backfill-upholstery-inventory-history")
def main(
    dry_run: Annotated[bool, typer.Option("--dry-run/--execute")] = True,
    workspace_id: Annotated[str | None, typer.Option("--workspace-id")] = None,
) -> None:
    """Add reconstructed pre-ledger history rows (orders, requirement lifecycle)."""
    asyncio.run(_run(dry_run=dry_run, workspace_id=workspace_id))


if __name__ == "__main__":
    app()
