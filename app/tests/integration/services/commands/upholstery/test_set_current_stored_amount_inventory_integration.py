from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.items.enums import (
    ItemStateEnum,
    ItemUpholsteryRequirementSourceEnum,
    ItemUpholsteryRequirementStateEnum,
    ItemUpholsterySourceEnum,
)
from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.upholstery.set_current_stored_amount_inventory import (
    set_current_stored_amount_inventory,
)
from beyo_manager.services.context import ServiceContext


def _ctx(db_session, *, workspace_id: str, user_id: str, client_id: str, stored: str) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": user_id, "role_name": "manager"},
        incoming_data={
            "client_id": client_id,
            "current_stored_amount_meters": Decimal(stored),
        },
        session=db_session,
    )


async def _seed_inventory_graph(db_session):
    suffix = uuid4().hex[:8]
    workspace_id = f"ws_{suffix}"
    user_id = f"usr_{suffix}"
    upholstery_id = f"uph_{suffix}"
    inventory_id = f"uin_{suffix}"
    item_one_id = f"itm_{suffix}_1"
    item_two_id = f"itm_{suffix}_2"
    item_upholstery_one_id = f"iup_{suffix}_1"
    item_upholstery_two_id = f"iup_{suffix}_2"

    workspace = Workspace(client_id=workspace_id, name="Test workspace")
    user = User(
        client_id=user_id,
        username=f"test-user-{suffix}",
        email=f"test-{suffix}@example.com",
        password="hashed",
    )
    upholstery = Upholstery(
        client_id=upholstery_id,
        workspace_id=workspace.client_id,
        name="Blue velvet",
    )
    inventory = UpholsteryInventory(
        client_id=inventory_id,
        workspace_id=workspace.client_id,
        upholstery_id=upholstery.client_id,
        current_stored_amount_meters=Decimal("2.000"),
        current_amount_in_need_meters=Decimal("5.000"),
        current_amount_in_use_meters=Decimal("0.000"),
        current_amount_ordered_meters=Decimal("0.000"),
        total_upholstery_used_meters=Decimal("0.000"),
        total_upholstery_used_inventory_meters=Decimal("0.000"),
        total_upholstery_used_surplus_meters=Decimal("0.000"),
        total_upholstery_surplus_meters=Decimal("0.000"),
        inventory_condition=UpholsteryInventoryConditionEnum.OUT_OF_STOCK,
    )
    item_one = Item(
        client_id=item_one_id,
        workspace_id=workspace.client_id,
        state=ItemStateEnum.PENDING,
        quantity=1,
    )
    item_two = Item(
        client_id=item_two_id,
        workspace_id=workspace.client_id,
        state=ItemStateEnum.PENDING,
        quantity=1,
    )
    item_upholstery_one = ItemUpholstery(
        client_id=item_upholstery_one_id,
        workspace_id=workspace.client_id,
        item_id=item_one.client_id,
        upholstery_id=upholstery.client_id,
        source=ItemUpholsterySourceEnum.INTERNAL,
    )
    item_upholstery_two = ItemUpholstery(
        client_id=item_upholstery_two_id,
        workspace_id=workspace.client_id,
        item_id=item_two.client_id,
        upholstery_id=upholstery.client_id,
        source=ItemUpholsterySourceEnum.INTERNAL,
    )

    db_session.add_all(
        [
            workspace,
            user,
            upholstery,
            inventory,
            item_one,
            item_two,
            item_upholstery_one,
            item_upholstery_two,
        ]
    )
    await db_session.flush()

    return workspace, user, inventory


