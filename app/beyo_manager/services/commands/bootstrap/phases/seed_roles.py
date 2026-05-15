from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.models.tables.roles.role import Role


async def seed_roles(session: AsyncSession) -> dict[str, str]:
    role_ids: dict[str, str] = {}
    for role_name in [
        RoleNameEnum.ADMIN,
        RoleNameEnum.WORKER,
        RoleNameEnum.MANAGER,
        RoleNameEnum.SELLER,
    ]:
        existing = await session.scalar(select(Role).where(Role.name == role_name))
        if existing is not None:
            role_ids[role_name.value] = existing.client_id
            continue

        role = Role(name=role_name)
        session.add(role)
        await session.flush()
        role_ids[role_name.value] = role.client_id

    return role_ids
