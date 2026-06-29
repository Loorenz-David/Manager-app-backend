from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.upholstery.supplier import Supplier
from beyo_manager.models.tables.upholstery.upholstery_supplier_link import UpholsterySupplierLink


async def load_supplier_names_by_upholstery_ids(
    session: AsyncSession,
    workspace_id: str,
    upholstery_ids: list[str],
) -> dict[str, str]:
    if not upholstery_ids:
        return {}

    result = await session.execute(
        select(UpholsterySupplierLink.upholstery_id, Supplier.name)
        .select_from(UpholsterySupplierLink)
        .join(
            Supplier,
            and_(
                Supplier.client_id == UpholsterySupplierLink.supplier_id,
                Supplier.workspace_id == workspace_id,
                Supplier.is_deleted.is_(False),
            ),
        )
        .where(
            UpholsterySupplierLink.workspace_id == workspace_id,
            UpholsterySupplierLink.upholstery_id.in_(upholstery_ids),
            UpholsterySupplierLink.is_deleted.is_(False),
        )
        .order_by(
            UpholsterySupplierLink.upholstery_id.asc(),
            UpholsterySupplierLink.preferred.desc(),
            UpholsterySupplierLink.priority_order.asc().nulls_last(),
            UpholsterySupplierLink.created_at.asc(),
        )
    )

    supplier_names: dict[str, str] = {}
    for upholstery_id, supplier_name in result.all():
        if upholstery_id not in supplier_names:
            supplier_names[upholstery_id] = supplier_name

    return supplier_names


async def load_supplier_name_for_upholstery(
    session: AsyncSession,
    workspace_id: str,
    upholstery_id: str,
) -> str | None:
    supplier_names = await load_supplier_names_by_upholstery_ids(
        session=session,
        workspace_id=workspace_id,
        upholstery_ids=[upholstery_id],
    )
    return supplier_names.get(upholstery_id)
