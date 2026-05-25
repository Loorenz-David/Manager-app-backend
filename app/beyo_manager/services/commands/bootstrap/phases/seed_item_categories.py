from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
from beyo_manager.models.tables.items.item_category import ItemCategory

_SEATING_CATEGORIES = [
    "Armchair",
    "Bench",
    "Dining Chair",
    "Sofa",
    "Stool",
]

_WOOD_CATEGORIES = [
    "Conference Table",
    "Chest Of Drawers",
    "Serving Trolley",
    "Corner Cabinet",
    "Nest Of Tables",
    "Bedside Table",
    "Writing Desk",
    "Sewing Table",
    "Dining Table",
    "Coffee Table",
    "Plant Stand",
    "Bar Cabinet",
    "Small Side Table",
    "Hall Table",
    "Side Table",
    "Secretary Cabinet",
    "Highboard",
    "Sideboard",
    "Bookshelf",
    "Shelving",
    "Cabinet",
    "Mirror",
    "Poster",
    "Lamp",
]

_CATEGORY_IMAGE_URLS = {
    "Armchair": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/armchair.webp",
    "Bar Cabinet": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/bar_cabinet.webp",
    "Bedside Table": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/bed_side_table.webp",
    "Bench": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/bench%201.webp",
    "Bookshelf": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/bookshelf.webp",
    "Cabinet": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/cabinet.webp",
    "Chest Of Drawers": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/chest_of_drawer.webp",
    "Coffee Table": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/coffee_table.webp",
    "Conference Table": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/conference_table.webp",
    "Corner Cabinet": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/corner_cabinet.webp",
    "Dining Chair": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/dining_chair%201.webp",
    "Dining Table": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/dining_table.webp",
    "Hall Table": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/coffee_table.webp",
    "Highboard": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/highboard.webp",
    "Lamp": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/lamp.webp",
    "Mirror": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/mirror.webp",
    "Nest Of Tables": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/nest_of_tables.webp",
    "Plant Stand": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/plant_stand.webp",
    "Poster": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/poster.webp",
    "Secretary Cabinet": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/secretary_table.webp",
    "Serving Trolley": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/serving_trolley.webp",
    "Sewing Table": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/sewing_table.webp",
    "Shelving": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/shelving_system.webp",
    "Side Table": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/sofa_table.webp",
    "Sideboard": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/sideboard.webp",
    "Small Side Table": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/small_table.webp",
    "Sofa": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/sofa%201.webp",
    "Stool": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/stool%201.webp",
    "Writing Desk": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/writing_desk%201.webp",
}


async def seed_item_categories(session: AsyncSession, workspace_id: str) -> dict[str, str]:
    category_ids: dict[str, str] = {}
    pairs = [
        (name, ItemMajorCategoryEnum.SEAT, _CATEGORY_IMAGE_URLS.get(name)) for name in _SEATING_CATEGORIES
    ] + [
        (name, ItemMajorCategoryEnum.WOOD, _CATEGORY_IMAGE_URLS.get(name)) for name in _WOOD_CATEGORIES
    ]
    for name, major_category, image_url in pairs:
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
            image_url=image_url,
            major_category=major_category,
        )
        session.add(category)
        await session.flush()
        category_ids[name] = category.client_id

    return category_ids
