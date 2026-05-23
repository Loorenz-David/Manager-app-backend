"""
Private inventory mutation helpers.

All helpers are async functions that take `session: AsyncSession` and explicit parameters.
They call `await session.flush()` when they write, but never commit or begin transactions.
The calling command owns the transaction context.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementSourceEnum
from beyo_manager.domain.upholstery.condition_evaluation import evaluate_inventory_condition
from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.base.identity import generate_id
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory


# ---------------------------------------------------------------------------
# CMD-1 — check_and_inject_need
# ---------------------------------------------------------------------------


async def check_and_inject_need(
    session: AsyncSession,
    workspace_id: str,
    upholstery_id: str,
    quantity: Decimal,
    inject: bool = True,
) -> dict:
    """
    Load or create the UpholsteryInventory row for (workspace_id, upholstery_id).
    When inject=True: add quantity to current_amount_in_need_meters and flush.
    Always returns: {inventory_id, sufficient, condition}.
    When inject=False: pure read — no writes, no flush.
    """
    result = await session.execute(
        select(UpholsteryInventory).where(
            UpholsteryInventory.workspace_id == workspace_id,
            UpholsteryInventory.upholstery_id == upholstery_id,
            UpholsteryInventory.is_deleted.is_(False),
        )
    )
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

    if inject:
        inv.current_amount_in_need_meters = (
            inv.current_amount_in_need_meters or Decimal("0")
        ) + quantity
        inv.inventory_condition = evaluate_inventory_condition(
            inv.current_stored_amount_meters,
            inv.current_amount_in_need_meters,
            inv.low_stock_threshold_meters,
        )
        await session.flush()

    net = (inv.current_stored_amount_meters or Decimal("0")) - (
        inv.current_amount_in_need_meters or Decimal("0")
    )
    return {
        "inventory_id": inv.client_id,
        "sufficient": net >= Decimal("0"),
        "condition": inv.inventory_condition,
    }


# ---------------------------------------------------------------------------
# CMD-2 — consume_to_in_use
# ---------------------------------------------------------------------------


async def consume_to_in_use(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    quantity: Decimal,
) -> None:
    """
    Move quantity from stored → in_use. Decrements in_need (requirement is now active).
    Guard: raises ValidationError if stored would go negative.
    No condition re-evaluation — net (stored − in_need) is unchanged.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
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
    inv.current_amount_in_need_meters = max(
        Decimal("0"),
        (inv.current_amount_in_need_meters or Decimal("0")) - quantity,
    )
    await session.flush()


# ---------------------------------------------------------------------------
# CMD-3 — finish_in_use
# ---------------------------------------------------------------------------


async def finish_in_use(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    quantity: Decimal,
    source: ItemUpholsteryRequirementSourceEnum,
) -> None:
    """
    Decrement in_use by quantity; route to used_inventory or used_surplus totals by source.
    Guard: raises ValidationError if in_use would go negative.
    No condition re-evaluation — net (stored − in_need) is unchanged.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    new_in_use = (inv.current_amount_in_use_meters or Decimal("0")) - quantity
    if new_in_use < Decimal("0"):
        raise ValidationError(
            "Inventory inconsistency: completion quantity exceeds recorded in-use amount."
        )
    inv.current_amount_in_use_meters = new_in_use
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
    await session.flush()


# ---------------------------------------------------------------------------
# CMD-4 — add_ordered (internal helper)
# ---------------------------------------------------------------------------


async def add_ordered(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    quantity: Decimal,
) -> None:
    """
    Increment current_amount_ordered_meters. No condition re-evaluation.
    Called by the external order system via the public command wrapper.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    inv.current_amount_ordered_meters = (
        inv.current_amount_ordered_meters or Decimal("0")
    ) + quantity
    await session.flush()


# ---------------------------------------------------------------------------
# CMD-5 — confirm_ordered_to_stock
# ---------------------------------------------------------------------------


async def confirm_ordered_to_stock(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    quantity: Decimal,
) -> None:
    """
    Move quantity from ordered → stored. Re-evaluates condition.
    Guard: raises ValidationError if ordered would go negative.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
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
    inv.inventory_condition = evaluate_inventory_condition(
        inv.current_stored_amount_meters,
        inv.current_amount_in_need_meters,
        inv.low_stock_threshold_meters,
    )
    await session.flush()


# ---------------------------------------------------------------------------
# CMD-6 — add_stored_surplus
# ---------------------------------------------------------------------------


async def add_stored_surplus(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    quantity: Decimal,
) -> None:
    """
    Add offcut/surplus material to stored inventory. Re-evaluates condition.
    Does NOT modify in_need — need decrements only when material moves to in_use (CMD-2).
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    inv.current_stored_amount_meters = (
        inv.current_stored_amount_meters or Decimal("0")
    ) + quantity
    inv.total_upholstery_surplus_meters = (
        inv.total_upholstery_surplus_meters or Decimal("0")
    ) + quantity
    inv.inventory_condition = evaluate_inventory_condition(
        inv.current_stored_amount_meters,
        inv.current_amount_in_need_meters,
        inv.low_stock_threshold_meters,
    )
    await session.flush()


# ---------------------------------------------------------------------------
# CMD-7 — adjust_need
# ---------------------------------------------------------------------------


async def adjust_need(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    delta: Decimal,
) -> dict:
    """
    Adjust current_amount_in_need_meters by a signed delta and re-evaluate condition.
    delta > 0: need increases (requirement quantity grew).
    delta < 0: need decreases (requirement quantity shrank).
    Returns {sufficient, condition}.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    new_in_need = max(
        Decimal("0"),
        (inv.current_amount_in_need_meters or Decimal("0")) + delta,
    )
    inv.current_amount_in_need_meters = new_in_need
    inv.inventory_condition = evaluate_inventory_condition(
        inv.current_stored_amount_meters,
        inv.current_amount_in_need_meters,
        inv.low_stock_threshold_meters,
    )
    await session.flush()
    net = (inv.current_stored_amount_meters or Decimal("0")) - new_in_need
    return {
        "sufficient": net >= Decimal("0"),
        "condition": inv.inventory_condition,
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
) -> None:
    """
    Atomic combine of consume + finish for AVAILABLE → COMPLETED (skips IN_USE).
    Decrements stored and in_need by same quantity — net unchanged, no condition re-eval.
    Guard: raises ValidationError if stored would go negative.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    new_stored = (inv.current_stored_amount_meters or Decimal("0")) - quantity
    if new_stored < Decimal("0"):
        raise ValidationError(
            "Not enough upholstery in stored inventory to complete directly — "
            "stock may have changed since availability was confirmed."
        )
    inv.current_stored_amount_meters = new_stored
    inv.current_amount_in_need_meters = max(
        Decimal("0"),
        (inv.current_amount_in_need_meters or Decimal("0")) - quantity,
    )
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
    await session.flush()


# ---------------------------------------------------------------------------
# Private loader — shared by all mutation helpers
# ---------------------------------------------------------------------------


async def _load_inventory(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
) -> UpholsteryInventory:
    """Load inventory with guard for not found / workspace mismatch."""
    result = await session.execute(
        select(UpholsteryInventory).where(
            UpholsteryInventory.workspace_id == workspace_id,
            UpholsteryInventory.client_id == upholstery_inventory_id,
            UpholsteryInventory.is_deleted.is_(False),
        )
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        raise NotFound("UpholsteryInventory not found.")
    return inv
