"""CMD: Soft-delete item issues in batch."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.services.commands.items.requests import parse_batch_delete_item_issues_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def batch_delete_item_issues(ctx: ServiceContext) -> dict:
    request = parse_batch_delete_item_issues_request(ctx.incoming_data)
    item_id: str | None = ctx.incoming_data.get("item_id")

    requested_ids = {entry.item_issue_id for entry in request.issues}
    now = datetime.now(timezone.utc)

    async with maybe_begin(ctx.session):
        where_clauses = [
            ItemIssue.workspace_id == ctx.workspace_id,
            ItemIssue.client_id.in_(requested_ids),
            ItemIssue.is_deleted.is_(False),
        ]
        if item_id:
            where_clauses.append(ItemIssue.item_id == item_id)

        result = await ctx.session.execute(
            select(ItemIssue).where(*where_clauses)
        )
        issues = result.scalars().all()

        found_ids = {issue.client_id for issue in issues}
        if found_ids != requested_ids:
            missing_ids = sorted(requested_ids - found_ids)
            raise NotFound(f"Item issue(s) not found: {', '.join(missing_ids)}")

        for issue in issues:
            issue.is_deleted = True
            issue.deleted_at = now
            issue.deleted_by_id = ctx.user_id

    return {}
