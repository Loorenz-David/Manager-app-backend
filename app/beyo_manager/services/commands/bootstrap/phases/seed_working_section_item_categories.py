from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.services.commands.bootstrap.phases.seed_item_categories import _SEATING_CATEGORIES, _WOOD_CATEGORIES
from beyo_manager.models.tables.working_sections.working_section_item_category import WorkingSectionItemCategory

_BOTH_CATEGORY_SECTIONS: frozenset[str] = frozenset({"cleaning"})
_WOOD_ONLY_SECTIONS: frozenset[str] = frozenset({"wood fix", "ground oil", "hardwax oil"})


async def seed_working_section_item_categories(
    session: AsyncSession,
    workspace_id: str,
    section_ids: dict[str, str],
    item_category_ids: dict[str, str],
) -> None:
    for section_name, section_id in section_ids.items():
        if section_name in _BOTH_CATEGORY_SECTIONS:
            category_names = [*_SEATING_CATEGORIES, *_WOOD_CATEGORIES]
        elif section_name in _WOOD_ONLY_SECTIONS:
            category_names = _WOOD_CATEGORIES
        else:
            category_names = _SEATING_CATEGORIES

        for category_name in category_names:
            item_category_id = item_category_ids[category_name]
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