@pytest.mark.integration
async def test_set_current_stored_amount_inventory_promotes_expected_candidates(db_session, monkeypatch):
    workspace, user, inventory = await _seed_inventory_graph(db_session)
    suffix = inventory.client_id.split("_", 1)[1]
    older_requirement = ItemUpholsteryRequirement(
        client_id=f"iur_{suffix}_1",
        workspace_id=workspace.client_id,
        item_upholstery_id=f"iup_{suffix}_1",
        upholstery_inventory_id=inventory.client_id,
        amount_meters=Decimal("2.000"),
        source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
        state=ItemUpholsteryRequirementStateEnum.ORDERED,
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    newer_requirement = ItemUpholsteryRequirement(
        client_id=f"iur_{suffix}_2",
        workspace_id=workspace.client_id,
        item_upholstery_id=f"iup_{suffix}_2",
        upholstery_inventory_id=inventory.client_id,
        amount_meters=Decimal("1.000"),
        source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
        state=ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add_all([older_requirement, newer_requirement])
    await db_session.flush()

    dispatched = []

    async def _fake_dispatch(events):
        dispatched.extend(events)

    monkeypatch.setattr(
        "beyo_manager.services.commands.upholstery.set_current_stored_amount_inventory.event_bus.dispatch",
        _fake_dispatch,
    )

    await set_current_stored_amount_inventory(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            client_id=inventory.client_id,
            stored="5.000",
        )
    )

    refreshed_inventory = (
        await db_session.execute(
            select(UpholsteryInventory).where(UpholsteryInventory.client_id == inventory.client_id)
        )
    ).scalar_one()
    refreshed_requirements = (
        await db_session.execute(
            select(ItemUpholsteryRequirement).order_by(ItemUpholsteryRequirement.client_id)
        )
    ).scalars().all()

    assert refreshed_inventory.current_stored_amount_meters == Decimal("5.000")
    assert refreshed_inventory.current_amount_in_need_meters == Decimal("5.000")
    assert refreshed_inventory.inventory_condition == UpholsteryInventoryConditionEnum.OUT_OF_STOCK
    assert [req.state for req in refreshed_requirements] == [
        ItemUpholsteryRequirementStateEnum.AVAILABLE,
        ItemUpholsteryRequirementStateEnum.AVAILABLE,
    ]
    assert len(dispatched) == 1
    assert dispatched[0].extra == {
        "ids": [f"iup_{suffix}_1", f"iup_{suffix}_2"],
        "new_state": ItemUpholsteryRequirementStateEnum.AVAILABLE.value,
    }


@pytest.mark.integration
async def test_set_current_stored_amount_inventory_demotes_low_priority_available_first(db_session, monkeypatch):
    workspace, user, inventory = await _seed_inventory_graph(db_session)
    suffix = inventory.client_id.split("_", 1)[1]
    older_available = ItemUpholsteryRequirement(
        client_id=f"iur_{suffix}_1",
        workspace_id=workspace.client_id,
        item_upholstery_id=f"iup_{suffix}_1",
        upholstery_inventory_id=inventory.client_id,
        amount_meters=Decimal("2.000"),
        source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
        state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    newer_available = ItemUpholsteryRequirement(
        client_id=f"iur_{suffix}_2",
        workspace_id=workspace.client_id,
        item_upholstery_id=f"iup_{suffix}_2",
        upholstery_inventory_id=inventory.client_id,
        amount_meters=Decimal("1.000"),
        source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
        state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    inventory.current_stored_amount_meters = Decimal("3.000")
    db_session.add_all([older_available, newer_available])
    await db_session.flush()

    dispatched = []

    async def _fake_dispatch(events):
        dispatched.extend(events)

    monkeypatch.setattr(
        "beyo_manager.services.commands.upholstery.set_current_stored_amount_inventory.event_bus.dispatch",
        _fake_dispatch,
    )

    await set_current_stored_amount_inventory(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            client_id=inventory.client_id,
            stored="2.000",
        )
    )

    refreshed_inventory = (
        await db_session.execute(
            select(UpholsteryInventory).where(UpholsteryInventory.client_id == inventory.client_id)
        )
    ).scalar_one()
    refreshed_requirements = {
        req.item_upholstery_id: req
        for req in (await db_session.execute(select(ItemUpholsteryRequirement))).scalars().all()
    }

    assert refreshed_inventory.current_stored_amount_meters == Decimal("2.000")
    assert refreshed_inventory.current_amount_in_need_meters == Decimal("5.000")
    assert refreshed_requirements[f"iup_{suffix}_1"].state == ItemUpholsteryRequirementStateEnum.AVAILABLE
    assert refreshed_requirements[f"iup_{suffix}_2"].state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
    assert len(dispatched) == 1
    assert dispatched[0].extra == {
        "ids": [f"iup_{suffix}_2"],
        "new_state": ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING.value,
    }


@pytest.mark.integration
async def test_set_current_stored_amount_inventory_noop_emits_no_events(db_session, monkeypatch):
    workspace, user, inventory = await _seed_inventory_graph(db_session)
    dispatched = []

    async def _fake_dispatch(events):
        dispatched.extend(events)

    monkeypatch.setattr(
        "beyo_manager.services.commands.upholstery.set_current_stored_amount_inventory.event_bus.dispatch",
        _fake_dispatch,
    )

    await set_current_stored_amount_inventory(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            client_id=inventory.client_id,
            stored="2.000",
        )
    )

    refreshed_inventory = (
        await db_session.execute(
            select(UpholsteryInventory).where(UpholsteryInventory.client_id == inventory.client_id)
        )
    ).scalar_one()

    assert refreshed_inventory.updated_by_id is None
    assert dispatched == []


@pytest.mark.integration
async def test_set_current_stored_amount_inventory_not_found_raises(db_session):
    with pytest.raises(NotFound, match="UpholsteryInventory not found."):
        await set_current_stored_amount_inventory(
            _ctx(
                db_session,
                workspace_id="ws_missing",
                user_id="usr_missing",
                client_id="uin_missing",
                stored="1.000",
            )
        )
