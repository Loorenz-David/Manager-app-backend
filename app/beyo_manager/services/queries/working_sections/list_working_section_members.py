from sqlalchemy import select

from beyo_manager.domain.working_sections.serializers import serialize_working_section_member
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_membership import (
    WorkingSectionMembership,
)
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_working_section_members(ctx: ServiceContext) -> dict:
    working_section_id: str = ctx.incoming_data.get("working_section_id", "")
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

    section = await ctx.session.scalar(
        select(WorkingSection).where(
            WorkingSection.workspace_id == ctx.workspace_id,
            WorkingSection.client_id == working_section_id,
            WorkingSection.is_deleted.is_(False),
        )
    )
    if section is None:
        raise NotFound("Working section not found.")

    result = await ctx.session.execute(
        select(
            WorkingSectionMembership.client_id.label("membership_id"),
            WorkingSectionMembership.working_section_id,
            WorkingSectionMembership.user_id,
            User.username,
            WorkingSectionMembership.assigned_at,
        )
        .join(User, User.client_id == WorkingSectionMembership.user_id)
        .where(
            WorkingSectionMembership.workspace_id == ctx.workspace_id,
            WorkingSectionMembership.working_section_id == working_section_id,
            WorkingSectionMembership.removed_at.is_(None),
        )
        .order_by(WorkingSectionMembership.assigned_at.asc())
        .offset(offset)
        .limit(limit + 1)
    )
    rows = result.all()
    has_more = len(rows) > limit
    members = [serialize_working_section_member(row) for row in rows[:limit]]
    return {
        "members": members,
        "members_pagination": {"has_more": has_more, "limit": limit, "offset": offset},
    }
