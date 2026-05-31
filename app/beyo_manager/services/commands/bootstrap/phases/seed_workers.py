from datetime import datetime, timezone

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import Settings
from beyo_manager.models.tables.analytics.user_lifetime_stats import UserLifetimeStats
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.models.tables.working_sections.working_section_membership import WorkingSectionMembership


_WORKER_NAMES = [
    "Roma",
    "Andrii",
    "Nazar",
    "Tatiana",
    "Feruza",
    "Kola",
    "Norby",
    "Vitaly",
]

_WORKER_PASSWORD = "Admin1234!"


async def seed_workers(
    session: AsyncSession,
    _settings: Settings,
    workspace_result: dict[str, str],
    section_ids: dict[str, str],
    admin_user_id: str,
) -> dict[str, str]:
    workspace_id = workspace_result["workspace_id"]
    worker_workspace_role_id = workspace_result["worker"]

    worker_name_to_user_id: dict[str, str] = {}

    for worker_name in _WORKER_NAMES:
        username = worker_name
        email = f"{worker_name.lower()}@test.dev"

        existing_user = await session.scalar(select(User).where(User.email == email))
        if existing_user is None:
            hashed_password = bcrypt.hashpw(
                _WORKER_PASSWORD.encode(),
                bcrypt.gensalt(),
            ).decode()
            user = User(
                email=email,
                username=username,
                password=hashed_password,
                created_by_id=admin_user_id,
            )
            session.add(user)
            await session.flush()
            worker_user = user
        else:
            worker_user = existing_user

        worker_user_id = worker_user.client_id
        worker_name_to_user_id[worker_name] = worker_user_id

        existing_membership = await session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.user_id == worker_user_id,
                WorkspaceMembership.workspace_id == workspace_id,
            )
        )
        if existing_membership is None:
            session.add(
                WorkspaceMembership(
                    user_id=worker_user_id,
                    workspace_id=workspace_id,
                    workspace_role_id=worker_workspace_role_id,
                    is_active=True,
                )
            )
            await session.flush()

        existing_work_profile = await session.scalar(
            select(UserWorkProfile).where(
                UserWorkProfile.user_id == worker_user_id,
                UserWorkProfile.workspace_id == workspace_id,
            )
        )
        if existing_work_profile is None:
            now = datetime.now(timezone.utc)
            session.add(
                UserWorkProfile(
                    user_id=worker_user_id,
                    workspace_id=workspace_id,
                    created_by_id=admin_user_id,
                    created_at=now,
                )
            )
            session.add(
                UserLifetimeStats(
                    workspace_id=workspace_id,
                    user_id=worker_user_id,
                    user_display_name_snapshot=worker_user.username,
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.flush()

    now = datetime.now(timezone.utc)
    for section_id in section_ids.values():
        for worker_user_id in worker_name_to_user_id.values():
            existing_section_membership = await session.scalar(
                select(WorkingSectionMembership).where(
                    WorkingSectionMembership.workspace_id == workspace_id,
                    WorkingSectionMembership.working_section_id == section_id,
                    WorkingSectionMembership.user_id == worker_user_id,
                    WorkingSectionMembership.removed_at.is_(None),
                )
            )
            if existing_section_membership is not None:
                continue

            session.add(
                WorkingSectionMembership(
                    workspace_id=workspace_id,
                    working_section_id=section_id,
                    user_id=worker_user_id,
                    assigned_at=now,
                    assigned_by_id=admin_user_id,
                )
            )
            await session.flush()

            return worker_name_to_user_id
