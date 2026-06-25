from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory

_SEED_CATEGORY_NAME = "Sample Fabrics"

_SEEDED_UPHOLSTERY_NAMES: list[str] = [
    "linen mist",
    "velvet ember",
    "oak dune",
    "stone breeze",
]


async def delete_seeded_upholsteries(
    session: AsyncSession,
    workspace_id: str,
    deleted_by_id: str | None,
) -> None:
    now = datetime.now(timezone.utc)

    for name in _SEEDED_UPHOLSTERY_NAMES:
        upholstery = await session.scalar(
            select(Upholstery).where(
                Upholstery.workspace_id == workspace_id,
                Upholstery.name == name,
                Upholstery.is_deleted.is_(False),
            )
        )
        if upholstery is None:
            continue

        inventory = await session.scalar(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == workspace_id,
                UpholsteryInventory.upholstery_id == upholstery.client_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        if inventory is not None:
            inventory.is_deleted = True
            inventory.deleted_at = now
            inventory.deleted_by_id = deleted_by_id

        upholstery.is_deleted = True
        upholstery.deleted_at = now
        upholstery.deleted_by_id = deleted_by_id
        upholstery.list_order = None

    await session.flush()

    category = await session.scalar(
        select(UpholsteryCategory).where(
            UpholsteryCategory.workspace_id == workspace_id,
            UpholsteryCategory.name == _SEED_CATEGORY_NAME,
            UpholsteryCategory.is_deleted.is_(False),
        )
    )
    if category is not None:
        category.is_deleted = True
        category.deleted_at = now
        category.deleted_by_id = deleted_by_id

    await session.flush()
