from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.working_sections.working_section_item_category import WorkingSectionItemCategory
from beyo_manager.services.commands.bootstrap.phases.seed_item_categories import _SEATING_CATEGORIES, _WOOD_CATEGORIES
from beyo_manager.services.commands.bootstrap.phases.seed_working_sections import (
    get_desired_bootstrap_working_section_names,
)

_BOTH_CATEGORY_SECTIONS: frozenset[str] = frozenset({"photography"})
_WOOD_ONLY_SECTIONS: frozenset[str] = frozenset({"cleaning wood", "wood fix", "ground oil", "hardwax oil"})


async def seed_working_section_item_categories(
    session: AsyncSession,
    workspace_id: str,
    section_ids: dict[str, str],
    item_category_ids: dict[str, str],
) -> None:
    desired_section_names = get_desired_bootstrap_working_section_names()
    managed_section_ids = {
        section_ids[section_name]
        for section_name in desired_section_names
        if section_name in section_ids
    }
    expected_pairs: set[tuple[str, str]] = set()

    for section_name, section_id in section_ids.items():
        if section_name in _BOTH_CATEGORY_SECTIONS:
            category_names = [*_SEATING_CATEGORIES, *_WOOD_CATEGORIES]
        elif section_name in _WOOD_ONLY_SECTIONS:
            category_names = _WOOD_CATEGORIES
        else:
            category_names = _SEATING_CATEGORIES

        for category_name in category_names:
            item_category_id = item_category_ids[category_name]
            expected_pairs.add((section_id, item_category_id))
            existing = await session.scalar(
                select(WorkingSectionItemCategory).where(
                    WorkingSectionItemCategory.workspace_id == workspace_id,
                    WorkingSectionItemCategory.working_section_id == section_id,
                    WorkingSectionItemCategory.item_category_id == item_category_id,
                )
            )
            if existing is not None:
                continue

            link = WorkingSectionItemCategory(
                workspace_id=workspace_id,
                working_section_id=section_id,
                item_category_id=item_category_id,
            )
            session.add(link)
            await session.flush()

    existing_rows = (
        await session.execute(
            select(WorkingSectionItemCategory).where(
                WorkingSectionItemCategory.workspace_id == workspace_id,
                WorkingSectionItemCategory.working_section_id.in_(managed_section_ids),
            )
        )
    ).scalars().all()
    for existing_row in existing_rows:
        pair = (existing_row.working_section_id, existing_row.item_category_id)
        if pair not in expected_pairs:
            await session.delete(existing_row)
