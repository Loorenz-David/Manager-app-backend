"""
Upholstery inventory ledger recorder — the only writer of
``upholstery_inventory_history_records`` rows (besides the migration baseline and the
reconstruction backfill script).

How it is used
--------------
Every quantity helper in ``_inventory_mutations.py`` takes a required keyword
``movement: InventoryMovementContext`` and ends with ``record_movement(...)``. Callers never
insert ledger rows themselves, so a nested command (e.g. ``ensure_item_upholstery_in_session``
→ ``update_requirement_quantity``) still writes exactly one row per helper call.

Requirement state changes caused by a movement (allocation promotions / demotions) are
recorded as child rows via ``record_requirement_transitions`` with ``parent_record_id`` set to
the movement. State-only commands write a zero-delta ``allocation_run`` parent first.

Transactions
------------
Like the mutation helpers, this module flushes but never commits: ledger rows commit or roll
back together with the quantity change they describe. Rows are immutable once committed;
*inside* the writing transaction a caller may still patch ``requirement_to_state`` on a
returned record when the requirement's outcome depends on the helper result
(AVAILABLE vs NEEDS_ORDERING after ``check_and_inject_need`` / ``adjust_need``).

Correlation
-----------
``correlation_id_for(session)`` hands out one id per session scope; ``run_service`` resets the
scope when the outermost service run ends (``reset_movement_scope``), so one request = one
correlation id.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.upholstery.enums import (
    InventoryMovementTriggerEnum,
    InventoryMovementTypeEnum,
)
from beyo_manager.models.base.identity import generate_id
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.models.tables.upholstery.upholstery_inventory_history_record import (
    INVENTORY_BUCKET_COLUMNS,
    INVENTORY_BUCKETS,
    UpholsteryInventoryHistoryRecord,
)

if TYPE_CHECKING:
    from beyo_manager.models.tables.items.item_upholstery_requirement import (
        ItemUpholsteryRequirement,
    )
    from beyo_manager.services.context import ServiceContext


ANOMALY_IN_NEED_CLAMPED = "in_need_clamped_at_zero"
DETAILS_ID_CAP = 50

_CORRELATION_KEY = "uih_correlation_id"
_TOUCHED_KEY = "uih_touched"
_ITEM_CACHE_KEY = "uih_item_by_iup"
_TASK_CACHE_KEY = "uih_task_by_item"

_ZERO = Decimal("0")


# ---------------------------------------------------------------------------
# Context passed into every mutation helper
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InventoryMovementContext:
    """Who/why/what-for of one inventory movement. Immutable; derive variants with helpers."""

    actor_id: str | None
    username_snapshot: str | None
    trigger: InventoryMovementTriggerEnum
    correlation_id: str
    requirement_id: str | None = None
    item_upholstery_id: str | None = None
    item_id: str | None = None
    task_id: str | None = None
    task_step_id: str | None = None
    upholstery_order_id: str | None = None
    from_state: ItemUpholsteryRequirementStateEnum | None = None
    to_state: ItemUpholsteryRequirementStateEnum | None = None
    note: str | None = None

    @classmethod
    def from_service(
        cls,
        ctx: ServiceContext,
        trigger: InventoryMovementTriggerEnum,
        **refs: Any,
    ) -> InventoryMovementContext:
        # ServiceContext.user_id / username default to "" — never write "" into the users FK.
        return cls(
            actor_id=ctx.user_id or None,
            username_snapshot=ctx.username or None,
            trigger=trigger,
            correlation_id=correlation_id_for(ctx.session),
            **refs,
        )

    @classmethod
    def system(
        cls,
        session: AsyncSession,
        trigger: InventoryMovementTriggerEnum,
        *,
        actor_id: str | None = None,
        username: str | None = None,
        **refs: Any,
    ) -> InventoryMovementContext:
        """For scripts / workers that run outside ``run_service``."""
        return cls(
            actor_id=actor_id or None,
            username_snapshot=username or None,
            trigger=trigger,
            correlation_id=correlation_id_for(session),
            **refs,
        )

    def with_refs(self, **refs: Any) -> InventoryMovementContext:
        return dataclasses.replace(self, **refs)

    def for_requirement(
        self,
        requirement: ItemUpholsteryRequirement,
        *,
        to_state: ItemUpholsteryRequirementStateEnum | None = None,
    ) -> InventoryMovementContext:
        """Scope to one requirement; ``from_state`` is the requirement's state right now."""
        return dataclasses.replace(
            self,
            requirement_id=requirement.client_id,
            item_upholstery_id=requirement.item_upholstery_id,
            from_state=requirement.state,
            to_state=to_state,
        )


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BucketSnapshot:
    stored: Decimal
    in_use: Decimal
    in_need: Decimal
    ordered: Decimal
    total_used: Decimal
    total_used_inventory: Decimal
    total_used_surplus: Decimal
    total_surplus: Decimal

    @classmethod
    def of(cls, inv: UpholsteryInventory) -> BucketSnapshot:
        return cls(
            **{
                bucket: getattr(inv, column) if getattr(inv, column) is not None else _ZERO
                for bucket, column in INVENTORY_BUCKET_COLUMNS.items()
            }
        )

    def as_dict(self) -> dict[str, Decimal]:
        return {bucket: getattr(self, bucket) for bucket in INVENTORY_BUCKETS}


