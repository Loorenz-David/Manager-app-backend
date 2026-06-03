from datetime import datetime, timezone

from sqlalchemy import delete, select, update

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item_category_issue_type import ItemCategoryIssueType
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.models.tables.issue_types.issue_type import IssueType
from beyo_manager.models.tables.working_sections.working_section_supported_issue_type import (
    WorkingSectionSupportedIssueType,
)
from beyo_manager.services.commands.issue_types.requests import parse_delete_issue_types_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def delete_issue_types(ctx: ServiceContext) -> dict:
    request = parse_delete_issue_types_request(ctx.incoming_data)
    requested_ids = {entry.issue_type_id for entry in request.issues}
    now = datetime.now(timezone.utc)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(IssueType).where(
                IssueType.workspace_id == ctx.workspace_id,
                IssueType.client_id.in_(requested_ids),
                IssueType.is_deleted.is_(False),
            )
        )
        issue_types = result.scalars().all()

        found_ids = {issue_type.client_id for issue_type in issue_types}
        if found_ids != requested_ids:
            missing_ids = sorted(requested_ids - found_ids)
            raise NotFound(f"Issue type(s) not found: {', '.join(missing_ids)}")

        await ctx.session.execute(
            update(ItemIssue)
            .where(
                ItemIssue.workspace_id == ctx.workspace_id,
                ItemIssue.issue_type_id.in_(requested_ids),
            )
            .values(issue_type_id=None)
        )
        await ctx.session.execute(
            delete(WorkingSectionSupportedIssueType).where(
                WorkingSectionSupportedIssueType.workspace_id == ctx.workspace_id,
                WorkingSectionSupportedIssueType.issue_type_id.in_(requested_ids),
            )
        )
        await ctx.session.execute(
            delete(ItemCategoryIssueType).where(
                ItemCategoryIssueType.workspace_id == ctx.workspace_id,
                ItemCategoryIssueType.issue_type_id.in_(requested_ids),
            )
        )

        for issue_type in issue_types:
            issue_type.is_deleted = True
            issue_type.deleted_at = now
            issue_type.deleted_by_id = ctx.user_id

    return {}
