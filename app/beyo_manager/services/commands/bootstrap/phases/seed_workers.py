from datetime import datetime, timezone

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import Settings
from beyo_manager.errors.validation import ValidationError
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
    "Mykola",
    "Norby",
    "Vitaly",
    "Stina",
    "Betty",
    "Fayoz",
]

_WORKER_PASSWORD = "Admin1234!"

_WORKER_EMAILS: dict[str, str] = {
    "Mykola": "mykola@beyovintage.se",
}

# Select workspace role per seeded bootstrap user.
# Valid values are workspace role keys produced by seed_workspace: "admin", "worker", "manager", "seller", "wood_worker".
_WORKER_WORKSPACE_ROLES: dict[str, str] = {
    worker_name: "worker"
    for worker_name in _WORKER_NAMES
}
_WORKER_WORKSPACE_ROLES["Norby"] = "manager"
_WORKER_WORKSPACE_ROLES["Stina"] = "manager"
_WORKER_WORKSPACE_ROLES["Betty"] = "manager"
_WORKER_WORKSPACE_ROLES["Fayoz"] = "admin"
_WORKER_WORKSPACE_ROLES["Mykola"] = "wood_worker"

# Toggle worker assignment per working section.
# Set any section to False to skip automatic assignment for that section.
_WORKING_SECTION_ASSIGNMENT_MAP: dict[str, bool] = {
    "disassembly": True,
    "cleaning": True,
    "structural repair": True,
    "sanding": True,
    "upholstery removal": True,
    "padding": True,
    "upholstery installation": True,
    "assembly": True,
    "sewing": True,
    "weaving": True,
    "wood fix": True,
    "ground oil": True,
    "hardwax oil": True,
}

_SECTION_GROUPS: dict[str, tuple[str, ...]] = {
    "restoration": (
        "disassembly",
        "cleaning",
        "structural repair",
        "sanding",
        "assembly",
    ),
    "restoration_core": (
        "disassembly",
        "structural repair",
        "sanding",
        "assembly",
    ),
    "upholstery": (
        "upholstery removal",
        "padding",
        "upholstery installation",
        "sewing",
        "weaving",
    ),
    "wood_finishing": (
        "wood fix",
        "ground oil",
        "hardwax oil",
    ),
    "kola_sections": (
        "cleaning",
        "wood fix",
        "ground oil",
        "hardwax oil",
    ),
}

_SECTION_GROUPS["all"] = tuple(_WORKING_SECTION_ASSIGNMENT_MAP.keys())

# Select section groups per worker.
# Default: restoration_core + upholstery (excludes kola_sections which belong to Mykola only).
_WORKER_SECTION_GROUPS: dict[str, tuple[str, ...]] = {
    worker_name: ("restoration_core", "upholstery")
    for worker_name in _WORKER_NAMES
}
_WORKER_SECTION_GROUPS["Mykola"] = ("kola_sections",)
_WORKER_SECTION_GROUPS["Stina"] = ()
_WORKER_SECTION_GROUPS["Betty"] = ()


def _resolve_worker_section_names(worker_name: str) -> set[str]:
    selected_groups = _WORKER_SECTION_GROUPS.get(worker_name, ("all",))
    section_names: set[str] = set()

    for group_name in selected_groups:
        section_names.update(_SECTION_GROUPS.get(group_name, ()))

    return {
        section_name
        for section_name in section_names
        if _WORKING_SECTION_ASSIGNMENT_MAP.get(section_name, True)
    }


def _resolve_worker_workspace_role_id(
    worker_name: str,
    workspace_result: dict[str, str],
) -> str:
    role_key = _WORKER_WORKSPACE_ROLES.get(worker_name, "worker")
    workspace_role_id = workspace_result.get(role_key)
    if workspace_role_id is None:
        raise ValidationError(
            f"Unknown workspace role '{role_key}' configured for seeded worker '{worker_name}'."
        )
    return workspace_role_id


async def seed_workers(
    session: AsyncSession,
    _settings: Settings,
    workspace_result: dict[str, str],
    section_ids: dict[str, str],
    admin_user_id: str,
) -> dict[str, str]:
    workspace_id = workspace_result["workspace_id"]

    worker_name_to_user_id: dict[str, str] = {}

    for worker_name in _WORKER_NAMES:
        username = worker_name
        email = _WORKER_EMAILS.get(worker_name, f"{worker_name.lower()}@test.dev")

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
        worker_workspace_role_id = _resolve_worker_workspace_role_id(worker_name, workspace_result)
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
        elif existing_membership.workspace_role_id != worker_workspace_role_id:
            existing_membership.workspace_role_id = worker_workspace_role_id
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
    for worker_name, worker_user_id in worker_name_to_user_id.items():
        worker_section_names = _resolve_worker_section_names(worker_name)
        for section_name, section_id in section_ids.items():
            existing_section_membership = await session.scalar(
                select(WorkingSectionMembership).where(
                    WorkingSectionMembership.workspace_id == workspace_id,
                    WorkingSectionMembership.working_section_id == section_id,
                    WorkingSectionMembership.user_id == worker_user_id,
                    WorkingSectionMembership.removed_at.is_(None),
                )
            )

            if section_name not in worker_section_names:
                if existing_section_membership is not None:
                    existing_section_membership.removed_at = now
                    await session.flush()
                continue

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
