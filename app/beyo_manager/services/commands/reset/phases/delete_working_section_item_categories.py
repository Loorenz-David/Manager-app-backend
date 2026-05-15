from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.working_sections.working_section_item_category import (
    WorkingSectionItemCategory,
)


async def delete_working_section_item_categories(session: AsyncSession, workspace_id: str) -> None:
    """Delete all WorkingSectionItemCategory rows for workspace. Phase 2 of reset."""
    await session.execute(
        delete(WorkingSectionItemCategory).where(
            WorkingSectionItemCategory.workspace_id == workspace_id,
        )
    )
