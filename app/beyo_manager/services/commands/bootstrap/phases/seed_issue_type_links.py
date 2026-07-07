from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.items.item_category_issue_type import ItemCategoryIssueType
from beyo_manager.models.tables.working_sections.working_section_supported_issue_type import (
    WorkingSectionSupportedIssueType,
)
from beyo_manager.services.commands.bootstrap.phases.seed_issue_types import ISSUE_DEFINITIONS
from beyo_manager.services.commands.bootstrap.phases.seed_working_sections import (
    get_desired_bootstrap_working_section_names,
)


async def seed_issue_type_links(
    session: AsyncSession,
    workspace_id: str,
    issue_type_ids: dict[str, str],
    item_category_ids: dict[str, str],
    section_ids: dict[str, str],
) -> None:
    desired_section_names = get_desired_bootstrap_working_section_names()
    managed_section_ids = {
        section_ids[section_name]
        for section_name in desired_section_names
        if section_name in section_ids
    }
    expected_supported_pairs: set[tuple[str, str]] = set()

    for issue_definition in ISSUE_DEFINITIONS:
        issue_name = issue_definition["name"]
        issue_type_id = issue_type_ids.get(issue_name)
        if issue_type_id is None:
            raise ValueError(f"Unknown issue type in seed map: {issue_name!r}")

        for section_name in issue_definition["working_sections"]:
            section_id = section_ids.get(section_name)
            if section_id is None:
                raise ValueError(f"Unknown working section in seed map: {section_name!r}")
            expected_supported_pairs.add((section_id, issue_type_id))
            existing = await session.scalar(
                select(WorkingSectionSupportedIssueType).where(
                    WorkingSectionSupportedIssueType.workspace_id == workspace_id,
                    WorkingSectionSupportedIssueType.working_section_id == section_id,
                    WorkingSectionSupportedIssueType.issue_type_id == issue_type_id,
                )
            )
            if existing is None:
                session.add(
                    WorkingSectionSupportedIssueType(
                        workspace_id=workspace_id,
                        working_section_id=section_id,
                        issue_type_id=issue_type_id,
                    )
                )
                await session.flush()

        item_category_placements: dict[str, list[str]] = issue_definition["item_category_placements"]
        for category_name, placements in item_category_placements.items():
            item_category_id = item_category_ids.get(category_name)
            if item_category_id is None:
                raise ValueError(f"Unknown item category in seed map: {category_name!r}")
            for placement_of_issue in placements:
                existing = await session.scalar(
                    select(ItemCategoryIssueType).where(
                        ItemCategoryIssueType.workspace_id == workspace_id,
                        ItemCategoryIssueType.issue_type_id == issue_type_id,
                        ItemCategoryIssueType.item_category_id == item_category_id,
                        ItemCategoryIssueType.placement_of_issue == placement_of_issue,
                    )
                )
                if existing is None:
                    session.add(
                        ItemCategoryIssueType(
                            workspace_id=workspace_id,
                            issue_type_id=issue_type_id,
                            item_category_id=item_category_id,
                            placement_of_issue=placement_of_issue,
                        )
                    )
                    await session.flush()

    existing_supported_rows = (
        await session.execute(
            select(WorkingSectionSupportedIssueType).where(
                WorkingSectionSupportedIssueType.workspace_id == workspace_id,
                WorkingSectionSupportedIssueType.working_section_id.in_(managed_section_ids),
            )
        )
    ).scalars().all()
    for existing_supported_row in existing_supported_rows:
        pair = (
            existing_supported_row.working_section_id,
            existing_supported_row.issue_type_id,
        )
        if pair not in expected_supported_pairs:
            await session.delete(existing_supported_row)