@dataclass(frozen=True, slots=True)
class RequirementTransition:
    requirement: ItemUpholsteryRequirement
    from_state: ItemUpholsteryRequirementStateEnum | None
    to_state: ItemUpholsteryRequirementStateEnum | None


class RequirementStateTracker:
    """Diff requirement states around code that changes them (allocation), non-invasively."""

    def __init__(self, states: dict[str, ItemUpholsteryRequirementStateEnum | None]) -> None:
        self._states = states

    @classmethod
    def capture(cls, requirements: Iterable[ItemUpholsteryRequirement]) -> RequirementStateTracker:
        return cls({req.client_id: req.state for req in requirements})

    def add(self, requirements: Iterable[ItemUpholsteryRequirement]) -> None:
        """Capture requirements loaded later; already-captured ones keep their first state."""
        for req in requirements:
            self._states.setdefault(req.client_id, req.state)

    def transitions(
        self, requirements: Iterable[ItemUpholsteryRequirement]
    ) -> list[RequirementTransition]:
        """Captured requirements whose state differs now. Uncaptured ones are ignored —
        record a creation explicitly with ``RequirementTransition(from_state=None, ...)``."""
        out: list[RequirementTransition] = []
        seen: set[str] = set()
        for req in requirements:
            if req.client_id in seen or req.client_id not in self._states:
                continue
            seen.add(req.client_id)
            before = self._states[req.client_id]
            if before == req.state:
                continue
            out.append(RequirementTransition(requirement=req, from_state=before, to_state=req.state))
        return out


# ---------------------------------------------------------------------------
# Session-scoped bookkeeping
# ---------------------------------------------------------------------------


def correlation_id_for(session: AsyncSession) -> str:
    return session.info.setdefault(_CORRELATION_KEY, generate_id("ucor"))


def pop_touched_inventories(session: AsyncSession) -> set[tuple[str, str]]:
    """(workspace_id, inventory_id) pairs that got ledger rows since the last pop."""
    return session.info.pop(_TOUCHED_KEY, set())


def reset_movement_scope(session: AsyncSession) -> None:
    for key in (_CORRELATION_KEY, _TOUCHED_KEY, _ITEM_CACHE_KEY, _TASK_CACHE_KEY):
        session.info.pop(key, None)


# ---------------------------------------------------------------------------
# Task / item resolution (write time; the read side has a fallback)
# ---------------------------------------------------------------------------


async def resolve_item_ids_for_item_upholsteries(
    session: AsyncSession, item_upholstery_ids: Iterable[str]
) -> dict[str, str]:
    cache: dict[str, str] = session.info.setdefault(_ITEM_CACHE_KEY, {})
    missing = {i for i in item_upholstery_ids if i and i not in cache}
    if missing:
        rows = await session.execute(
            select(ItemUpholstery.client_id, ItemUpholstery.item_id).where(
                ItemUpholstery.client_id.in_(missing)
            )
        )
        for iup_id, item_id in rows.all():
            cache[iup_id] = item_id
    return {i: cache[i] for i in item_upholstery_ids if i in cache}


