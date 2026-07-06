from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from beyo_manager.config import settings
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.roles.permissions import resolve_permissions_for_role
from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext


_DEFAULT_APP_SCOPE = "manager"
_SCOPE_ALLOWED_ROLES: dict[str, set[str]] = {
    "manager": {RoleNameEnum.MANAGER.value, RoleNameEnum.ADMIN.value, RoleNameEnum.SELLER.value},  # TODO: remove seller when seller app is built
    "worker": {RoleNameEnum.WORKER.value, RoleNameEnum.MANAGER.value},
    "seller": {RoleNameEnum.SELLER.value},
    "admin": {RoleNameEnum.ADMIN.value},
}


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


async def sign_in_user(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data
    identifier = data.get("email") or data.get("username")
    password = data.get("password", "")

    result = await ctx.session.execute(
        select(User).where((User.email == identifier) | (User.username == identifier))
    )
    user = result.scalar_one_or_none()
    if user is None or not _verify_password(password, user.password):
        raise PermissionDenied("Invalid credentials.")

    membership_result = await ctx.session.execute(
        select(WorkspaceMembership)
        .options(selectinload(WorkspaceMembership.workspace_role).selectinload(WorkspaceRole.role))
        .where(
            WorkspaceMembership.user_id == user.client_id,
            WorkspaceMembership.is_active.is_(True),
        )
    )
    membership = membership_result.scalar_one_or_none()
    if membership is None:
        raise PermissionDenied("User has no workspace membership.")

    workspace = await ctx.session.get(Workspace, membership.workspace_id)
    app_scope = data.get("app_scope", _DEFAULT_APP_SCOPE)
    actual_role = membership.workspace_role.role.name.value
    allowed_roles = _SCOPE_ALLOWED_ROLES.get(app_scope)
    if allowed_roles is None or actual_role not in allowed_roles:
        raise PermissionDenied("Invalid credentials.")
    return build_auth_response(user, workspace=workspace, membership=membership, app_scope=app_scope)


def build_auth_response(user: User, *, workspace: Workspace, membership: WorkspaceMembership, app_scope: str) -> dict:
    workspace_role = membership.workspace_role
    permission_role = workspace_role.role
    permissions = resolve_permissions_for_role(permission_role)
    workspace_specialization = (
        workspace_role.specialization.value
        if workspace_role.specialization is not None
        else None
    )
    now = datetime.now(timezone.utc)
    claims = {
        "user_id": user.client_id,
        "username": user.username,
        "workspace_id": workspace.client_id,
        "workspace_role_id": workspace_role.client_id,
        "role_name": permission_role.name.value,
        "workspace_role_name": workspace_specialization or permission_role.name.value,
        "workspace_specialization": workspace_specialization,
        "app_scope": app_scope,
        "time_zone": workspace.time_zone or "UTC",
        "backend_permissions": permissions["backend"],
        "ui": permissions["ui"],
    }
    access_token = jwt.encode(
        {**claims, "jti": str(uuid4()), "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes)},
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    refresh_token = jwt.encode(
        {**claims, "jti": str(uuid4()), "exp": now + timedelta(days=settings.jwt_refresh_token_expire_days)},
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    return {
        "access_token": access_token,
        "_refresh_token": refresh_token,
        "user": {
            **claims,
            "email": user.email,
        },
        "workspace_id": workspace.client_id,
    }
