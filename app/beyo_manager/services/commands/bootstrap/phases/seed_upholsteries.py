from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.upholstery.enums import UpholsteryCurrencyEnum
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory


_UPHOLSTERIES: list[dict[str, str]] = [
    {"name": "linen mist", "code": "LIN-MIST"},
    {"name": "velvet ember", "code": "VEL-EMBER"},
]


async def seed_upholsteries(
    session: AsyncSession,
    workspace_id: str,
    created_by_id: str | None,
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}

    for idx, seed in enumerate(_UPHOLSTERIES):
        name = seed["name"]
        code = seed["code"]

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
                created_by_id=created_by_id,
            )
            session.add(upholstery)
            await session.flush()
            upholstery_row = upholstery
        else:
            upholstery_row = existing_upholstery

        existing_inventory = await session.scalar(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == workspace_id,
                UpholsteryInventory.upholstery_id == upholstery_row.client_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        if existing_inventory is None:
            seeded_stored_amount = Decimal("24.500") if idx == 0 else Decimal("0")
            inventory = UpholsteryInventory(
                workspace_id=workspace_id,
                upholstery_id=upholstery_row.client_id,
                currency=UpholsteryCurrencyEnum.EURO,
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
