from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.upholstery.condition_evaluation import evaluate_inventory_condition
from beyo_manager.domain.upholstery.enums import UpholsteryCurrencyEnum
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory

_SEED_CATEGORY_NAME = "Sample Fabrics"

_UPHOLSTERIES: list[dict[str, str]] = [
    {
        "name": "linen mist",
        "code": "LIN-MIST",
        "image_url": "https://cdn.nordisktextil.se/eyJrZXkiOiJzdG9yZV8zZjA5NzVjZi01ZjA0LTQ5NDgtYmRlMy04NTRhM2FhOGZmNDdcL2ltYWdlc1wvd1NMOWVmWDZzY1pPazhlc05Sd0dDd0pvc05Ja3FpTEYySlc4MFVFZi5qcGciLCJlZGl0cyI6eyJyZXNpemUiOnsid2lkdGgiOjEwMjQsImhlaWdodCI6MTAyNCwiZml0IjoiaW5zaWRlIn19fQ==",
        "seeded_stored_amount_meters": "24.500",
    },
    {
        "name": "velvet ember",
        "code": "VEL-EMBER",
        "image_url": "https://cdn.nordisktextil.se/eyJrZXkiOiJzdG9yZV8zZjA5NzVjZi01ZjA0LTQ5NDgtYmRlMy04NTRhM2FhOGZmNDdcL2ltYWdlc1wvUWJQclY3R3p0b1JwbFc0MTY4NTA5NTA1OC53ZWJwIiwiZWRpdHMiOnsicmVzaXplIjp7IndpZHRoIjo0MDAsImhlaWdodCI6NDAwLCJmaXQiOiJpbnNpZGUifX19",
        "seeded_stored_amount_meters": "0",
    },
    {
        "name": "oak dune",
        "code": "OAK-DUNE",
        "image_url": "https://nevotex.com/Admin/Public/GetImage.ashx?width=705&height=524&crop=5&FillCanvas=True&DoNotUpscale=true&Compression=75&image=/Files/Images/produktbilder/1008371_4.jpg",
        "seeded_stored_amount_meters": "5",
    },
    {
        "name": "stone breeze",
        "code": "STO-BREEZE",
        "image_url": "https://nevotex.com/Admin/Public/GetImage.ashx?width=705&height=524&crop=5&FillCanvas=True&DoNotUpscale=true&Compression=75&image=/Files/Images/produktbilder/1004206_4.jpg",
        "seeded_stored_amount_meters": "0",
    },
]


async def seed_upholsteries(
    session: AsyncSession,
    workspace_id: str,
    created_by_id: str | None,
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}

    existing_category = await session.scalar(
        select(UpholsteryCategory).where(
            UpholsteryCategory.workspace_id == workspace_id,
            UpholsteryCategory.name == _SEED_CATEGORY_NAME,
            UpholsteryCategory.is_deleted.is_(False),
        )
    )
    if existing_category is None:
        category = UpholsteryCategory(
            workspace_id=workspace_id,
            name=_SEED_CATEGORY_NAME,
            created_by_id=created_by_id,
        )
        session.add(category)
        await session.flush()
        category_row = category
    else:
        category_row = existing_category

    for idx, seed in enumerate(_UPHOLSTERIES):
        name = seed["name"]
        code = seed["code"]
        image_url = seed["image_url"]

        existing_upholstery = await session.scalar(
            select(Upholstery).where(
                Upholstery.workspace_id == workspace_id,
                Upholstery.name == name,
            )
        )
        if existing_upholstery is None:
            upholstery = Upholstery(
                workspace_id=workspace_id,
                name=name,
                code=code,
                image_url=image_url,
                upholstery_category_id=category_row.client_id,
                created_by_id=created_by_id,
            )
            session.add(upholstery)
            await session.flush()
            upholstery_row = upholstery
        else:
            dirty = False
            if existing_upholstery.image_url is None:
                existing_upholstery.image_url = image_url
                dirty = True
            if existing_upholstery.upholstery_category_id is None:
                existing_upholstery.upholstery_category_id = category_row.client_id
                dirty = True
            if dirty:
                await session.flush()
            upholstery_row = existing_upholstery

        existing_inventory = await session.scalar(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == workspace_id,
                UpholsteryInventory.upholstery_id == upholstery_row.client_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        if existing_inventory is None:
            seeded_stored_amount = Decimal(seed["seeded_stored_amount_meters"])
            inventory = UpholsteryInventory(
                workspace_id=workspace_id,
                upholstery_id=upholstery_row.client_id,
                currency=UpholsteryCurrencyEnum.EURO,
                inventory_condition=evaluate_inventory_condition(
                    stored=seeded_stored_amount,
                    in_need=Decimal("0"),
                    threshold=None,
                ),
                current_stored_amount_meters=seeded_stored_amount,
                created_by_id=created_by_id,
            )
            session.add(inventory)
            await session.flush()
            inventory_row = inventory
        else:
            inventory_row = existing_inventory

        result[name] = {
            "upholstery_id": upholstery_row.client_id,
            "inventory_id": inventory_row.client_id,
        }

    return result
