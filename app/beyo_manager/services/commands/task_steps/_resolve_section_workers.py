from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.working_sections.working_section_membership import (
    WorkingSectionMembership,
)
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership


async def resolve_section_worker_ids(
    session: AsyncSession,
    *,
    workspace_id: str,
    working_section_ids: set[str],
) -> dict[str, list[str]]:
    """Map each working section to the user_ids of its active members.

    Single source of truth for "who belongs to this working section" — used by
    both reassignment acknowledgments and the new-steps notification so their
    audiences can never drift. A user is a member of a section when they have an
    active ``WorkingSectionMembership`` (``removed_at IS NULL``) and an active
    workspace membership (deactivated users are excluded). There is intentionally
    no workspace-role filter: every assigned section member is included. Sections
    with no members are simply absent from the returned mapping.
    """
    if not working_section_ids:
        return {}

    result = await session.execute(
        select(
            WorkingSectionMembership.working_section_id,
            WorkingSectionMembership.user_id,
        )
        .join(
            WorkspaceMembership,
            WorkspaceMembership.user_id == WorkingSectionMembership.user_id,
        )
        .where(
            WorkingSectionMembership.workspace_id == workspace_id,
            WorkingSectionMembership.working_section_id.in_(working_section_ids),
            WorkingSectionMembership.removed_at.is_(None),
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.is_active.is_(True),
        )
        .distinct()
    )

    members_by_section: dict[str, list[str]] = {}
    for section_id, user_id in result.all():
        members_by_section.setdefault(section_id, []).append(user_id)
    return members_by_section
