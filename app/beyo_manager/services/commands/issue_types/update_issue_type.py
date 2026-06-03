from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.items.item_category_issue_type import ItemCategoryIssueType
from beyo_manager.models.tables.issue_types.issue_type import IssueType
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_supported_issue_type import (
    WorkingSectionSupportedIssueType,
)
from beyo_manager.services.commands.issue_types.requests import parse_update_issue_type_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def update_issue_type(ctx: ServiceContext) -> dict:
    request = parse_update_issue_type_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        issue_type = await ctx.session.scalar(
            select(IssueType).where(
                IssueType.workspace_id == ctx.workspace_id,
                IssueType.client_id == request.issue_type_id,
                IssueType.is_deleted.is_(False),
            )
        )
        if issue_type is None:
            raise NotFound("Issue type not found.")

        if request.issue_type_name and request.issue_type_name != issue_type.name:
            existing = await ctx.session.scalar(
                select(IssueType).where(
                    IssueType.workspace_id == ctx.workspace_id,
                    IssueType.name == request.issue_type_name,
                    IssueType.is_deleted.is_(False),
                    IssueType.client_id != issue_type.client_id,
                )
            )
            if existing is not None:
                raise ConflictError("Issue type name already exists.")
            issue_type.name = request.issue_type_name

        if request.issue_mode is not None:
            issue_type.issue_mode = request.issue_mode

        if request.linked_working_section_ids is not None:
            existing_rows = (
                await ctx.session.execute(
                    select(WorkingSectionSupportedIssueType).where(
                        WorkingSectionSupportedIssueType.workspace_id == ctx.workspace_id,
                        WorkingSectionSupportedIssueType.issue_type_id == issue_type.client_id,
                    )
                )
            ).scalars().all()
            existing_ids = {row.working_section_id for row in existing_rows}
            incoming_ids = set(request.linked_working_section_ids)

            for row in existing_rows:
                if row.working_section_id not in incoming_ids:
                    await ctx.session.delete(row)

            for working_section_id in incoming_ids - existing_ids:
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

        if request.linked_item_category_ids is not None:
            existing_rows = (
                await ctx.session.execute(
                    select(ItemCategoryIssueType).where(
                        ItemCategoryIssueType.workspace_id == ctx.workspace_id,
                        ItemCategoryIssueType.issue_type_id == issue_type.client_id,
                    )
                )
            ).scalars().all()
            existing_map = {
                (row.item_category_id, row.placement_of_issue): row for row in existing_rows
            }
            incoming_map = {
                (entry.item_category_id, entry.placement_of_issue): entry
                for entry in request.linked_item_category_ids
            }

            for key, row in existing_map.items():
                if key not in incoming_map:
                    await ctx.session.delete(row)

            validated_item_category_ids: set[str] = set()
            for key, incoming_entry in incoming_map.items():
                if key in existing_map:
                    continue

                item_category_id = incoming_entry.item_category_id
                placement_of_issue = incoming_entry.placement_of_issue

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

        issue_type.updated_at = datetime.now(timezone.utc)
        issue_type.updated_by_id = ctx.user_id

    return {"client_id": issue_type.client_id}
