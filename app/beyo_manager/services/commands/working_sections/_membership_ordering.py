from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.working_sections.working_section_membership import (
    WorkingSectionMembership,
)


async def next_sort_order(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
) -> int:
    """Append cursor for a user's active section ordering.

    Returns ``max(sort_order) + 1`` over the user's active memberships in the
    workspace, or ``0`` when the user has no active memberships. This is the
    single source of truth for where newly-assigned sections land in the order.
    """
    current_max = await session.scalar(
        select(func.max(WorkingSectionMembership.sort_order)).where(
            WorkingSectionMembership.workspace_id == workspace_id,
            WorkingSectionMembership.user_id == user_id,
            WorkingSectionMembership.removed_at.is_(None),
        )
    )
    return 0 if current_max is None else current_max + 1
