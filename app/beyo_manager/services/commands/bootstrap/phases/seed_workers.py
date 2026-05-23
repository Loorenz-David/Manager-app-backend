from datetime import datetime, timezone
import random

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import Settings
from beyo_manager.models.tables.analytics.user_lifetime_stats import UserLifetimeStats
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.models.tables.working_sections.working_section_membership import WorkingSectionMembership


_FIRST_NAMES = [
    "alex",
    "emma",
    "liam",
    "olivia",
    "noah",
    "sophia",
    "lucas",
    "mia",
    "leo",
    "ava",
    "elias",
    "nora",
]

_LAST_NAMES = [
    "rivera",
    "bennett",
    "morris",
    "santos",
    "young",
    "ramirez",
    "reed",
    "foster",
    "woods",
    "diaz",
    "cole",
    "hayes",
]

# Worker slots requested by product, including shared workers across sections.
_WORKER_ASSIGNMENTS: dict[str, list[str]] = {
    "disassembly": ["worker_disassembly"],
    "cleaning": ["worker_cleaning_1", "worker_cleaning_2"],
    "structural repair": ["worker_structural"],
    "sanding": ["worker_structural"],
    "assembly": ["worker_disassembly"],
    "sewing": ["worker_sewing"],
    "weaving": ["worker_weaving"],
    "wood fix": ["worker_wood_fix_1", "worker_wood_fix_2"],
    "ground oil": ["worker_ground_oil"],
    "hardwax oil": ["worker_hardwax_oil"],
}


def _build_worker_identity(slot: str, rng: random.Random, used_usernames: set[str]) -> tuple[str, str]:
    while True:
        first = rng.choice(_FIRST_NAMES)
        last = rng.choice(_LAST_NAMES)
        suffix = rng.randint(10, 99)
        username = f"{first}_{last}_{suffix}"
        if username not in used_usernames:
            used_usernames.add(username)
            email = f"{username}@workers.beyo.dev"
            return username, email


async def seed_workers(
    session: AsyncSession,
    settings: Settings,
    workspace_result: dict[str, str],
    section_ids: dict[str, str],
    admin_user_id: str,
) -> dict[str, str]:
    workspace_id = workspace_result["workspace_id"]
    worker_workspace_role_id = workspace_result["worker"]

    rng = random.Random(f"{workspace_id}:bootstrap_workers")
    used_usernames: set[str] = set()
    slot_to_user_id: dict[str, str] = {}

    worker_slots = sorted({slot for slots in _WORKER_ASSIGNMENTS.values() for slot in slots})

    for slot in worker_slots:
        username, email = _build_worker_identity(slot, rng, used_usernames)

        existing_user = await session.scalar(select(User).where(User.email == email))
        if existing_user is None:
            hashed_password = bcrypt.hashpw(
                settings.bootstrap_admin_password.encode(),
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
        slot_to_user_id[slot] = worker_user_id

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
    for section_name, slots in _WORKER_ASSIGNMENTS.items():
        section_id = section_ids.get(section_name)
        if section_id is None:
            continue

        for slot in slots:
            worker_user_id = slot_to_user_id[slot]
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

    return slot_to_user_id