async def resolve_task_ids_for_items(
    session: AsyncSession, workspace_id: str, item_ids: Iterable[str]
) -> dict[str, str | None]:
    """item_id → the task it currently belongs to.

    Preference: an active link (``removed_at IS NULL``) to a non-deleted task, newest link first;
    else the newest link of any kind. ``None`` when the item was never on a task.
    """
    cache: dict[str, str | None] = session.info.setdefault(_TASK_CACHE_KEY, {})
    missing = {i for i in item_ids if i and i not in cache}
    if missing:
        rows = await session.execute(
            select(TaskItem.item_id, TaskItem.task_id, TaskItem.removed_at, Task.is_deleted, TaskItem.created_at)
            .join(Task, Task.client_id == TaskItem.task_id)
            .where(TaskItem.workspace_id == workspace_id, TaskItem.item_id.in_(missing))
        )
        best: dict[str, tuple[tuple, str]] = {}
        for item_id, task_id, removed_at, task_deleted, linked_at in rows.all():
            rank = (removed_at is None, not task_deleted, linked_at)
            if item_id not in best or rank > best[item_id][0]:
                best[item_id] = (rank, task_id)
        for item_id in missing:
            cache[item_id] = best[item_id][1] if item_id in best else None
    return {i: cache.get(i) for i in item_ids if i}


async def _resolve_refs(
    session: AsyncSession, workspace_id: str, movement: InventoryMovementContext
) -> tuple[str | None, str | None]:
    """(item_id, task_id) for a movement; explicit values win."""
    item_id = movement.item_id
    if item_id is None and movement.item_upholstery_id:
        item_id = (await resolve_item_ids_for_item_upholsteries(session, [movement.item_upholstery_id])).get(
            movement.item_upholstery_id
        )
    task_id = movement.task_id
    if task_id is None and item_id:
        task_id = (await resolve_task_ids_for_items(session, workspace_id, [item_id])).get(item_id)
    return item_id, task_id


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def _apply_snapshot(rec: UpholsteryInventoryHistoryRecord, phase: str, snap: BucketSnapshot | None) -> None:
    for bucket in INVENTORY_BUCKETS:
        setattr(rec, f"{phase}_{bucket}_meters", None if snap is None else getattr(snap, bucket))


def _mark_touched(session: AsyncSession, inv: UpholsteryInventory) -> None:
    session.info.setdefault(_TOUCHED_KEY, set()).add((inv.workspace_id, inv.client_id))


def _base_record(
    inv: UpholsteryInventory,
    movement_type: InventoryMovementTypeEnum,
    movement: InventoryMovementContext,
    *,
    item_id: str | None,
    task_id: str | None,
) -> UpholsteryInventoryHistoryRecord:
    return UpholsteryInventoryHistoryRecord(
        client_id=generate_id(UpholsteryInventoryHistoryRecord.CLIENT_ID_PREFIX),
        workspace_id=inv.workspace_id,
        upholstery_inventory_id=inv.client_id,
        movement_type=movement_type,
        trigger=movement.trigger.value,
        correlation_id=movement.correlation_id,
        requirement_id=movement.requirement_id,
        item_upholstery_id=movement.item_upholstery_id,
        item_id=item_id,
        task_id=task_id,
        task_step_id=movement.task_step_id,
        upholstery_order_id=movement.upholstery_order_id,
        requirement_from_state=movement.from_state,
        requirement_to_state=movement.to_state,
        note=movement.note,
        created_by_id=movement.actor_id,
        username_snapshot=movement.username_snapshot,
        created_at=datetime.now(timezone.utc),
        is_reconstructed=False,
    )


