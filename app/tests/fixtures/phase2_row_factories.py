from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.workspaces.workspace import Workspace


async def adopt_or_create_role(db_session, role_name: RoleNameEnum) -> Role:
    """Reuse the database-wide catalog row or create it when this worker owns the first one."""
    role = await db_session.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        role = Role(name=role_name)
        db_session.add(role)
        await db_session.flush()
    return role


async def create_test_workspace(db_session, label: str) -> Workspace:
    """Create a workspace owned by the current test rather than borrowing arbitrary state."""
    workspace = Workspace(name=f"{label}-{uuid4().hex}")
    db_session.add(workspace)
    await db_session.flush()
    return workspace
