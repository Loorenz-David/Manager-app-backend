from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
from beyo_manager.models.tables.items.item_category import ItemCategory

_SEATING_CATEGORIES = [
    "Dining Chairs",
    "Easy Chairs",
    "Armchairs",
    "Sofas",
    "Stools",
    "Seating Benches",
]

_WOOD_CATEGORIES = [
    "Dining Tables",
    "Bedside Tables",
    "Coffee Tables",
    "Side Tables",
    "Hallway Tables",
    "Writing Desks",
    "Nest Of Tables",
    "Sideboards",
    "Highboards",
    "Bookshelves",
    "Shelving Units",
    "Chests Of Drawers",
    "Secretary Cabinets",
    "Bar Cabinets",
    "Wardrobes",
    "Storage Cabinets",
    "Posters",
    "Mirrors",
    "Porcelain",
    "Carpets",
    "Lamps",
]

_CATEGORY_IMAGE_URLS = {
    "Dining Chairs": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/dining_chair%201.webp",
    "Easy Chairs": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/armchair.webp",
    "Armchairs": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/armchair.webp",
    "Sofas": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/sofa%201.webp",
    "Stools": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/stool%201.webp",
    "Seating Benches": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/bench%201.webp",
    "Dining Tables": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/dining_table.webp",
    "Bedside Tables": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/bed_side_table.webp",
    "Coffee Tables": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/coffee_table.webp",
    "Side Tables": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/sofa_table.webp",
    "Hallway Tables": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/coffee_table.webp",
    "Writing Desks": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/writing_desk%201.webp",
    "Nest Of Tables": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/nest_of_tables.webp",
    "Sideboards": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/sideboard.webp",
    "Highboards": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/highboard.webp",
    "Bookshelves": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/bookshelf.webp",
    "Sheving Units": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/shelving_system.webp",
    "Chests Of Drawers": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/chest_of_drawer.webp",
    "Secretary Cabinets": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/secretary_table.webp",
    "Bar Cabinets": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/bar_cabinet.webp",
    "Wardrobes": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/cabinet.webp",
    "Storage Cabinets": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/cabinet.webp",
    "Posters": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/poster.webp",
    "Mirrors": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/mirror.webp",
    "Porcelain": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/cabinet.webp",
    "Carpets": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/poster.webp",
    "Lamps": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/item_categories/lamp.webp",
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
