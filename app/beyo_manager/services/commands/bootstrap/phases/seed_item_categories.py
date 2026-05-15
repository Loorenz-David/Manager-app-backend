from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
from beyo_manager.models.tables.items.item_category import ItemCategory

_SEATING_CATEGORIES = [
    "armchair",
    "bench",
    "chair",
    "chairs",
    "dining chair",
    "sofa",
    "stool",
]

_WOOD_CATEGORIES = [
    "bar cabinet",
    "bedside table",
    "bookshelf",
    "cabinet",
    "chest of drawer",
    "chest of drawers",
    "coffee table",
    "conference table",
    "corner cabinet",
    "dining table",
    "hall table",
    "highboard",
    "lamp",
    "mirror",
    "nest of tables",
    "plant stand",
    "poster",
    "round table",
    "secretary",
    "serving trolley",
    "side table",
    "sideboard",
    "small table",
    "shelving",
    "sewing table",
    "trolley",
    "writing desk",
]


async def seed_item_categories(session: AsyncSession, workspace_id: str) -> dict[str, str]:
    category_ids: dict[str, str] = {}
    pairs = [
        (name, ItemMajorCategoryEnum.SEAT) for name in _SEATING_CATEGORIES
    ] + [
        (name, ItemMajorCategoryEnum.WOOD) for name in _WOOD_CATEGORIES
    ]
    for name, major_category in pairs:
        existing = await session.scalar(
            select(ItemCategory).where(
                ItemCategory.workspace_id == workspace_id,
                ItemCategory.name == name,
            )
        )
        if existing is not None:
            category_ids[name] = existing.client_id
            continue

        category = ItemCategory(
            workspace_id=workspace_id,
            name=name,
            major_category=major_category,
        )
        session.add(category)
        await session.flush()
        category_ids[name] = category.client_id

    return category_ids
