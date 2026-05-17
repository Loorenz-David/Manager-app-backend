"""
Skip-and-continue allocation algorithm shared by lifecycle commands.

Used by CMD-4 (mark_ordered), CMD-5 (resolve_after_stock), and CMD-9 (reallocate).
"""

from decimal import Decimal
from datetime import datetime, timezone
from typing import TypedDict

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement


class AllocationResult(TypedDict):
    """Result of skip-and-continue allocation."""
    resolved: list[str]      # item_upholstery_ids marked with target_state
    unresolved: list[str]    # item_upholstery_ids left unchanged


def run_skip_and_continue_allocation(
    candidates: list[ItemUpholsteryRequirement],
    running_pool: Decimal,
    target_state: ItemUpholsteryRequirementStateEnum,
    timestamp_field: str | None,
) -> AllocationResult:
    """
    Iterate candidates in priority order (already sorted by caller).
    For each candidate: if pool >= candidate.amount_meters → assign target_state.
    Skip candidates that don't fit — do NOT stop early.
    
    Args:
        candidates: Sorted requirement list to iterate
        running_pool: Available pool in meters
        target_state: State to assign when a candidate fits
        timestamp_field: Attribute name to stamp (e.g. 'ordered_at'), or None to skip
    
    Returns:
        AllocationResult with resolved and unresolved item_upholstery_ids
    """
    resolved: list[str] = []
    unresolved: list[str] = []
    now = datetime.now(timezone.utc)

    for req in candidates:
        amount = req.amount_meters or Decimal("0")
        if running_pool - amount >= Decimal("0"):
            req.state = target_state
            if timestamp_field:
                setattr(req, timestamp_field, now)
            running_pool -= amount
            resolved.append(req.item_upholstery_id)
        else:
            unresolved.append(req.item_upholstery_id)

    return AllocationResult(resolved=resolved, unresolved=unresolved)
