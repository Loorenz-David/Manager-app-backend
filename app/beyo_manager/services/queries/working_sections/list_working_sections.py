from sqlalchemy import select
from sqlalchemy.orm import aliased

from beyo_manager.domain.users.serializers import serialize_user_working_section_member
from beyo_manager.domain.working_sections.serializers import serialize_working_section_full
from beyo_manager.models.tables.issue_types.issue_type import IssueType
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_dependency import WorkingSectionDependency
from beyo_manager.models.tables.working_sections.working_section_item_category import WorkingSectionItemCategory
from beyo_manager.models.tables.working_sections.working_section_membership import WorkingSectionMembership
from beyo_manager.models.tables.working_sections.working_section_supported_issue_type import (
    WorkingSectionSupportedIssueType,
)
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_working_sections(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

    result = await ctx.session.execute(
        select(WorkingSection)
        .where(
            WorkingSection.workspace_id == ctx.workspace_id,
            WorkingSection.is_deleted.is_(False),
        )
        .order_by(WorkingSection.created_at.asc())
        .offset(offset)
        .limit(limit + 1)
    )
    rows = result.scalars().all()
    has_more = len(rows) > limit
    sections = rows[:limit]

    if not sections:
        return {
            "working_sections": [],
            "working_sections_pagination": {"has_more": False, "limit": limit, "offset": offset},
        }

    section_ids = [section.client_id for section in sections]

    prerequisite_section = aliased(WorkingSection)
    dep_result = await ctx.session.execute(
        select(
            WorkingSectionDependency.dependent_section_id,
            WorkingSectionDependency.prerequisite_section_id,
            prerequisite_section.name.label("prerequisite_name"),
        )
        .select_from(WorkingSectionDependency)
        .join(
            prerequisite_section,
            prerequisite_section.client_id == WorkingSectionDependency.prerequisite_section_id,
        )
        .where(
            WorkingSectionDependency.workspace_id == ctx.workspace_id,
            WorkingSectionDependency.dependent_section_id.in_(section_ids),
            prerequisite_section.workspace_id == ctx.workspace_id,
            prerequisite_section.is_deleted.is_(False),
        )
    )
    deps_by_section: dict[str, list[tuple[str, str]]] = {section_id: [] for section_id in section_ids}
    for row in dep_result.all():
        deps_by_section[row.dependent_section_id].append(
            (row.prerequisite_section_id, row.prerequisite_name)
        )

    cat_result = await ctx.session.execute(
        select(
            WorkingSectionItemCategory.working_section_id,
            WorkingSectionItemCategory.item_category_id,
            ItemCategory.name.label("category_name"),
            ItemCategory.major_category.label("major_category"),
        )
        .select_from(WorkingSectionItemCategory)
        .join(ItemCategory, ItemCategory.client_id == WorkingSectionItemCategory.item_category_id)
        .where(
            WorkingSectionItemCategory.workspace_id == ctx.workspace_id,
            WorkingSectionItemCategory.working_section_id.in_(section_ids),
            ItemCategory.workspace_id == ctx.workspace_id,
            ItemCategory.is_deleted.is_(False),
        )
    )
    cats_by_section: dict[str, list[tuple[str, str, str]]] = {section_id: [] for section_id in section_ids}
    for row in cat_result.all():
        cats_by_section[row.working_section_id].append(
            (row.item_category_id, row.category_name, row.major_category.value)
        )

    issue_type_result = await ctx.session.execute(
        select(
            WorkingSectionSupportedIssueType.working_section_id,
            WorkingSectionSupportedIssueType.issue_type_id,
            IssueType.name.label("issue_type_name"),
        )
        .select_from(WorkingSectionSupportedIssueType)
        .join(IssueType, IssueType.client_id == WorkingSectionSupportedIssueType.issue_type_id)
        .where(
            WorkingSectionSupportedIssueType.workspace_id == ctx.workspace_id,
            WorkingSectionSupportedIssueType.working_section_id.in_(section_ids),
            IssueType.workspace_id == ctx.workspace_id,
            IssueType.is_deleted.is_(False),
        )
    )
    issues_by_section: dict[str, list[tuple[str, str]]] = {section_id: [] for section_id in section_ids}
    for row in issue_type_result.all():
        issues_by_section[row.working_section_id].append((row.issue_type_id, row.issue_type_name))

    member_result = await ctx.session.execute(
        select(
            WorkingSectionMembership.working_section_id,
            User,
        )
        .select_from(WorkingSectionMembership)
        .join(User, User.client_id == WorkingSectionMembership.user_id)
        .where(
            WorkingSectionMembership.workspace_id == ctx.workspace_id,
            WorkingSectionMembership.working_section_id.in_(section_ids),
            WorkingSectionMembership.removed_at.is_(None),
        )
        .order_by(WorkingSectionMembership.working_section_id, User.username.asc())
    )
    members_by_section: dict[str, list[dict]] = {section_id: [] for section_id in section_ids}
    for row in member_result.all():
        members_by_section[row.working_section_id].append(
            serialize_user_working_section_member(row.User)
        )

    return {
        "working_sections": [
            serialize_working_section_full(
                section,
                deps_by_section[section.client_id],
                cats_by_section[section.client_id],
                issues_by_section[section.client_id],
                members_by_section[section.client_id],
            )
            for section in sections
        ],
        "working_sections_pagination": {"has_more": has_more, "limit": limit, "offset": offset},
    }
