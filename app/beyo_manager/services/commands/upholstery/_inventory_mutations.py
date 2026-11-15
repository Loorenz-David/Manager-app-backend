"""
Private inventory mutation helpers — the single choke point for every change to an
``UpholsteryInventory`` quantity bucket.

All helpers are async functions that take `session: AsyncSession` and explicit parameters.
They call `await session.flush()` when they write, but never commit or begin transactions.
The calling command owns the transaction context.

Ledger contract
---------------
Every writing helper takes a required keyword-only ``movement: InventoryMovementContext`` and
appends exactly one ``upholstery_inventory_history_records`` row (before/after snapshot of all
quantity buckets) via ``_inventory_history.record_movement``, returning that record. The
inventory row is loaded ``FOR UPDATE`` so concurrent movements on the same upholstery serialise
instead of overwriting each other, and so the before-snapshot is truthful.

``tests/unit/services/commands/upholstery/test_inventory_mutation_choke_point_guard.py``
enforces that quantity columns are assigned only here.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementSourceEnum
from beyo_manager.domain.upholstery.condition_evaluation import evaluate_inventory_condition
from beyo_manager.domain.upholstery.enums import (
    InventoryMovementTypeEnum,
    UpholsteryInventoryConditionEnum,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.base.identity import generate_id
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.models.tables.upholstery.upholstery_inventory_history_record import (
    UpholsteryInventoryHistoryRecord,
)
from beyo_manager.services.commands.upholstery._inventory_history import (
    ANOMALY_IN_NEED_CLAMPED,
    BucketSnapshot,
    InventoryMovementContext,
    record_inventory_created,
    record_movement,
)

_ZERO = Decimal("0")


def _reduce_need(current: Decimal | None, quantity: Decimal) -> tuple[Decimal, bool]:
    """in_need − quantity floored at 0. Returns (new value, clamped?).

    A clamp means the projection already held less need than this requirement accounts for —
    recorded as an anomaly on the ledger row instead of silently hidden.
    """
    raw = (current or _ZERO) - quantity
    return (max(_ZERO, raw), raw < _ZERO)


def _reevaluate_condition(inv: UpholsteryInventory) -> None:
    inv.inventory_condition = evaluate_inventory_condition(
        inv.current_stored_amount_meters,
        inv.current_amount_in_need_meters,
        inv.low_stock_threshold_meters,
    )


# ---------------------------------------------------------------------------
# CMD-1 — check_and_inject_need
# ---------------------------------------------------------------------------


async def check_and_inject_need(
    session: AsyncSession,
    workspace_id: str,
    upholstery_id: str,
    quantity: Decimal,
    inject: bool = True,
    *,
    movement: InventoryMovementContext,
) -> dict:
    """
    Load or create the UpholsteryInventory row for (workspace_id, upholstery_id).
    When inject=True: add quantity to current_amount_in_need_meters, record a
    ``need_added`` ledger row (plus ``inventory_created`` when the row was auto-created).
    Always returns: {inventory_id, sufficient, condition, history_record}.
    When inject=False: pure read — no writes, no flush, ``history_record`` is None.
    """
    query = select(UpholsteryInventory).where(
        UpholsteryInventory.workspace_id == workspace_id,
        UpholsteryInventory.upholstery_id == upholstery_id,
        UpholsteryInventory.is_deleted.is_(False),
    )
    if inject:
        query = query.with_for_update().execution_options(populate_existing=True)
    result = await session.execute(query)
    inv = result.scalar_one_or_none()

    if inv is None:
        inv = UpholsteryInventory(
            client_id=generate_id(UpholsteryInventory.CLIENT_ID_PREFIX),
            workspace_id=workspace_id,
            upholstery_id=upholstery_id,
            current_stored_amount_meters=Decimal("0"),
            current_amount_in_need_meters=Decimal("0"),
            current_amount_in_use_meters=Decimal("0"),
            current_amount_ordered_meters=Decimal("0"),
            total_upholstery_used_meters=Decimal("0"),
            total_upholstery_used_inventory_meters=Decimal("0"),
            total_upholstery_used_surplus_meters=Decimal("0"),
            total_upholstery_surplus_meters=Decimal("0"),
            inventory_condition=UpholsteryInventoryConditionEnum.AVAILABLE,
            low_stock_threshold_meters=None,
        )
        session.add(inv)
        if inject:
            await session.flush()
            await record_inventory_created(
                session,
                inv,
                movement=movement.with_refs(
                    requirement_id=None, from_state=None, to_state=None
                ),
            )

    record: UpholsteryInventoryHistoryRecord | None = None
    if inject:
        before = BucketSnapshot.of(inv)
        inv.current_amount_in_need_meters = (
            inv.current_amount_in_need_meters or Decimal("0")
        ) + quantity
        _reevaluate_condition(inv)
        record = await record_movement(
            session,
            inv,
            InventoryMovementTypeEnum.NEED_ADDED,
            before=before,
            movement=movement,
            quantity=quantity,
        )

    net = (inv.current_stored_amount_meters or Decimal("0")) - (
        inv.current_amount_in_need_meters or Decimal("0")
    )
    return {
        "inventory_id": inv.client_id,
        "sufficient": net >= Decimal("0"),
        "condition": inv.inventory_condition,
        "history_record": record,
    }


# ---------------------------------------------------------------------------
# CMD-2 — consume_to_in_use
# ---------------------------------------------------------------------------


async def consume_to_in_use(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    quantity: Decimal,
    *,
    movement: InventoryMovementContext,
) -> UpholsteryInventoryHistoryRecord:
    """
    Move quantity from stored → in_use. Decrements in_need (requirement is now active).
    Guard: raises ValidationError if stored would go negative.
    No condition re-evaluation — net (stored − in_need) is unchanged.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    before = BucketSnapshot.of(inv)
    new_stored = (inv.current_stored_amount_meters or Decimal("0")) - quantity
    if new_stored < Decimal("0"):
        raise ValidationError(
            "Not enough upholstery in stored inventory to start production — "
            "please add more stock before marking in-use."
        )
    inv.current_stored_amount_meters = new_stored
    inv.current_amount_in_use_meters = (
        inv.current_amount_in_use_meters or Decimal("0")
    ) + quantity
    inv.current_amount_in_need_meters, clamped = _reduce_need(
        inv.current_amount_in_need_meters, quantity
    )
    return await record_movement(
        session,
        inv,
        InventoryMovementTypeEnum.RESERVED_FOR_USE,
        before=before,
        movement=movement,
        quantity=quantity,
        anomaly=ANOMALY_IN_NEED_CLAMPED if clamped else None,
    )


