from decimal import Decimal
from uuid import uuid4

import pytest

from beyo_manager.domain.items.enums import (
    ItemStateEnum,
    ItemUpholsteryRequirementSourceEnum,
    ItemUpholsteryRequirementStateEnum,
    ItemUpholsterySourceEnum,
)
from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.items.update_and_delete_item_upholstery import (
    delete_item_upholstery,
)
from beyo_manager.services.context import ServiceContext


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


def _ctx(db_session, *, workspace_id: str, user_id: str, client_id: str) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "username": "delete-upholstery-user",
            "role_name": "manager",
        },
        incoming_data={"client_id": client_id},
        session=db_session,
    )


async def _seed_workspace(db_session):
    suffix = uuid4().hex[:10]
    user = User(
        client_id=f"usr_{suffix}",
        username=f"delete-iup-user-{suffix}",
        email=f"delete-iup-user-{suffix}@example.com",
        password="hashed",
    )
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Delete-IUP workspace {suffix}")
    db_session.add_all([user, workspace])
    await db_session.flush()
    return workspace, user, suffix


async def _seed_item_upholstery(
    db_session,
    *,
    workspace: Workspace,
    user: User,
    suffix: str,
    state: ItemUpholsteryRequirementStateEnum | None,
    amount: Decimal | None = Decimal("2.000"),
    stored: Decimal = Decimal("0"),
    in_need: Decimal = Decimal("0"),
    in_use: Decimal = Decimal("0"),
):
    upholstery = Upholstery(
        client_id=f"uph_{suffix}",
        workspace_id=workspace.client_id,
        name=f"Delete-IUP upholstery {suffix}",
        code=f"DELETE-IUP-{suffix}",
    )
    inventory = UpholsteryInventory(
        client_id=f"uin_{suffix}",
        workspace_id=workspace.client_id,
        upholstery_id=upholstery.client_id,
        current_stored_amount_meters=stored,
        current_amount_in_need_meters=in_need,
        current_amount_in_use_meters=in_use,
        current_amount_ordered_meters=Decimal("0"),
        total_upholstery_used_meters=Decimal("0"),
        total_upholstery_used_inventory_meters=Decimal("0"),
        total_upholstery_used_surplus_meters=Decimal("0"),
        total_upholstery_surplus_meters=Decimal("0"),
        inventory_condition=UpholsteryInventoryConditionEnum.OUT_OF_STOCK,
    )
    item = Item(
        client_id=f"itm_{suffix}",
        workspace_id=workspace.client_id,
        article_number=f"DELETE-IUP-{suffix}",
        state=ItemStateEnum.PENDING,
        quantity=1,
    )
    db_session.add_all([upholstery, inventory, item])
    await db_session.flush()

    item_upholstery = ItemUpholstery(
        client_id=f"iup_{suffix}",
        workspace_id=workspace.client_id,
        item_id=item.client_id,
        upholstery_id=upholstery.client_id,
        name=upholstery.name,
        code=upholstery.code,
        amount_meters=amount,
        source=ItemUpholsterySourceEnum.INTERNAL,
        created_by_id=user.client_id,
    )
    db_session.add(item_upholstery)
    await db_session.flush()

    requirement = None
    if state is not None:
        requirement = ItemUpholsteryRequirement(
            client_id=f"iur_{suffix}",
            workspace_id=workspace.client_id,
            item_upholstery_id=item_upholstery.client_id,
            upholstery_inventory_id=inventory.client_id,
            amount_meters=amount,
            source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
            state=state,
            created_by_id=user.client_id,
        )
        db_session.add(requirement)
        await db_session.flush()
        item_upholstery.active_requirement_id = requirement.client_id
        await db_session.flush()

    return item_upholstery, requirement, inventory


