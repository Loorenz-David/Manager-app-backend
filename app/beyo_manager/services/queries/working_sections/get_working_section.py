from sqlalchemy import select
from sqlalchemy.orm import aliased

from beyo_manager.domain.working_sections.serializers import serialize_working_section_full
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.issue_types.issue_type import IssueType
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_dependency import WorkingSectionDependency
from beyo_manager.models.tables.working_sections.working_section_item_category import WorkingSectionItemCategory
from beyo_manager.models.tables.working_sections.working_section_supported_issue_type import (
    WorkingSectionSupportedIssueType,
)
from beyo_manager.services.context import ServiceContext


async def get_working_section(ctx: ServiceContext) -> dict:
    working_section_id: str = ctx.incoming_data.get("client_id", "")

    result = await ctx.session.execute(
        select(WorkingSection).where(
            WorkingSection.workspace_id == ctx.workspace_id,
            WorkingSection.client_id == working_section_id,
            WorkingSection.is_deleted.is_(False),
        )
    )
    section = result.scalar_one_or_none()
    if section is None:
        raise NotFound("Working section not found.")

    prerequisite_section = aliased(WorkingSection)
    dep_result = await ctx.session.execute(
        select(
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
            WorkingSectionDependency.dependent_section_id == working_section_id,
            prerequisite_section.workspace_id == ctx.workspace_id,
            prerequisite_section.is_deleted.is_(False),
        )
    )
    dependencies = [
        (row.prerequisite_section_id, row.prerequisite_name) for row in dep_result.all()
    ]

    cat_result = await ctx.session.execute(
        select(
            WorkingSectionItemCategory.item_category_id,
            ItemCategory.name.label("category_name"),
        )
        .select_from(WorkingSectionItemCategory)
        .join(ItemCategory, ItemCategory.client_id == WorkingSectionItemCategory.item_category_id)
        .where(
            WorkingSectionItemCategory.workspace_id == ctx.workspace_id,
            WorkingSectionItemCategory.working_section_id == working_section_id,
            ItemCategory.workspace_id == ctx.workspace_id,
            ItemCategory.is_deleted.is_(False),
        )
    )
    categories = [(row.item_category_id, row.category_name) for row in cat_result.all()]

    issue_type_result = await ctx.session.execute(
        select(
            WorkingSectionSupportedIssueType.issue_type_id,
            IssueType.name.label("issue_type_name"),
        )
        .select_from(WorkingSectionSupportedIssueType)
        .join(IssueType, IssueType.client_id == WorkingSectionSupportedIssueType.issue_type_id)
        .where(
            WorkingSectionSupportedIssueType.workspace_id == ctx.workspace_id,
            WorkingSectionSupportedIssueType.working_section_id == working_section_id,
            IssueType.workspace_id == ctx.workspace_id,
            IssueType.is_deleted.is_(False),
        )
    )
    issue_types = [
        (row.issue_type_id, row.issue_type_name) for row in issue_type_result.all()
    ]

    return {
        "working_section": serialize_working_section_full(
            section,
            dependencies,
            categories,
            issue_types,
        )
    }
