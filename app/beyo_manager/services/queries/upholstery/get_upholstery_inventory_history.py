"""Query: the change history (ledger timeline) of one upholstery inventory.

Reads ``upholstery_inventory_history_records``: top-level movements newest first, keyset
paginated, each with its nested requirement-state children. Batch-loads actors, tasks, items
and orders. On the first page it also reports whether the inventory's current totals still match
the latest recorded after-snapshot (``integrity``). A mismatch means something changed the totals
outside the recorded paths, which separates app or ops problems from recorded human actions.
"""

from __future__ import annotations

import base64
import binascii
from datetime import datetime
from decimal import Decimal

from sqlalchemy import literal, select, tuple_

from beyo_manager.domain.upholstery.serializers import (
    inventory_history_delta,
    serialize_inventory_buckets,
    serialize_inventory_history_record,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.models.tables.upholstery.upholstery_inventory_history_record import (
    INVENTORY_BUCKET_COLUMNS,
    INVENTORY_BUCKETS,
    UpholsteryInventoryHistoryRecord as Rec,
)
from beyo_manager.models.tables.upholstery.upholstery_order import UpholsteryOrder
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.commands.upholstery._inventory_history import resolve_task_ids_for_items
from beyo_manager.services.context import ServiceContext

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def encode_cursor(created_at: datetime, client_id: str) -> str:
    raw = f"{created_at.isoformat()}|{client_id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        iso, client_id = base64.urlsafe_b64decode(padded.encode()).decode().split("|", 1)
        created_at = datetime.fromisoformat(iso)
    except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
        raise ValidationError("Invalid history cursor.") from exc
    if not client_id or created_at.tzinfo is None:
        raise ValidationError("Invalid history cursor.")
    return created_at, client_id


def _snapshot(rec: Rec, phase: str) -> dict[str, Decimal | None] | None:
    values = {bucket: getattr(rec, f"{phase}_{bucket}_meters") for bucket in INVENTORY_BUCKETS}
    return None if all(v is None for v in values.values()) else values


def _current_buckets(inv: UpholsteryInventory) -> dict[str, Decimal]:
    return {
        bucket: getattr(inv, column) if getattr(inv, column) is not None else Decimal("0")
        for bucket, column in INVENTORY_BUCKET_COLUMNS.items()
    }


def _chain_break(rec: Rec, previous: Rec | None) -> bool:
    """True when this movement's before-snapshot doesn't continue the previous row's after —
    i.e. the totals were changed between the two by something that wrote no ledger row."""
    before = _snapshot(rec, "before")
    if before is None or previous is None:
        return False
    prev_after = _snapshot(previous, "after")
    if prev_after is None:
        return False
    return any((before[b] or Decimal("0")) != (prev_after[b] or Decimal("0")) for b in INVENTORY_BUCKETS)


async def get_upholstery_inventory_history(ctx: ServiceContext) -> dict:
    client_id = ctx.incoming_data.get("client_id")
    params = ctx.query_params or {}
    limit = max(1, min(int(params.get("limit") or DEFAULT_LIMIT), MAX_LIMIT))
    cursor = params.get("cursor")
    session = ctx.session

    inv = (
        await session.execute(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.client_id == client_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
    ).scalar_one_or_none()
    if inv is None:
        raise NotFound("UpholsteryInventory not found.")

    page_query = select(Rec).where(
        Rec.workspace_id == ctx.workspace_id,
        Rec.upholstery_inventory_id == inv.client_id,
        Rec.parent_record_id.is_(None),
    )
    if cursor:
        c_at, c_id = decode_cursor(cursor)
        page_query = page_query.where(tuple_(Rec.created_at, Rec.client_id) < tuple_(literal(c_at), literal(c_id)))
    rows = (
        await session.execute(page_query.order_by(Rec.created_at.desc(), Rec.client_id.desc()).limit(limit + 1))
    ).scalars().all()
    has_more = len(rows) > limit
    page = list(rows[:limit])

    children_by_parent: dict[str, list[Rec]] = {}
    if page:
        child_rows = (
            await session.execute(
                select(Rec)
                .where(Rec.parent_record_id.in_([r.client_id for r in page]))
                .order_by(Rec.created_at.asc(), Rec.client_id.asc())
            )
        ).scalars().all()
        for child in child_rows:
            children_by_parent.setdefault(child.parent_record_id, []).append(child)

    # Chain predecessors (a predecessor can be on the next page, or a different parent).
    known: dict[str, Rec] = {r.client_id: r for r in page}
    missing_prev = {r.previous_record_id for r in page if r.previous_record_id and r.previous_record_id not in known}
    if missing_prev:
        for prev in (await session.execute(select(Rec).where(Rec.client_id.in_(missing_prev)))).scalars().all():
            known[prev.client_id] = prev

    all_rows = page + [c for cs in children_by_parent.values() for c in cs]

    # Task per row: recorded at write time, else inferred from the item now.
    inferred_item_ids = {r.item_id for r in all_rows if r.task_id is None and r.item_id}
    inferred = (
        await resolve_task_ids_for_items(session, ctx.workspace_id, inferred_item_ids) if inferred_item_ids else {}
    )

    def task_for(rec: Rec) -> tuple[str | None, str | None]:
        if rec.task_id:
            return rec.task_id, "recorded"
        if rec.item_id and inferred.get(rec.item_id):
            return inferred[rec.item_id], "inferred"
        return None, None

    task_ids = {t for t in (task_for(r)[0] for r in all_rows) if t}
    user_ids = {r.created_by_id for r in all_rows if r.created_by_id}
    item_ids = {r.item_id for r in all_rows if r.item_id}
    order_ids = {r.upholstery_order_id for r in all_rows if r.upholstery_order_id}

    users = (
        {u.client_id: u for u in (await session.execute(select(User).where(User.client_id.in_(user_ids)))).scalars()}
        if user_ids
        else {}
    )
    tasks = (
        {
            t.client_id: t
            for t in (
                await session.execute(
                    select(Task).where(Task.workspace_id == ctx.workspace_id, Task.client_id.in_(task_ids))
                )
            ).scalars()
        }
        if task_ids
        else {}
    )
    items = (
        {
            i.client_id: i
            for i in (
                await session.execute(
                    select(Item).where(Item.workspace_id == ctx.workspace_id, Item.client_id.in_(item_ids))
                )
            ).scalars()
        }
        if item_ids
        else {}
    )
    orders = (
        {
            o.client_id: o
            for o in (
                await session.execute(
                    select(UpholsteryOrder).where(
                        UpholsteryOrder.workspace_id == ctx.workspace_id,
                        UpholsteryOrder.client_id.in_(order_ids),
                    )
                )
            ).scalars()
        }
        if order_ids
        else {}
    )

    def serialize(rec: Rec, children: list[dict] | None) -> dict:
        task_id, resolution = task_for(rec)
        return serialize_inventory_history_record(
            rec,
            users=users,
            tasks=tasks,
            items=items,
            orders=orders,
            task_id=task_id,
            task_resolution=resolution,
            chain_break=_chain_break(rec, known.get(rec.previous_record_id) if rec.previous_record_id else None),
            children=children,
        )

    records = [
        serialize(rec, [serialize(child, None) for child in children_by_parent.get(rec.client_id, [])])
        for rec in page
    ]

    return {
        "records": records,
        "integrity": await _integrity(session, inv) if not cursor else None,
        "pagination": {
            "limit": limit,
            "has_more": has_more,
            "next_cursor": encode_cursor(page[-1].created_at, page[-1].client_id) if has_more and page else None,
        },
    }


async def _integrity(session, inv: UpholsteryInventory) -> dict:
    """Compare the inventory's current totals with the latest recorded after-snapshot.

    ``drift`` = current − expected. ``pointer_matches`` checks that the inventory's
    ``latest_projection_history_id`` points at the newest snapshot-bearing row.
    """
    current = _current_buckets(inv)
    newest = (
        await session.execute(
            select(Rec)
            .where(
                Rec.upholstery_inventory_id == inv.client_id,
                Rec.is_reconstructed.is_(False),
                Rec.after_stored_meters.is_not(None),
            )
            .order_by(Rec.created_at.desc(), Rec.client_id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    latest = None
    if inv.latest_projection_history_id:
        latest = (
            newest
            if newest is not None and newest.client_id == inv.latest_projection_history_id
            else await session.get(Rec, inv.latest_projection_history_id)
        )
    expected = _snapshot(latest, "after") if latest is not None else None
    if expected is None:
        return {
            "status": "no_baseline",
            "latest_record_id": None,
            "pointer_matches": False,
            "expected": None,
            "current": serialize_inventory_buckets(current),
            "drift": None,
        }
    drift = inventory_history_delta(expected, current)
    return {
        "status": "drift" if any(v != 0 for v in drift.values()) else "consistent",
        "latest_record_id": latest.client_id,
        "pointer_matches": newest is not None and newest.client_id == latest.client_id,
        "expected": serialize_inventory_buckets(expected),
        "current": serialize_inventory_buckets(current),
        "drift": serialize_inventory_buckets(drift),
    }
