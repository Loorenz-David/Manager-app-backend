"""Realtime refresh for upholstery inventories touched by a service run.

``_inventory_history.record_movement`` marks every inventory that received a ledger row in
``session.info``. ``run_service`` calls ``dispatch_touched_inventory_events`` once, after the
outermost service run succeeded (its transaction is committed by then), so the inventory detail
and history timeline refresh for movements whose commands never emitted an inventory event
(requirement lifecycle, step side effect, orders, manual stock edits).
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.services.commands.upholstery._inventory_history import pop_touched_inventories
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent

logger = logging.getLogger(__name__)


async def dispatch_touched_inventory_events(session: AsyncSession) -> None:
    touched = pop_touched_inventories(session)
    if not touched:
        return
    events = [
        WorkspaceEvent(
            event_name="upholstery:inventory-updated",
            client_id=inventory_id,
            workspace_id=workspace_id,
            extra={},
        )
        for workspace_id, inventory_id in sorted(touched)
    ]
    try:
        await event_bus.dispatch(events)
    except Exception:  # never fail a committed request over a refresh hint
        logger.exception(
            "inventory realtime dispatch failed",
            extra={"event_type": "upholstery.inventory_realtime_failed", "count": len(events)},
        )
