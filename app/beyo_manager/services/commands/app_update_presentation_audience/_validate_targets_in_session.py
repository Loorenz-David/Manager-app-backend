"""Validate audience targets are within the publisher's permitted scope.

In-session helper (not a command). Prevents cross-workspace targeting and
targeting of users who are not active members of the acting workspace.
"""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.workspaces.workspace_membership import (
    WorkspaceMembership,
)


async def validate_targets_in_session(
    session: AsyncSession,
    workspace_id: str,
    workspace_ids: Sequence[str],
    user_ids: Sequence[str],
) -> None:
    # Cross-workspace targeting is not permitted (no platform-admin tier exists).
    outside = [ws for ws in workspace_ids if ws != workspace_id]
    if outside:
        raise PermissionDenied(
            "Cannot target workspaces outside your own workspace."
        )

    if user_ids:
        result = await session.execute(
            select(WorkspaceMembership.user_id).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id.in_(set(user_ids)),
                WorkspaceMembership.is_active.is_(True),
            )
        )
        member_ids = set(result.scalars().all())
        missing = set(user_ids) - member_ids
        if missing:
            raise ValidationError(
                f"Target user(s) are not active members of this workspace: {sorted(missing)}."
            )