async def record_movement(
    session: AsyncSession,
    inv: UpholsteryInventory,
    movement_type: InventoryMovementTypeEnum,
    *,
    before: BucketSnapshot | None,
    movement: InventoryMovementContext,
    quantity: Decimal | None,
    anomaly: str | None = None,
    details: dict | None = None,
) -> UpholsteryInventoryHistoryRecord:
    """Append one movement row for ``inv`` (already mutated in memory) and advance the chain."""
    if inv in session.new:
        await session.flush()  # inventory INSERT must precede the ledger INSERT (FK)
    item_id, task_id = await _resolve_refs(session, inv.workspace_id, movement)
    rec = _base_record(inv, movement_type, movement, item_id=item_id, task_id=task_id)
    rec.previous_record_id = inv.latest_projection_history_id
    rec.quantity_meters = quantity
    rec.anomaly = anomaly
    rec.details = details
    _apply_snapshot(rec, "before", before)
    _apply_snapshot(rec, "after", BucketSnapshot.of(inv))
    session.add(rec)
    inv.latest_projection_history_id = rec.client_id
    _mark_touched(session, inv)
    await session.flush()
    return rec


async def record_inventory_created(
    session: AsyncSession,
    inv: UpholsteryInventory,
    *,
    movement: InventoryMovementContext,
) -> UpholsteryInventoryHistoryRecord:
    """First row of a new inventory: no before-snapshot, after = its initial values."""
    return await record_movement(
        session,
        inv,
        InventoryMovementTypeEnum.INVENTORY_CREATED,
        before=None,
        movement=movement,
        quantity=None,
    )


async def record_requirement_transitions(
    session: AsyncSession,
    *,
    parent: UpholsteryInventoryHistoryRecord,
    transitions: Iterable[RequirementTransition],
    movement: InventoryMovementContext,
) -> list[UpholsteryInventoryHistoryRecord]:
    """One child row per requirement state change, nested under ``parent``. No snapshots
    (allocation never moves meters) and no chain advance."""
    transitions = list(transitions)
    if not transitions:
        return []
    iup_ids = [t.requirement.item_upholstery_id for t in transitions if t.requirement.item_upholstery_id]
    item_by_iup = await resolve_item_ids_for_item_upholsteries(session, iup_ids)
    task_by_item = await resolve_task_ids_for_items(session, parent.workspace_id, set(item_by_iup.values()))

    children: list[UpholsteryInventoryHistoryRecord] = []
    for t in transitions:
        req = t.requirement
        item_id = item_by_iup.get(req.item_upholstery_id)
        child = UpholsteryInventoryHistoryRecord(
            client_id=generate_id(UpholsteryInventoryHistoryRecord.CLIENT_ID_PREFIX),
            workspace_id=parent.workspace_id,
            upholstery_inventory_id=parent.upholstery_inventory_id,
            movement_type=InventoryMovementTypeEnum.REQUIREMENT_STATE_CHANGED,
            trigger=movement.trigger.value,
            correlation_id=movement.correlation_id,
            parent_record_id=parent.client_id,
            quantity_meters=req.amount_meters,
            requirement_id=req.client_id,
            item_upholstery_id=req.item_upholstery_id,
            item_id=item_id,
            task_id=task_by_item.get(item_id) if item_id else None,
            upholstery_order_id=movement.upholstery_order_id,
            requirement_from_state=t.from_state,
            requirement_to_state=t.to_state,
            created_by_id=movement.actor_id,
            username_snapshot=movement.username_snapshot,
            created_at=datetime.now(timezone.utc),
            is_reconstructed=False,
        )
        session.add(child)
        children.append(child)
    await session.flush()
    return children


async def record_allocation_run(
    session: AsyncSession,
    inv: UpholsteryInventory,
    *,
    movement: InventoryMovementContext,
    transitions: Iterable[RequirementTransition],
    details: dict | None = None,
) -> UpholsteryInventoryHistoryRecord | None:
    """Zero-delta parent for state-only commands, plus its children.

    Writes nothing when no requirement changed state — a no-op allocation is not history.
    """
    transitions = list(transitions)
    if not transitions:
        return None
    snap = BucketSnapshot.of(inv)
    parent = await record_movement(
        session,
        inv,
        InventoryMovementTypeEnum.ALLOCATION_RUN,
        before=snap,
        movement=movement,
        quantity=None,
        details=details,
    )
    await record_requirement_transitions(session, parent=parent, transitions=transitions, movement=movement)
    return parent


