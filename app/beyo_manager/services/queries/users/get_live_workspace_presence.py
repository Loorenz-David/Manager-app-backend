import json

from sqlalchemy import select

from beyo_manager.domain.presence.serializers import serialize_live_user_presence
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.redis import make_key
from beyo_manager.services.infra.redis.async_client import get_async_redis


async def get_live_workspace_presence(ctx: ServiceContext) -> dict:
    result = await ctx.session.execute(
        select(User, Role.name.label("role_name"))
        .join(WorkspaceMembership, WorkspaceMembership.user_id == User.client_id)
        .join(WorkspaceRole, WorkspaceRole.client_id == WorkspaceMembership.workspace_role_id)
        .join(Role, Role.client_id == WorkspaceRole.role_id)
        .where(
            WorkspaceMembership.workspace_id == ctx.workspace_id,
            WorkspaceMembership.is_active.is_(True),
        )
        .order_by(User.username.asc())
    )
    members = result.all()

    if not members:
        return {"presence": []}

    redis = get_async_redis()
    view_keys = [make_key("user_view", row.User.client_id) for row in members]
    online_keys = [make_key("user_online", row.User.client_id) for row in members]

    pipe = redis.pipeline(transaction=False)
    for key in view_keys + online_keys:
        pipe.get(key)
    values = await pipe.execute()

    n = len(members)
    view_values = values[:n]
    online_values = values[n:]

    presence = []
    for i, row in enumerate(members):
        raw_view = view_values[i]
        current_view = json.loads(raw_view) if raw_view is not None else None
        is_online = online_values[i] is not None
        presence.append(
            serialize_live_user_presence(row.User, row.role_name, current_view, is_online)
        )

    return {"presence": presence}
