from sqlalchemy import select

from beyo_manager.domain.issue_types.enums import IssueSourceEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.items.item_category_issue_type import ItemCategoryIssueType
from beyo_manager.models.tables.issue_types.issue_type import IssueType
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_supported_issue_type import (
    WorkingSectionSupportedIssueType,
)
from beyo_manager.services.commands.issue_types.requests import parse_create_issue_type_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def create_issue_type(ctx: ServiceContext) -> dict:
    request = parse_create_issue_type_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        existing = await ctx.session.scalar(
            select(IssueType).where(
                IssueType.workspace_id == ctx.workspace_id,
                IssueType.name == request.issue_type_name,
                IssueType.is_deleted.is_(False),
            )
        )
        if existing is not None:
            raise ConflictError("Issue type name already exists.")

        issue_type = IssueType(
            workspace_id=ctx.workspace_id,
            name=request.issue_type_name,
            source=IssueSourceEnum.MANUAL,
            issue_mode=request.issue_mode,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(issue_type)
        await ctx.session.flush()

        for working_section_id in set(request.linked_working_section_ids):
            working_section = await ctx.session.scalar(
                select(WorkingSection).where(
                    WorkingSection.workspace_id == ctx.workspace_id,
                    WorkingSection.client_id == working_section_id,
                    WorkingSection.is_deleted.is_(False),
                )
            )
            if working_section is None:
                raise NotFound(f"Working section {working_section_id!r} not found.")

            ctx.session.add(
                WorkingSectionSupportedIssueType(
                    workspace_id=ctx.workspace_id,
                    working_section_id=working_section_id,
                    issue_type_id=issue_type.client_id,
                )
            )

        validated_item_category_ids: set[str] = set()
        for item_category_link in request.linked_item_category_ids:
            item_category_id = item_category_link.item_category_id
            placement_of_issue = item_category_link.placement_of_issue

            if item_category_id not in validated_item_category_ids:
                item_category = await ctx.session.scalar(
                    select(ItemCategory).where(
                        ItemCategory.workspace_id == ctx.workspace_id,
                        ItemCategory.client_id == item_category_id,
                        ItemCategory.is_deleted.is_(False),
                    )
                )
                if item_category is None:
                    raise NotFound(f"Item category {item_category_id!r} not found.")
                validated_item_category_ids.add(item_category_id)

            ctx.session.add(
                ItemCategoryIssueType(
                    workspace_id=ctx.workspace_id,
                    item_category_id=item_category_id,
                    issue_type_id=issue_type.client_id,
                    placement_of_issue=placement_of_issue,
                )
            )

        await ctx.session.flush()

    return {"client_id": issue_type.client_id}
