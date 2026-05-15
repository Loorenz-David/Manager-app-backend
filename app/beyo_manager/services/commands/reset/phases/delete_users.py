from sqlalchemy import delete, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership


async def delete_orphan_bootstrap_users(
    session: AsyncSession,
    *,
    bootstrap_admin_email: str | None,
    bootstrap_admin_username: str | None,
) -> int:
    """
    Optionally delete bootstrap admin users only if they are now orphaned.

    Safety constraints:
    - Only candidates matching configured bootstrap email and/or username
    - Candidate user must have zero workspace memberships remaining
    """
    candidate_predicates = []
    if bootstrap_admin_email:
        candidate_predicates.append(User.email == bootstrap_admin_email)
    if bootstrap_admin_username:
        candidate_predicates.append(User.username == bootstrap_admin_username)

    if not candidate_predicates:
        return 0

    has_membership = exists(
        select(WorkspaceMembership.client_id).where(WorkspaceMembership.user_id == User.client_id)
    )

    result = await session.execute(
        delete(User).where(
            or_(*candidate_predicates),
            ~has_membership,
        )
    )
    return result.rowcount or 0
