"""CMD-1: Create ItemUpholstery with initial requirement."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import (
    ItemUpholsteryRequirementSourceEnum,
    ItemUpholsteryRequirementStateEnum,
    ItemUpholsterySourceEnum,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.commands.items.requests import parse_create_item_upholstery_request
from beyo_manager.services.commands.upholstery._inventory_mutations import check_and_inject_need
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def _create_item_upholstery_in_session(
    session: AsyncSession,
    workspace_id: str,
    item_id: str,
    upholstery_id: str | None,
    name: str | None,
    code: str | None,
    amount_meters: Decimal | None,
    source: ItemUpholsterySourceEnum,
    time_to_fix_in_seconds: int | None,
    user_id: str | None,
) -> str:
    """Create ItemUpholstery and its initial requirement inside an open transaction."""
    iup = ItemUpholstery(
        workspace_id=workspace_id,
        item_id=item_id,
        upholstery_id=upholstery_id,
        name=name,
        code=code,
        amount_meters=amount_meters,
        source=source,
        time_to_fix_in_seconds=time_to_fix_in_seconds,
        created_by_id=user_id,
    )
    session.add(iup)
    await session.flush()

    if amount_meters is not None and source != ItemUpholsterySourceEnum.CUSTOMER:
        inv_result = await check_and_inject_need(
            session=session,
            workspace_id=workspace_id,
            upholstery_id=upholstery_id,
            quantity=amount_meters,
            inject=True,
        )
        state = (
            ItemUpholsteryRequirementStateEnum.AVAILABLE
            if inv_result["sufficient"]
            else ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
        )
        req = ItemUpholsteryRequirement(
            workspace_id=workspace_id,
            item_upholstery_id=iup.client_id,
            upholstery_inventory_id=inv_result["inventory_id"],
            amount_meters=amount_meters,
            source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
            state=state,
            created_by_id=user_id,
        )
    elif amount_meters is None:
        req = ItemUpholsteryRequirement(
            workspace_id=workspace_id,
            item_upholstery_id=iup.client_id,
            upholstery_inventory_id=None,
            amount_meters=None,
            source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
            state=ItemUpholsteryRequirementStateEnum.MISSING_QUANTITY,
            created_by_id=user_id,
        )
    else:
        req = ItemUpholsteryRequirement(
            workspace_id=workspace_id,
            item_upholstery_id=iup.client_id,
            upholstery_inventory_id=None,
            amount_meters=amount_meters,
            source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
            state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
            created_by_id=user_id,
        )

    session.add(req)
    await session.flush()
    iup.active_requirement_id = req.client_id
    return iup.client_id


async def create_item_upholstery(ctx: ServiceContext) -> dict:
    """Create ItemUpholstery and initial ItemUpholsteryRequirement (standalone command)."""
    request = parse_create_item_upholstery_request(ctx.incoming_data)

    if request.upholstery_id is None and request.source != ItemUpholsterySourceEnum.CUSTOMER:
        raise ValidationError("upholstery_id is required when source is not CUSTOMER.")

    async with maybe_begin(ctx.session):
        item_result = await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id == request.item_id,
                Item.is_deleted.is_(False),
            )
        )
        if item_result.scalar_one_or_none() is None:
            raise NotFound("Item not found.")

        iup_client_id = await _create_item_upholstery_in_session(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            item_id=request.item_id,
            upholstery_id=request.upholstery_id,
            name=request.name,
            code=request.code,
            amount_meters=request.amount_meters,
            source=request.source,
            time_to_fix_in_seconds=request.time_to_fix_in_seconds,
            user_id=ctx.user_id,
        )

    return {"client_id": iup_client_id}