# ---------------------------------------------------------------------------
# CMD-3 — finish_in_use
# ---------------------------------------------------------------------------


async def finish_in_use(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    quantity: Decimal,
    source: ItemUpholsteryRequirementSourceEnum,
    *,
    movement: InventoryMovementContext,
) -> UpholsteryInventoryHistoryRecord:
    """
    Decrement in_use by quantity; route to used_inventory or used_surplus totals by source.
    Guard: raises ValidationError if in_use would go negative.
    No condition re-evaluation — net (stored − in_need) is unchanged.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    before = BucketSnapshot.of(inv)
    new_in_use = (inv.current_amount_in_use_meters or Decimal("0")) - quantity
    if new_in_use < Decimal("0"):
        raise ValidationError(
            "Inventory inconsistency: completion quantity exceeds recorded in-use amount."
        )
    inv.current_amount_in_use_meters = new_in_use
    _add_used_totals(inv, quantity, source)
    return await record_movement(
        session,
        inv,
        InventoryMovementTypeEnum.USE_FINISHED,
        before=before,
        movement=movement,
        quantity=quantity,
    )


# ---------------------------------------------------------------------------
# CMD-4 — add_ordered (internal helper)
# ---------------------------------------------------------------------------


async def add_ordered(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    quantity: Decimal,
    *,
    movement: InventoryMovementContext,
) -> UpholsteryInventoryHistoryRecord:
    """
    Increment current_amount_ordered_meters. No condition re-evaluation.
    Called by the external order system via the public command wrapper.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    before = BucketSnapshot.of(inv)
    inv.current_amount_ordered_meters = (
        inv.current_amount_ordered_meters or Decimal("0")
    ) + quantity
    return await record_movement(
        session,
        inv,
        InventoryMovementTypeEnum.ORDER_PLACED,
        before=before,
        movement=movement,
        quantity=quantity,
    )


