"""Two-phase sequence-order application.

Reassigning ``sequence_order`` under a UNIQUE(parent, sequence_order) constraint
can transiently collide. Writing negative temporaries first, flushing, then the
final positive values guarantees no intermediate duplicate is ever visible to the
constraint.
"""

from sqlalchemy.ext.asyncio import AsyncSession


async def apply_sequence_orders(
    session: AsyncSession,
    rows_by_id: dict[str, object],
    order_map: dict[str, int],
) -> None:
    if not order_map:
        return
    for client_id, order in order_map.items():
        rows_by_id[client_id].sequence_order = -order
    await session.flush()
    for client_id, order in order_map.items():
        rows_by_id[client_id].sequence_order = order
    await session.flush()
