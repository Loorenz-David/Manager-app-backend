import bcrypt
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import Settings
from beyo_manager.models.tables.analytics.user_lifetime_stats import UserLifetimeStats
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership


async def seed_admin_user(
    session: AsyncSession,
    settings: Settings,
    workspace_result: dict[str, str],
) -> dict[str, str]:
    workspace_id = workspace_result["workspace_id"]
    admin_workspace_role_id = workspace_result["admin"]

    existing_user = await session.scalar(
        select(User).where(User.email == settings.bootstrap_admin_email)
    )
    if existing_user is None:
        hashed_password = bcrypt.hashpw(
            settings.bootstrap_admin_password.encode(),
            bcrypt.gensalt(),
        ).decode()
        user = User(
            email=settings.bootstrap_admin_email,
            username=settings.bootstrap_admin_username,
            password=hashed_password,
        )
        session.add(user)
        await session.flush()
        admin_user = user
    else:
        admin_user = existing_user

    user_client_id = admin_user.client_id

    existing_membership = await session.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.user_id == user_client_id,
            WorkspaceMembership.workspace_id == workspace_id,
        )
    )
    if existing_membership is None:
        membership = WorkspaceMembership(
            user_id=user_client_id,
            workspace_id=workspace_id,
            workspace_role_id=admin_workspace_role_id,
            is_active=True,
        )
        session.add(membership)
        await session.flush()

    existing_work_profile = await session.scalar(
        select(UserWorkProfile).where(
            UserWorkProfile.user_id == user_client_id,
            UserWorkProfile.workspace_id == workspace_id,
        )
    )
    if existing_work_profile is None:
        now = datetime.now(timezone.utc)
        session.add(
            UserWorkProfile(
                user_id=user_client_id,
                workspace_id=workspace_id,
                created_by_id=user_client_id,
                created_at=now,
            )
        )
        session.add(
            UserLifetimeStats(
                workspace_id=workspace_id,
                user_id=user_client_id,
                user_display_name_snapshot=admin_user.username,
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()

    return {"admin_user_id": user_client_id}