# ---------------------------------------------------------------------------
# CMD-5 — confirm_ordered_to_stock
# ---------------------------------------------------------------------------


async def confirm_ordered_to_stock(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    quantity: Decimal,
    *,
    movement: InventoryMovementContext,
) -> UpholsteryInventoryHistoryRecord:
    """
    Move quantity from ordered → stored. Re-evaluates condition.
    Guard: raises ValidationError if ordered would go negative.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    before = BucketSnapshot.of(inv)
    new_ordered = (inv.current_amount_ordered_meters or Decimal("0")) - quantity
    if new_ordered < Decimal("0"):
        raise ValidationError(
            "Confirmed quantity exceeds the recorded ordered amount — "
            "verify the stock quantity before confirming."
        )
    inv.current_amount_ordered_meters = new_ordered
    inv.current_stored_amount_meters = (
        inv.current_stored_amount_meters or Decimal("0")
    ) + quantity
    _reevaluate_condition(inv)
    return await record_movement(
        session,
        inv,
        InventoryMovementTypeEnum.ORDER_RECEIVED,
        before=before,
        movement=movement,
        quantity=quantity,
    )


# ---------------------------------------------------------------------------
# CMD-6 — add_stored_surplus
# ---------------------------------------------------------------------------


async def add_stored_surplus(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    quantity: Decimal,
    *,
    movement: InventoryMovementContext,
) -> UpholsteryInventoryHistoryRecord:
    """
    Add offcut/surplus material to stored inventory. Re-evaluates condition.
    Does NOT modify in_need — need decrements only when material moves to in_use (CMD-2).
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    before = BucketSnapshot.of(inv)
    inv.current_stored_amount_meters = (
        inv.current_stored_amount_meters or Decimal("0")
    ) + quantity
    inv.total_upholstery_surplus_meters = (
        inv.total_upholstery_surplus_meters or Decimal("0")
    ) + quantity
    _reevaluate_condition(inv)
    return await record_movement(
        session,
        inv,
        InventoryMovementTypeEnum.SURPLUS_ADDED,
        before=before,
        movement=movement,
        quantity=quantity,
    )


# ---------------------------------------------------------------------------
# CMD-7 — adjust_need
# ---------------------------------------------------------------------------


async def adjust_need(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    delta: Decimal,
    *,
    movement: InventoryMovementContext,
) -> dict:
    """
    Adjust current_amount_in_need_meters by a signed delta and re-evaluate condition.
    delta > 0: need increases (requirement quantity grew).
    delta < 0: need decreases (requirement quantity shrank / requirement cancelled).
    Returns {sufficient, condition, history_record}.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    before = BucketSnapshot.of(inv)
    raw = (inv.current_amount_in_need_meters or Decimal("0")) + delta
    new_in_need = max(Decimal("0"), raw)
    inv.current_amount_in_need_meters = new_in_need
    _reevaluate_condition(inv)
    record = await record_movement(
        session,
        inv,
        InventoryMovementTypeEnum.NEED_ADJUSTED,
        before=before,
        movement=movement,
        quantity=delta,
        anomaly=ANOMALY_IN_NEED_CLAMPED if raw < Decimal("0") else None,
    )
    net = (inv.current_stored_amount_meters or Decimal("0")) - new_in_need
    return {
        "sufficient": net >= Decimal("0"),
        "condition": inv.inventory_condition,
        "history_record": record,
    }


# ---------------------------------------------------------------------------
# CMD-8 — complete_available_direct
# ---------------------------------------------------------------------------


async def complete_available_direct(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    quantity: Decimal,
    source: ItemUpholsteryRequirementSourceEnum,
    *,
    movement: InventoryMovementContext,
) -> UpholsteryInventoryHistoryRecord:
    """
    Atomic combine of consume + finish for AVAILABLE → COMPLETED (skips IN_USE).
    Decrements stored and in_need by same quantity — net unchanged, no condition re-eval.
    Guard: raises ValidationError if stored would go negative.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    before = BucketSnapshot.of(inv)
    new_stored = (inv.current_stored_amount_meters or Decimal("0")) - quantity
    if new_stored < Decimal("0"):
        raise ValidationError(
            "Not enough upholstery in stored inventory to complete directly — "
            "stock may have changed since availability was confirmed."
        )
    inv.current_stored_amount_meters = new_stored
    inv.current_amount_in_need_meters, clamped = _reduce_need(
        inv.current_amount_in_need_meters, quantity
    )
    _add_used_totals(inv, quantity, source)
    return await record_movement(
        session,
        inv,
        InventoryMovementTypeEnum.USED_DIRECT,
        before=before,
        movement=movement,
        quantity=quantity,
        anomaly=ANOMALY_IN_NEED_CLAMPED if clamped else None,
    )


