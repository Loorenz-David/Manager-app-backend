from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement


async def delete_item_upholstery_requirements(session: AsyncSession, workspace_id: str) -> None:
    """Delete all ItemUpholsteryRequirement rows for workspace."""
    # Break circular FK: item_upholsteries.active_requirement_id -> item_upholstery_requirements.client_id
    await session.execute(
        update(ItemUpholstery)
        .where(ItemUpholstery.workspace_id == workspace_id)
        .values(active_requirement_id=None)
    )

    await session.execute(
        delete(ItemUpholsteryRequirement).where(
            ItemUpholsteryRequirement.workspace_id == workspace_id,
        )
    )
