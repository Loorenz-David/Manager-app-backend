"""CMD: Soft-delete an ItemIssue."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.services.commands.items.requests import parse_delete_item_issue_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def delete_item_issue(ctx: ServiceContext) -> dict:
    request = parse_delete_item_issue_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(ItemIssue).where(
                ItemIssue.workspace_id == ctx.workspace_id,
                ItemIssue.client_id == request.client_id,
                ItemIssue.item_id == request.item_id,
                ItemIssue.is_deleted.is_(False),
            )
        )
        issue = result.scalar_one_or_none()
        if issue is None:
            raise NotFound("Item issue not found.")

        issue.is_deleted = True
        issue.deleted_at = datetime.now(timezone.utc)
        issue.deleted_by_id = ctx.user_id

    return {}
