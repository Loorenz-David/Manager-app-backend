from sqlalchemy import exists, func, select

from beyo_manager.domain.users.serializers import serialize_user_list_item, serialize_user_working_section_member, serialize_user_compact_with_role
from beyo_manager.domain.working_sections.serializers import serialize_working_section_compact
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_membership import WorkingSectionMembership
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.utils.string_filter import apply_string_filter

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50

_ALLOWED_STRING_COLUMNS = {
    "username": User.username,
    "email": User.email,
    "phone_number": User.phone_number,
}


async def list_users(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    string_filters = ctx.query_params.get("string_filters")
    role_filter = ctx.query_params.get("role")
    sections_filter = ctx.query_params.get("working_sections")
    compact = ctx.query_params.get("compact", "false").lower() == "true"

    def _build_base_query(include_all_columns: bool = True):
        """Build the base query with all filters applied."""
        if include_all_columns:
            q_stmt = (
                select(
                    User,
                    WorkspaceRole.client_id.label("role_client_id"),
                    WorkspaceRole.name.label("role_name"),
                )
                .join(WorkspaceMembership, WorkspaceMembership.user_id == User.client_id)
                .join(WorkspaceRole, WorkspaceRole.client_id == WorkspaceMembership.workspace_role_id)
                .where(
                    WorkspaceMembership.workspace_id == ctx.workspace_id,
                    WorkspaceMembership.is_active.is_(True),
                )
            )
        else:
            q_stmt = (
                select(func.count(User.client_id.distinct()))
                .join(WorkspaceMembership, WorkspaceMembership.user_id == User.client_id)
                .join(WorkspaceRole, WorkspaceRole.client_id == WorkspaceMembership.workspace_role_id)
                .where(
                    WorkspaceMembership.workspace_id == ctx.workspace_id,
                    WorkspaceMembership.is_active.is_(True),
                )
            )

        q_stmt = apply_string_filter(q_stmt, q, string_filters, _ALLOWED_STRING_COLUMNS)

        if role_filter:
            role_names = [r.strip() for r in role_filter.split(",") if r.strip()]
            q_stmt = q_stmt.where(WorkspaceRole.name.in_(role_names))

        if sections_filter:
            section_names = [s.strip() for s in sections_filter.split(",") if s.strip()]
            q_stmt = q_stmt.where(
                exists(
                    select(WorkingSectionMembership.client_id)
                    .join(
                        WorkingSection,
                        WorkingSection.client_id == WorkingSectionMembership.working_section_id,
                    )
                    .where(
                        WorkingSectionMembership.user_id == User.client_id,
                        WorkingSectionMembership.workspace_id == ctx.workspace_id,
                        WorkingSectionMembership.removed_at.is_(None),
                        WorkingSection.workspace_id == ctx.workspace_id,
                        WorkingSection.is_deleted.is_(False),
                        WorkingSection.name.in_(section_names),
                    )
                )
            )

        return q_stmt

    # Get total count before pagination
    count_stmt = _build_base_query(include_all_columns=False)
    total = (await ctx.session.execute(count_stmt)).scalar() or 0

    stmt = _build_base_query(include_all_columns=True)
    stmt = stmt.order_by(User.username.asc()).offset(offset).limit(limit + 1)
    result = await ctx.session.execute(stmt)
    rows = result.all()
    has_more = len(rows) > limit
    page = rows[:limit]

    if not page:
        return {
            "users": [],
            "users_pagination": {"has_more": False, "limit": limit, "offset": offset, "total": total},
        }

    # In compact mode, we don't need to fetch working sections
    if compact:
        users_data = [
            serialize_user_compact_with_role(row.User, row.role_client_id, row.role_name)
            for row in page
        ]
        return {
            "users": users_data,
            "users_pagination": {"has_more": has_more, "limit": limit, "offset": offset, "total": total},
        }

    # Full mode: fetch working sections for each user
    user_ids = [row.User.client_id for row in page]

    sections_result = await ctx.session.execute(
        select(
            WorkingSectionMembership.user_id,
            WorkingSection.client_id,
            WorkingSection.name,
            WorkingSection.image,
        )
        .join(
            WorkingSection,
            WorkingSection.client_id == WorkingSectionMembership.working_section_id,
        )
        .where(
            WorkingSectionMembership.user_id.in_(user_ids),
            WorkingSectionMembership.workspace_id == ctx.workspace_id,
            WorkingSectionMembership.removed_at.is_(None),
            WorkingSection.workspace_id == ctx.workspace_id,
            WorkingSection.is_deleted.is_(False),
        )
    )
    sections_by_user: dict[str, list[dict]] = {uid: [] for uid in user_ids}
    for sec_row in sections_result.all():
        sections_by_user[sec_row.user_id].append(
            serialize_working_section_compact(sec_row.client_id, sec_row.name, sec_row.image)
        )

    return {
        "users": [
            serialize_user_list_item(
                row.User,
                row.role_client_id,
                row.role_name,
                sections_by_user[row.User.client_id],
            )
            for row in page
        ],
        "users_pagination": {"has_more": has_more, "limit": limit, "offset": offset, "total": total},
    }