async def _capture_events(monkeypatch):
    dispatched = []

    async def _fake_dispatch(events):
        dispatched.extend(events)

    monkeypatch.setattr(
        "beyo_manager.services.commands.items.update_and_delete_item_upholstery.event_bus.dispatch",
        _fake_dispatch,
    )
    return dispatched


async def test_delete_item_upholstery_cancels_ordered_requirement_and_reverts_need(
    db_session, monkeypatch
):
    workspace, user, suffix = await _seed_workspace(db_session)
    item_upholstery, requirement, inventory = await _seed_item_upholstery(
        db_session,
        workspace=workspace,
        user=user,
        suffix=suffix,
        state=ItemUpholsteryRequirementStateEnum.ORDERED,
        amount=Decimal("6.000"),
        in_need=Decimal("6.000"),
    )
    dispatched = await _capture_events(monkeypatch)

    result = await delete_item_upholstery(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            client_id=item_upholstery.client_id,
        )
    )
    await db_session.refresh(item_upholstery)
    await db_session.refresh(requirement)
    await db_session.refresh(inventory)

    assert result == {}
    assert item_upholstery.is_deleted is True
    assert requirement.state == ItemUpholsteryRequirementStateEnum.FAILED
    assert requirement.failed_at is not None
    assert inventory.current_amount_in_need_meters == Decimal("0.000")
    assert [event.event_name for event in dispatched] == [
        "item:updated",
        "item:upholstery-deleted",
    ]


async def test_delete_item_upholstery_cancels_in_use_requirement_and_restores_stock(
    db_session, monkeypatch
):
    workspace, user, suffix = await _seed_workspace(db_session)
    item_upholstery, requirement, inventory = await _seed_item_upholstery(
        db_session,
        workspace=workspace,
        user=user,
        suffix=suffix,
        state=ItemUpholsteryRequirementStateEnum.IN_USE,
        amount=Decimal("3.000"),
        stored=Decimal("0"),
        in_use=Decimal("3.000"),
    )
    await _capture_events(monkeypatch)

    await delete_item_upholstery(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            client_id=item_upholstery.client_id,
        )
    )
    await db_session.refresh(requirement)
    await db_session.refresh(inventory)

    assert requirement.state == ItemUpholsteryRequirementStateEnum.FAILED
    assert inventory.current_amount_in_use_meters == Decimal("0.000")
    assert inventory.current_stored_amount_meters == Decimal("3.000")


async def test_delete_item_upholstery_blocks_when_requirement_completed(
    db_session, monkeypatch
):
    workspace, user, suffix = await _seed_workspace(db_session)
    item_upholstery, requirement, inventory = await _seed_item_upholstery(
        db_session,
        workspace=workspace,
        user=user,
        suffix=suffix,
        state=ItemUpholsteryRequirementStateEnum.COMPLETED,
        amount=Decimal("2.000"),
    )
    await _capture_events(monkeypatch)

    with pytest.raises(ConflictError, match="Cannot delete upholstery after requirement completion."):
        await delete_item_upholstery(
            _ctx(
                db_session,
                workspace_id=workspace.client_id,
                user_id=user.client_id,
                client_id=item_upholstery.client_id,
            )
        )

    await db_session.refresh(item_upholstery)
    await db_session.refresh(requirement)
    assert item_upholstery.is_deleted is False
    assert requirement.state == ItemUpholsteryRequirementStateEnum.COMPLETED


async def test_delete_item_upholstery_without_active_requirement_succeeds(
    db_session, monkeypatch
):
    workspace, user, suffix = await _seed_workspace(db_session)
    item_upholstery, requirement, _ = await _seed_item_upholstery(
        db_session,
        workspace=workspace,
        user=user,
        suffix=suffix,
        state=None,
    )
    await _capture_events(monkeypatch)

    result = await delete_item_upholstery(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            client_id=item_upholstery.client_id,
        )
    )
    await db_session.refresh(item_upholstery)

    assert result == {}
    assert item_upholstery.is_deleted is True
    assert requirement is None
