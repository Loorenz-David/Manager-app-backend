"""CMD: Soft-delete ItemIssues in batch."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.services.commands.items.requests import parse_delete_item_issues_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def delete_item_issues(ctx: ServiceContext) -> dict:
    request = parse_delete_item_issues_request(ctx.incoming_data)

    requested_issue_ids = set(request.issue_ids)
    now = datetime.now(timezone.utc)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(ItemIssue).where(
                ItemIssue.workspace_id == ctx.workspace_id,
                ItemIssue.item_id == request.item_id,
                ItemIssue.client_id.in_(requested_issue_ids),
                ItemIssue.is_deleted.is_(False),
            )
        )
        issues = result.scalars().all()

        found_issue_ids = {issue.client_id for issue in issues}
        if found_issue_ids != requested_issue_ids:
            missing_issue_ids = sorted(requested_issue_ids - found_issue_ids)
            raise NotFound(f"Item issue(s) not found: {', '.join(missing_issue_ids)}")

        for issue in issues:
            issue.is_deleted = True
            issue.deleted_at = now
            issue.deleted_by_id = ctx.user_id

    return {}
