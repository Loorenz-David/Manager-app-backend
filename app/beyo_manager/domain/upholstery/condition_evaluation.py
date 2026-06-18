"""
Pure function for evaluating upholstery inventory condition.

Invariants:
- net = stored − in_need
- If net <= 0 → OUT_OF_STOCK
- If threshold is set and net <= threshold → LOW_STOCK
- Otherwise → AVAILABLE
- Null fields treated as zero
- No hysteresis
"""

from decimal import Decimal

from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum


def evaluate_inventory_condition(
    stored: Decimal | None,
    in_need: Decimal | None,
    threshold: Decimal | None,
) -> UpholsteryInventoryConditionEnum:
    """
    Evaluate inventory condition based on stored amount, amount in need, and low-stock threshold.
    
    Args:
        stored: Current stored amount in meters (null treated as 0)
        in_need: Current amount in need in meters (null treated as 0)
        threshold: Low-stock threshold in meters (null disables low-stock check)
    
    Returns:
        UpholsteryInventoryConditionEnum (OUT_OF_STOCK, LOW_STOCK, or AVAILABLE)
    """
    safe_stored = stored or Decimal("0")
    safe_need = in_need or Decimal("0")
    net = safe_stored - safe_need

    if net <= Decimal("0"):
        return UpholsteryInventoryConditionEnum.OUT_OF_STOCK

    if threshold is not None and net <= threshold:
        return UpholsteryInventoryConditionEnum.LOW_STOCK

    return UpholsteryInventoryConditionEnum.AVAILABLE