def allocation_details(
    *,
    pool_meters: Decimal | None = None,
    resolved: Iterable[ItemUpholsteryRequirement] = (),
    unresolved: Iterable[ItemUpholsteryRequirement] = (),
    target_state: ItemUpholsteryRequirementStateEnum | None = None,
) -> dict:
    """JSON-safe allocation facts for a parent row's ``details`` ("why did/didn't a task flip")."""
    resolved_ids = [r.client_id for r in resolved]
    unresolved_ids = [r.client_id for r in unresolved]
    out: dict[str, Any] = {
        "resolved_count": len(resolved_ids),
        "unresolved_count": len(unresolved_ids),
        "resolved_requirement_ids": resolved_ids[:DETAILS_ID_CAP],
        "unresolved_requirement_ids": unresolved_ids[:DETAILS_ID_CAP],
    }
    if pool_meters is not None:
        out["pool_meters"] = str(pool_meters)
    if target_state is not None:
        out["target_state"] = target_state.value
    return out


async def record_allocation_outcome(
    session: AsyncSession,
    *,
    parent: UpholsteryInventoryHistoryRecord,
    movement: InventoryMovementContext,
    inventory: UpholsteryInventory,
    candidates: list[ItemUpholsteryRequirement],
    tracker: RequirementStateTracker,
    target_state: ItemUpholsteryRequirementStateEnum,
    mode: str,
) -> list[UpholsteryInventoryHistoryRecord]:
    """After a pooled allocation that followed ``parent``'s movement: nest the requirement state
    changes under it and attach the allocation facts (pool, resolved / unresolved) as details —
    recorded even when nothing changed, because "why didn't my task flip" needs that evidence."""
    from beyo_manager.services.commands.upholstery._pooled_requirement_allocation import (
        calculate_pooled_requirement_pool,
    )

    children = await record_requirement_transitions(
        session, parent=parent, transitions=tracker.transitions(candidates), movement=movement
    )
    parent.details = allocation_details(
        pool_meters=calculate_pooled_requirement_pool(inventory, list(candidates), mode)
        if candidates
        else None,
        resolved=[r for r in candidates if r.state == target_state],
        unresolved=[r for r in candidates if r.state != target_state],
        target_state=target_state,
    )
    return children


async def record_allocation_runs(
    session: AsyncSession,
    *,
    workspace_id: str,
    movement: InventoryMovementContext,
    tracker: RequirementStateTracker,
    candidates: Iterable[ItemUpholsteryRequirement],
    target_state: ItemUpholsteryRequirementStateEnum | None = None,
    pool_meters: Decimal | None = None,
) -> list[UpholsteryInventoryHistoryRecord]:
    """For state-only commands (no meters move): one zero-delta ``allocation_run`` parent per
    inventory whose requirements changed state, with the changes nested under it."""
    from beyo_manager.services.commands.upholstery._inventory_mutations import (
        load_inventory_for_update,
    )

    candidates = list(candidates)
    by_inventory: dict[str, list[RequirementTransition]] = {}
    for t in tracker.transitions(candidates):
        inv_id = t.requirement.upholstery_inventory_id
        if inv_id:
            by_inventory.setdefault(inv_id, []).append(t)

    parents: list[UpholsteryInventoryHistoryRecord] = []
    for inv_id in sorted(by_inventory):
        inv = await load_inventory_for_update(session, workspace_id, inv_id)
        inv_candidates = [c for c in candidates if c.upholstery_inventory_id == inv_id]
        details = allocation_details(
            pool_meters=pool_meters,
            resolved=[c for c in inv_candidates if target_state is not None and c.state == target_state],
            unresolved=[c for c in inv_candidates if target_state is not None and c.state != target_state],
            target_state=target_state,
        )
        parent = await record_allocation_run(
            session, inv, movement=movement, transitions=by_inventory[inv_id], details=details
        )
        if parent is not None:
            parents.append(parent)
    return parents
