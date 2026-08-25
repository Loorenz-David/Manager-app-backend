"""CMD-1: Create ItemUpholstery with initial requirement."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.items.enums import (
    ItemUpholsteryRequirementSourceEnum,
    ItemUpholsteryRequirementStateEnum,
    ItemUpholsterySourceEnum,
)
from beyo_manager.domain.items.upholstery_selection import (
    has_positive_amount_meters,
    should_defer_requirement_creation,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import (
    build_create_message,
    build_delete_message,
)
from beyo_manager.services.commands.items.requests import parse_create_item_upholstery_request
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.commands.upholstery._inventory_mutations import check_and_inject_need
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


def _validate_internal_upholstery_selection(
    source: ItemUpholsterySourceEnum,
    upholstery_id: str | None,
    amount_meters: Decimal | None,
    *,
    missing_id_error: str,
) -> None:
    if source == ItemUpholsterySourceEnum.INTERNAL and upholstery_id is None and not has_positive_amount_meters(amount_meters):
        raise ValidationError(missing_id_error)


async def _create_initial_requirement_for_item_upholstery(
    session: AsyncSession,
    workspace_id: str,
    item_upholstery: ItemUpholstery,
    amount_meters: Decimal | None,
    source: ItemUpholsterySourceEnum,
    user_id: str | None,
) -> str:
    """Create and attach a new active requirement for an existing ItemUpholstery."""
    if amount_meters is not None and source != ItemUpholsterySourceEnum.CUSTOMER:
        inv_result = await check_and_inject_need(
            session=session,
            workspace_id=workspace_id,
            upholstery_id=item_upholstery.upholstery_id,
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
            item_upholstery_id=item_upholstery.client_id,
            upholstery_inventory_id=inv_result["inventory_id"],
            amount_meters=amount_meters,
            source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
            state=state,
            created_by_id=user_id,
        )
    elif amount_meters is None:
        req = ItemUpholsteryRequirement(
            workspace_id=workspace_id,
            item_upholstery_id=item_upholstery.client_id,
            upholstery_inventory_id=None,
            amount_meters=None,
            source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
            state=ItemUpholsteryRequirementStateEnum.MISSING_QUANTITY,
            created_by_id=user_id,
        )
    else:
        req = ItemUpholsteryRequirement(
            workspace_id=workspace_id,
            item_upholstery_id=item_upholstery.client_id,
            upholstery_inventory_id=None,
            amount_meters=amount_meters,
            source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
            state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
            created_by_id=user_id,
        )

    session.add(req)
    await session.flush()
    item_upholstery.active_requirement_id = req.client_id
    return req.client_id


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
    client_id: str | None = None,
) -> str:
    """Create ItemUpholstery and its initial requirement inside an open transaction."""
    iup_kwargs: dict[str, str] = {}
    if client_id is not None:
        validate_provided_client_id(client_id, "iup")
        existing = await session.get(ItemUpholstery, client_id)
        if existing is not None:
            raise ConflictError("Provided client_id is already in use.")
        iup_kwargs["client_id"] = client_id

    iup = ItemUpholstery(
        **iup_kwargs,
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

    if not should_defer_requirement_creation(source, upholstery_id, amount_meters):
        await _create_initial_requirement_for_item_upholstery(
            session=session,
            workspace_id=workspace_id,
            item_upholstery=iup,
            amount_meters=amount_meters,
            source=source,
            user_id=user_id,
        )
    return iup.client_id


async def ensure_item_upholstery_in_session(
    ctx: ServiceContext,
    *,
    item_id: str,
    data: dict,
) -> tuple[str, bool]:
    """Create or update the current item upholstery inside the caller's transaction.

    A non-terminal upholstery context is reused. Completed or failed contexts are
    archived and replaced with a new context so their sourcing history remains
    immutable while the item still has at most one current context.
    """
    item_result = await ctx.session.execute(
        select(Item)
        .where(
            Item.workspace_id == ctx.workspace_id,
            Item.client_id == item_id,
            Item.is_deleted.is_(False),
        )
        .with_for_update()
    )
    if item_result.scalar_one_or_none() is None:
        raise NotFound("Item not found.")

    result = await ctx.session.execute(
        select(ItemUpholstery)
        .where(
            ItemUpholstery.workspace_id == ctx.workspace_id,
            ItemUpholstery.item_id == item_id,
            ItemUpholstery.is_deleted.is_(False),
        )
        .order_by(ItemUpholstery.created_at.asc())
        .with_for_update()
    )
    current_rows = result.scalars().all()
    if len(current_rows) > 1:
        raise ConflictError(
            "Item has multiple active upholstery contexts; resolve the duplicate data before creating another."
        )

    current = current_rows[0] if current_rows else None
    requested_client_id = data.get("client_id")
    if current is None:
        return (
            await _create_item_upholstery_in_session(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                item_id=item_id,
                upholstery_id=data.get("upholstery_id"),
                name=data.get("name"),
                code=data.get("code"),
                amount_meters=data.get("amount_meters"),
                source=data["source"],
                time_to_fix_in_seconds=data.get("time_to_fix_in_seconds"),
                user_id=ctx.user_id,
                client_id=requested_client_id,
            ),
            True,
        )

    if requested_client_id is not None and requested_client_id != current.client_id:
        raise ConflictError(
            "The requested item upholstery does not match the current item upholstery."
        )

    if current.active_requirement_id is not None:
        requirement_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.client_id == current.active_requirement_id,
                ItemUpholsteryRequirement.item_upholstery_id == current.client_id,
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        active_requirement = requirement_result.scalar_one_or_none()
        if active_requirement is None:
            raise ConflictError("Current item upholstery has no active requirement row.")

        if active_requirement.state in {
            ItemUpholsteryRequirementStateEnum.COMPLETED,
            ItemUpholsteryRequirementStateEnum.FAILED,
        }:
            now = datetime.now(timezone.utc)
            current.is_deleted = True
            current.deleted_at = now
            current.deleted_by_id = ctx.user_id
            username = ctx.identity.get("username")
            upholstery_target = f"upholstery '{current.name}'" if current.name else "upholstery"
            await _create_history_record_in_session(
                session=ctx.session,
                entity_type=HistoryRecordEntityTypeEnum.ITEM_UPHOLSTERY,
                entity_client_id=current.client_id,
                change_type=HistoryRecordChangeTypeEnum.DELETED,
                description=build_delete_message(username, upholstery_target, "item"),
                field_name=None,
                from_value=None,
                to_value=None,
                created_by_id=ctx.user_id,
                username_snapshot=username,
            )
            return (
                await _create_item_upholstery_in_session(
                    session=ctx.session,
                    workspace_id=ctx.workspace_id,
                    item_id=item_id,
                    upholstery_id=data.get("upholstery_id"),
                    name=data.get("name"),
                    code=data.get("code"),
                    amount_meters=data.get("amount_meters"),
                    source=data["source"],
                    time_to_fix_in_seconds=data.get("time_to_fix_in_seconds"),
                    user_id=ctx.user_id,
                    client_id=None,
                ),
                True,
            )

    update_data = {"client_id": current.client_id}
    update_data.update(
        {
            key: value
            for key, value in data.items()
            if key in {
                "upholstery_id",
                "source",
                "name",
                "code",
                "amount_meters",
                "time_to_fix_in_seconds",
            }
        }
    )
    from beyo_manager.services.commands.items.requests import parse_update_item_upholstery_request
    from beyo_manager.services.commands.items.update_and_delete_item_upholstery import (
        _update_item_upholstery_in_session,
    )

    previous_upholstery_id = current.upholstery_id
    previous_source = current.source
    previous_amount = current.amount_meters
    await _update_item_upholstery_in_session(
        ctx,
        parse_update_item_upholstery_request(update_data),
    )

    selection_changed = (
        "upholstery_id" in update_data
        and update_data["upholstery_id"] != previous_upholstery_id
    ) or (
        "source" in update_data
        and update_data["source"] != previous_source
    )
    if (
        not selection_changed
        and "amount_meters" in update_data
        and update_data["amount_meters"] is not None
        and current.active_requirement_id is not None
        and update_data["amount_meters"] != previous_amount
    ):
        from beyo_manager.services.commands.items.update_requirement_quantity import (
            update_requirement_quantity,
        )

        quantity_ctx = ServiceContext(
            incoming_data={
                "item_upholstery_id": current.client_id,
                "amount_meters": update_data["amount_meters"],
            },
            identity=ctx.identity,
            session=ctx.session,
        )
        await update_requirement_quantity(quantity_ctx)
    return current.client_id, False


async def create_item_upholstery(ctx: ServiceContext) -> dict:
    """Create ItemUpholstery and initial ItemUpholsteryRequirement (standalone command)."""
    request = parse_create_item_upholstery_request(ctx.incoming_data)
    upholstery_name = request.name
    upholstery_code = request.code

    _validate_internal_upholstery_selection(
        request.source,
        request.upholstery_id,
        request.amount_meters,
        missing_id_error="upholstery_id is required when source is INTERNAL unless positive amount_meters is provided.",
    )

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

        if request.source == ItemUpholsterySourceEnum.INTERNAL and request.upholstery_id is not None:
            upholstery_result = await ctx.session.execute(
                select(Upholstery).where(
                    Upholstery.workspace_id == ctx.workspace_id,
                    Upholstery.client_id == request.upholstery_id,
                    Upholstery.is_deleted.is_(False),
                )
            )
            upholstery = upholstery_result.scalar_one_or_none()
            if upholstery is None:
                raise NotFound("Upholstery not found.")
            if upholstery_name is None:
                upholstery_name = upholstery.name
            if upholstery_code is None:
                upholstery_code = upholstery.code

        iup_client_id, created = await ensure_item_upholstery_in_session(
            ctx,
            item_id=request.item_id,
            data={
                "client_id": request.client_id,
                "upholstery_id": request.upholstery_id,
                "name": upholstery_name,
                "code": upholstery_code,
                "amount_meters": request.amount_meters,
                "source": request.source,
                "time_to_fix_in_seconds": request.time_to_fix_in_seconds,
            },
        )

        if created:
            username = ctx.identity.get("username")
            upholstery_target = f"upholstery '{request.name}'" if request.name else "upholstery"
            await _create_history_record_in_session(
                session=ctx.session,
                entity_type=HistoryRecordEntityTypeEnum.ITEM_UPHOLSTERY,
                entity_client_id=iup_client_id,
                change_type=HistoryRecordChangeTypeEnum.CREATED,
                description=build_create_message(username, upholstery_target, "item"),
                field_name=None,
                from_value=None,
                to_value=None,
                created_by_id=ctx.user_id,
                username_snapshot=username,
            )

    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="item:updated",
            client_id=request.item_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
        WorkspaceEvent(
            event_name="item:upholstery-created" if created else "item:upholstery-updated",
            client_id=iup_client_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ])
    return {"client_id": iup_client_id}
