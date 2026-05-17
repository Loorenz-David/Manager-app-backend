"""CMD-2: Create ItemIssue - standalone command and session-level helper."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemIssueStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.services.commands.items.requests import (
    CreateItemIssueRequest,
    parse_create_item_issue_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def _create_item_issue_in_session(
    session: AsyncSession,
    workspace_id: str,
    item_id: str,
    issue_data: CreateItemIssueRequest,
    user_id: str | None,
) -> str:
    """Create one ItemIssue inside an open transaction."""
    issue = ItemIssue(
        workspace_id=workspace_id,
        item_id=item_id,
        issue_type_id=issue_data.issue_type_id,
        issue_severity_id=issue_data.issue_severity_id,
        state=ItemIssueStateEnum.PENDING,
        base_time_seconds=issue_data.base_time_seconds,
        time_multiplier=issue_data.time_multiplier,
        issue_name_snapshot=issue_data.issue_name_snapshot,
        severity_name_snapshot=issue_data.severity_name_snapshot,
        created_by_id=user_id,
    )
    session.add(issue)
    await session.flush()
    return issue.client_id


async def create_item_issue(ctx: ServiceContext) -> dict:
    """Create a standalone ItemIssue linked to an existing active item."""
    request = parse_create_item_issue_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        item_result = await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id == request.item_id,
                Item.is_deleted.is_(False),
            )
        )
        if item_result.scalar_one_or_none() is None:
            raise NotFound("Item not found.")

        issue_client_id = await _create_item_issue_in_session(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            item_id=request.item_id,
            issue_data=request,
            user_id=ctx.user_id,
        )

    return {"client_id": issue_client_id}
