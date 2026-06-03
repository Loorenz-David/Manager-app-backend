"""CMD: Create item issues in batch."""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.models.tables.issue_types.issue_type import IssueType
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.commands.items.requests import parse_batch_create_item_issues_request
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


class _IssueCreatePayload(Protocol):
    client_id: str | None
    issue_type_id: str | None
    step_id: str
    worker_id: str
    working_section_id: str
    item_category_id: str
    issue_type_snapshot: str
    placement_of_issue_snapshot: str | None
    intensity: int


async def _validate_issue_references_batch(
    session: AsyncSession,
    workspace_id: str,
    issues_data: list[_IssueCreatePayload],
) -> dict[str, str]:
    """Validate all FK references for a batch of issues with one query per entity type."""
    step_ids = {d.step_id for d in issues_data}
    worker_ids = {d.worker_id for d in issues_data}
    section_ids = {d.working_section_id for d in issues_data}
    category_ids = {d.item_category_id for d in issues_data}
    issue_type_ids = {d.issue_type_id for d in issues_data if d.issue_type_id is not None}

    found_steps = set(
        (await session.scalars(
            select(TaskStep.client_id).where(
                TaskStep.workspace_id == workspace_id,
                TaskStep.client_id.in_(step_ids),
                TaskStep.is_deleted.is_(False),
            )
        )).all()
    )
    if step_ids != found_steps:
        raise NotFound(f"Task step(s) not found: {', '.join(sorted(step_ids - found_steps))}")

    found_workers = set(
        (await session.scalars(
            select(User.client_id).where(User.client_id.in_(worker_ids))
        )).all()
    )
    if worker_ids != found_workers:
        raise NotFound(f"Worker(s) not found: {', '.join(sorted(worker_ids - found_workers))}")

    found_sections = set(
        (await session.scalars(
            select(WorkingSection.client_id).where(
                WorkingSection.workspace_id == workspace_id,
                WorkingSection.client_id.in_(section_ids),
                WorkingSection.is_deleted.is_(False),
            )
        )).all()
    )
    if section_ids != found_sections:
        raise NotFound(f"Working section(s) not found: {', '.join(sorted(section_ids - found_sections))}")

    found_categories = set(
        (await session.scalars(
            select(ItemCategory.client_id).where(
                ItemCategory.workspace_id == workspace_id,
                ItemCategory.client_id.in_(category_ids),
                ItemCategory.is_deleted.is_(False),
            )
        )).all()
    )
    if category_ids != found_categories:
        raise NotFound(f"Item category(ies) not found: {', '.join(sorted(category_ids - found_categories))}")

    issue_mode_map: dict[str, str] = {}
    if issue_type_ids:
        rows = (
            await session.execute(
                select(IssueType.client_id, IssueType.issue_mode).where(
                    IssueType.workspace_id == workspace_id,
                    IssueType.client_id.in_(issue_type_ids),
                    IssueType.is_deleted.is_(False),
                )
            )
        ).all()
        found_types = {row.client_id for row in rows}
        if issue_type_ids != found_types:
            raise NotFound(f"Issue type(s) not found: {', '.join(sorted(issue_type_ids - found_types))}")

        issue_mode_map = {row.client_id: row.issue_mode.value for row in rows}

    return issue_mode_map


async def _create_item_issues_in_session(
    session: AsyncSession,
    workspace_id: str,
    item_id: str,
    issues_data: list[_IssueCreatePayload],
) -> list[str]:
    issue_mode_map = await _validate_issue_references_batch(session, workspace_id, issues_data)

    created: list[ItemIssue] = []
    for issue_data in issues_data:
        issue_kwargs: dict = {}
        if issue_data.client_id is not None:
            validate_provided_client_id(issue_data.client_id, "iti")
            issue_kwargs["client_id"] = issue_data.client_id

        issue = ItemIssue(
            **issue_kwargs,
            workspace_id=workspace_id,
            item_id=item_id,
            step_id=issue_data.step_id,
            worker_id=issue_data.worker_id,
            working_section_id=issue_data.working_section_id,
            item_category_id=issue_data.item_category_id,
            issue_type_id=issue_data.issue_type_id,
            issue_type_snapshot=issue_data.issue_type_snapshot,
            issue_mode_snapshot=issue_mode_map.get(issue_data.issue_type_id) if issue_data.issue_type_id else None,
            placement_of_issue_snapshot=issue_data.placement_of_issue_snapshot,
            intensity=issue_data.intensity,
        )
        session.add(issue)
        created.append(issue)

    await session.flush()
    return [issue.client_id for issue in created]


async def batch_create_item_issues(ctx: ServiceContext) -> dict:
    request = parse_batch_create_item_issues_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        item = await ctx.session.scalar(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id == request.item_id,
                Item.is_deleted.is_(False),
            )
        )
        if item is None:
            raise NotFound("Item not found.")

        item_issue_ids = await _create_item_issues_in_session(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            item_id=request.item_id,
            issues_data=request.issues,
        )

    return {"item_issue_ids": item_issue_ids}