# ---------------------------------------------------------------------------
# CMD-9 — rollback_in_use_to_stored
# ---------------------------------------------------------------------------


async def rollback_in_use_to_stored(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    quantity: Decimal,
    *,
    movement: InventoryMovementContext,
) -> UpholsteryInventoryHistoryRecord:
    """
    Reverse an IN_USE reservation back to stored without touching in_need.

    Used when a currently in-use requirement is force-failed and replaced by a new
    requirement during upholstery swap.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    before = BucketSnapshot.of(inv)
    new_in_use = (inv.current_amount_in_use_meters or Decimal("0")) - quantity
    if new_in_use < Decimal("0"):
        raise ValidationError(
            "Inventory inconsistency: rollback quantity exceeds recorded in-use amount."
        )

    inv.current_amount_in_use_meters = new_in_use
    inv.current_stored_amount_meters = (
        inv.current_stored_amount_meters or Decimal("0")
    ) + quantity
    _reevaluate_condition(inv)
    return await record_movement(
        session,
        inv,
        InventoryMovementTypeEnum.USE_ROLLED_BACK,
        before=before,
        movement=movement,
        quantity=quantity,
    )


# ---------------------------------------------------------------------------
# CMD-10 — set_stored_amount (manual absolute correction)
# ---------------------------------------------------------------------------


async def set_stored_amount(
    session: AsyncSession,
    inv: UpholsteryInventory,
    new_amount: Decimal,
    *,
    movement: InventoryMovementContext,
) -> UpholsteryInventoryHistoryRecord:
    """
    Overwrite current_stored_amount_meters with an absolute value (a manual count) and
    re-evaluate condition. ``inv`` must have been loaded with ``load_inventory_for_update``.
    The ledger row keeps the old value in its before-snapshot.
    """
    before = BucketSnapshot.of(inv)
    inv.current_stored_amount_meters = new_amount
    _reevaluate_condition(inv)
    return await record_movement(
        session,
        inv,
        InventoryMovementTypeEnum.STORED_SET,
        before=before,
        movement=movement,
        quantity=new_amount,
    )


# ---------------------------------------------------------------------------
# Shared internals
# ---------------------------------------------------------------------------


def _add_used_totals(
    inv: UpholsteryInventory,
    quantity: Decimal,
    source: ItemUpholsteryRequirementSourceEnum,
) -> None:
    inv.total_upholstery_used_meters = (
        inv.total_upholstery_used_meters or Decimal("0")
    ) + quantity
    if source == ItemUpholsteryRequirementSourceEnum.INVENTORY:
        inv.total_upholstery_used_inventory_meters = (
            inv.total_upholstery_used_inventory_meters or Decimal("0")
        ) + quantity
    elif source == ItemUpholsteryRequirementSourceEnum.SURPLUS:
        inv.total_upholstery_used_surplus_meters = (
            inv.total_upholstery_used_surplus_meters or Decimal("0")
        ) + quantity


async def load_inventory_for_update(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
) -> UpholsteryInventory:
    """Load the inventory row locked FOR UPDATE with fresh attribute values.

    ``populate_existing`` matters: an inventory already in the identity map would otherwise keep
    the values read before the lock was granted. Autoflush runs first, so pending changes on the
    object are written before they could be overwritten.
    """
    result = await session.execute(
        select(UpholsteryInventory)
        .where(
            UpholsteryInventory.workspace_id == workspace_id,
            UpholsteryInventory.client_id == upholstery_inventory_id,
            UpholsteryInventory.is_deleted.is_(False),
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        raise NotFound("UpholsteryInventory not found.")
    return inv


# Back-compat alias for the private name the helpers used.
_load_inventory = load_inventory_for_update
