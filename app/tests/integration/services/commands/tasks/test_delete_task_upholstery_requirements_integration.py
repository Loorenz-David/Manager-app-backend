from datetime import datetime, timezone
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
from beyo_manager.domain.tasks.enums import (
    TaskItemRoleEnum,
    TaskStateEnum,
    TaskTypeEnum,
)
from beyo_manager.domain.upholstery.enums import (
    UpholsteryInventoryConditionEnum,
)
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import (
    ItemUpholsteryRequirement,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import (
    UpholsteryInventory,
)
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.items.cancel_upholstery_requirements import (
    cancel_unfinished_item_requirements_in_session,
)
from beyo_manager.services.commands.items.update_and_delete_item_upholstery import (
    update_item_upholstery,
)
from beyo_manager.services.commands.tasks.delete_task import delete_task
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.upholstery.upholstery_order_needs import (
    list_upholstery_order_needs,
)


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


def _ctx(
    db_session,
    *,
    workspace_id: str,
    user_id: str,
    incoming_data: dict,
) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "username": "requirement-canceller",
            "role_name": "manager",
        },
        incoming_data=incoming_data,
        session=db_session,
    )


async def _seed_workspace(db_session):
    suffix = uuid4().hex[:10]
    user = User(
        client_id=f"usr_{suffix}",
        username=f"cancel-user-{suffix}",
        email=f"cancel-user-{suffix}@example.com",
        password="hashed",
    )
    workspace = Workspace(
        client_id=f"ws_{suffix}",
        name=f"Cancellation workspace {suffix}",
    )
    db_session.add_all([user, workspace])
    await db_session.flush()
    return workspace, user, suffix


async def _seed_requirement_graph(
    db_session,
    *,
    workspace: Workspace,
    user: User,
    suffix: str,
    scalar: int,
    state: ItemUpholsteryRequirementStateEnum,
    amount: Decimal | None,
    stored: Decimal = Decimal("0"),
    in_need: Decimal = Decimal("0"),
    in_use: Decimal = Decimal("0"),
    ordered: Decimal = Decimal("0"),
    condition: UpholsteryInventoryConditionEnum = (
        UpholsteryInventoryConditionEnum.OUT_OF_STOCK
    ),
    task_state: TaskStateEnum = TaskStateEnum.WORKING,
    with_task: bool = True,
):
    key = f"{suffix}_{scalar}"
    upholstery = Upholstery(
        client_id=f"uph_{key}",
        workspace_id=workspace.client_id,
        name=f"Cancellation upholstery {key}",
        code=f"CANCEL-{key}",
    )
    inventory = UpholsteryInventory(
        client_id=f"uin_{key}",
        workspace_id=workspace.client_id,
        upholstery_id=upholstery.client_id,
        current_stored_amount_meters=stored,
        current_amount_in_need_meters=in_need,
        current_amount_in_use_meters=in_use,
        current_amount_ordered_meters=ordered,
        total_upholstery_used_meters=Decimal("0"),
        total_upholstery_used_inventory_meters=Decimal("0"),
        total_upholstery_used_surplus_meters=Decimal("0"),
        total_upholstery_surplus_meters=Decimal("0"),
        inventory_condition=condition,
    )
    item = Item(
        client_id=f"itm_{key}",
        workspace_id=workspace.client_id,
        article_number=f"CANCEL-{key}",
        state=ItemStateEnum.PENDING,
        quantity=1,
    )
    task = Task(
        client_id=f"tsk_{key}",
        workspace_id=workspace.client_id,
        task_scalar_id=scalar,
        task_type=TaskTypeEnum.INTERNAL,
        state=task_state,
        created_by_id=user.client_id,
    )
    db_session.add_all([upholstery, inventory, item, task])
    await db_session.flush()

    item_upholstery = ItemUpholstery(
        client_id=f"iup_{key}",
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
    if with_task:
        db_session.add(
            TaskItem(
                client_id=f"tim_{key}",
                workspace_id=workspace.client_id,
                task_id=task.client_id,
                item_id=item.client_id,
                role=TaskItemRoleEnum.PRIMARY,
                created_by_id=user.client_id,
            )
        )
    await db_session.flush()

    requirement = ItemUpholsteryRequirement(
        client_id=f"iur_{key}",
        workspace_id=workspace.client_id,
        item_upholstery_id=item_upholstery.client_id,
        upholstery_inventory_id=(
            None
            if state
            == ItemUpholsteryRequirementStateEnum.MISSING_QUANTITY
            else inventory.client_id
        ),
        amount_meters=amount,
        source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
        state=state,
        created_by_id=user.client_id,
    )
    db_session.add(requirement)
    await db_session.flush()
    item_upholstery.active_requirement_id = requirement.client_id
    await db_session.flush()
    return task, item, item_upholstery, requirement, inventory


async def _capture_delete_events(monkeypatch):
    dispatched = []

    async def _fake_dispatch(events):
        dispatched.extend(events)

    monkeypatch.setattr(
        "beyo_manager.services.commands.tasks.delete_task.event_bus.dispatch",
        _fake_dispatch,
    )
    return dispatched


async def test_delete_task_cancels_need_and_removes_order_need(
    db_session, monkeypatch
):
    workspace, user, suffix = await _seed_workspace(db_session)
    task, _, item_upholstery, requirement, inventory = (
        await _seed_requirement_graph(
            db_session,
            workspace=workspace,
            user=user,
            suffix=suffix,
            scalar=1,
            state=ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
            amount=Decimal("1.500"),
            stored=Decimal("3.500"),
            in_need=Decimal("5.000"),
        )
    )
    dispatched = await _capture_delete_events(monkeypatch)

    result = await delete_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"client_id": task.client_id},
        )
    )
    await db_session.refresh(task)
    await db_session.refresh(requirement)
    await db_session.refresh(inventory)
    await db_session.refresh(item_upholstery)

    assert result == {"client_id": task.client_id}
    assert task.is_deleted is True
    assert requirement.state == ItemUpholsteryRequirementStateEnum.FAILED
    assert requirement.failed_at is not None
    assert requirement.updated_by_id == user.client_id
    assert inventory.current_amount_in_need_meters == Decimal("3.500")
    assert item_upholstery.active_requirement_id == requirement.client_id

    order_needs = await list_upholstery_order_needs(
        ServiceContext(
            identity={
                "workspace_id": workspace.client_id,
                "user_id": user.client_id,
            },
            incoming_data={},
            query_params={"limit": 50, "offset": 0},
            session=db_session,
        )
    )
    assert order_needs["upholstery_needs_pagination"]["items"] == []
    assert [event.event_name for event in dispatched] == [
        "task:deleted",
        "item:upholstery-requirement-state-changed",
    ]
    assert dispatched[1].client_id == item_upholstery.client_id
    assert dispatched[1].extra == {"new_state": "failed"}


async def test_delete_task_preserves_shared_item_until_last_active_task(
    db_session, monkeypatch
):
    workspace, user, suffix = await _seed_workspace(db_session)
    first_task, item, _, requirement, inventory = (
        await _seed_requirement_graph(
            db_session,
            workspace=workspace,
            user=user,
            suffix=suffix,
            scalar=10,
            state=ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
            amount=Decimal("1.000"),
            in_need=Decimal("1.000"),
        )
    )
    second_task = Task(
        client_id=f"tsk_{suffix}_11",
        workspace_id=workspace.client_id,
        task_scalar_id=11,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.WORKING,
        created_by_id=user.client_id,
    )
    db_session.add(second_task)
    await db_session.flush()
    db_session.add(
        TaskItem(
            client_id=f"tim_{suffix}_11",
            workspace_id=workspace.client_id,
            task_id=second_task.client_id,
            item_id=item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=user.client_id,
        )
    )
    await db_session.flush()
    dispatched = await _capture_delete_events(monkeypatch)

    await delete_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"client_id": first_task.client_id},
        )
    )
    await db_session.refresh(requirement)
    await db_session.refresh(inventory)
    assert requirement.state == (
        ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
    )
    assert inventory.current_amount_in_need_meters == Decimal("1.000")

    await delete_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"client_id": second_task.client_id},
        )
    )
    await db_session.refresh(requirement)
    await db_session.refresh(inventory)
    assert requirement.state == ItemUpholsteryRequirementStateEnum.FAILED
    assert inventory.current_amount_in_need_meters == Decimal("0.000")
    assert [event.event_name for event in dispatched].count(
        "item:upholstery-requirement-state-changed"
    ) == 1


async def test_terminal_task_reference_does_not_preserve_demand(
    db_session, monkeypatch
):
    workspace, user, suffix = await _seed_workspace(db_session)
    task, item, _, requirement, _ = await _seed_requirement_graph(
        db_session,
        workspace=workspace,
        user=user,
        suffix=suffix,
        scalar=20,
        state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
        amount=Decimal("1.000"),
        stored=Decimal("1.000"),
        in_need=Decimal("1.000"),
        condition=UpholsteryInventoryConditionEnum.OUT_OF_STOCK,
    )
    terminal_task = Task(
        client_id=f"tsk_{suffix}_21",
        workspace_id=workspace.client_id,
        task_scalar_id=21,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.CANCELLED,
        created_by_id=user.client_id,
    )
    db_session.add(terminal_task)
    await db_session.flush()
    db_session.add(
        TaskItem(
            client_id=f"tim_{suffix}_21",
            workspace_id=workspace.client_id,
            task_id=terminal_task.client_id,
            item_id=item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
        )
    )
    await db_session.flush()
    await _capture_delete_events(monkeypatch)

    await delete_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"client_id": task.client_id},
        )
    )
    await db_session.refresh(requirement)
    assert requirement.state == ItemUpholsteryRequirementStateEnum.FAILED


async def test_removed_task_item_link_is_not_cancelled(
    db_session, monkeypatch
):
    workspace, user, suffix = await _seed_workspace(db_session)
    task, _, _, requirement, inventory = await _seed_requirement_graph(
        db_session,
        workspace=workspace,
        user=user,
        suffix=suffix,
        scalar=30,
        state=ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
        amount=Decimal("1.000"),
        in_need=Decimal("1.000"),
    )
    task_item = (
        await db_session.execute(
            select(TaskItem).where(TaskItem.task_id == task.client_id)
        )
    ).scalar_one()
    task_item.removed_at = datetime.now(timezone.utc)
    task_item.removed_by_id = user.client_id
    await db_session.flush()
    await _capture_delete_events(monkeypatch)

    await delete_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"client_id": task.client_id},
        )
    )
    await db_session.refresh(requirement)
    await db_session.refresh(inventory)
    assert requirement.state == (
        ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
    )
    assert inventory.current_amount_in_need_meters == Decimal("1.000")


async def test_cancellation_service_handles_all_unfinished_states(
    db_session,
):
    workspace, user, suffix = await _seed_workspace(db_session)
    graphs = {}
    inputs = [
        (
            ItemUpholsteryRequirementStateEnum.AVAILABLE,
            Decimal("1"),
            Decimal("2"),
            Decimal("1"),
            Decimal("0"),
            Decimal("0"),
        ),
        (
            ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
            Decimal("1"),
            Decimal("0"),
            Decimal("1"),
            Decimal("0"),
            Decimal("0"),
        ),
        (
            ItemUpholsteryRequirementStateEnum.ORDERED,
            Decimal("1"),
            Decimal("0"),
            Decimal("1"),
            Decimal("0"),
            Decimal("1"),
        ),
        (
            ItemUpholsteryRequirementStateEnum.IN_USE,
            Decimal("1"),
            Decimal("0"),
            Decimal("0"),
            Decimal("1"),
            Decimal("0"),
        ),
        (
            ItemUpholsteryRequirementStateEnum.MISSING_QUANTITY,
            None,
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
        ),
        (
            ItemUpholsteryRequirementStateEnum.COMPLETED,
            Decimal("1"),
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
        ),
        (
            ItemUpholsteryRequirementStateEnum.FAILED,
            Decimal("1"),
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
        ),
    ]
    for scalar, (
        state,
        amount,
        stored,
        in_need,
        in_use,
        ordered,
    ) in enumerate(inputs, start=100):
        graph = await _seed_requirement_graph(
            db_session,
            workspace=workspace,
            user=user,
            suffix=suffix,
            scalar=scalar,
            state=state,
            amount=amount,
            stored=stored,
            in_need=in_need,
            in_use=in_use,
            ordered=ordered,
            with_task=False,
        )
        graphs[state] = graph

    cancelled = await cancel_unfinished_item_requirements_in_session(
        session=db_session,
        workspace_id=workspace.client_id,
        item_ids=[graph[1].client_id for graph in graphs.values()],
        actor_id=user.client_id,
    )

    assert {row.previous_state for row in cancelled} == {
        ItemUpholsteryRequirementStateEnum.AVAILABLE,
        ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
        ItemUpholsteryRequirementStateEnum.ORDERED,
        ItemUpholsteryRequirementStateEnum.IN_USE,
        ItemUpholsteryRequirementStateEnum.MISSING_QUANTITY,
    }
    for state, graph in graphs.items():
        _, _, item_upholstery, requirement, inventory = graph
        await db_session.refresh(requirement)
        await db_session.refresh(inventory)
        await db_session.refresh(item_upholstery)
        if state in {
            ItemUpholsteryRequirementStateEnum.COMPLETED,
            ItemUpholsteryRequirementStateEnum.FAILED,
        }:
            assert requirement.state == state
        else:
            assert requirement.state == (
                ItemUpholsteryRequirementStateEnum.FAILED
            )
            assert requirement.failed_at is not None
            assert item_upholstery.active_requirement_id == (
                requirement.client_id
            )

    available_inventory = graphs[
        ItemUpholsteryRequirementStateEnum.AVAILABLE
    ][4]
    ordered_inventory = graphs[
        ItemUpholsteryRequirementStateEnum.ORDERED
    ][4]
    in_use_inventory = graphs[
        ItemUpholsteryRequirementStateEnum.IN_USE
    ][4]
    assert available_inventory.current_amount_in_need_meters == Decimal("0")
    assert available_inventory.inventory_condition == (
        UpholsteryInventoryConditionEnum.AVAILABLE
    )
    assert ordered_inventory.current_amount_in_need_meters == Decimal("0")
    assert ordered_inventory.current_amount_ordered_meters == Decimal("1")
    assert in_use_inventory.current_stored_amount_meters == Decimal("1")
    assert in_use_inventory.current_amount_in_use_meters == Decimal("0")
    assert in_use_inventory.inventory_condition == (
        UpholsteryInventoryConditionEnum.AVAILABLE
    )


async def test_delete_task_rolls_back_requirement_cancellation_on_failure(
    db_session, monkeypatch
):
    workspace, user, suffix = await _seed_workspace(db_session)
    task, _, _, requirement, inventory = await _seed_requirement_graph(
        db_session,
        workspace=workspace,
        user=user,
        suffix=suffix,
        scalar=200,
        state=ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
        amount=Decimal("1.000"),
        in_need=Decimal("1.000"),
    )
    task_id = task.client_id
    requirement_id = requirement.client_id
    inventory_id = inventory.client_id
    workspace_id = workspace.client_id
    user_id = user.client_id
    await db_session.commit()

    async def _fail_cleanup(*_args, **_kwargs):
        raise RuntimeError("cleanup failed")

    monkeypatch.setattr(
        "beyo_manager.services.commands.tasks.delete_task.cleanup_task_pins",
        _fail_cleanup,
    )

    with pytest.raises(RuntimeError, match="cleanup failed"):
        await delete_task(
            _ctx(
                db_session,
                workspace_id=workspace_id,
                user_id=user_id,
                incoming_data={"client_id": task_id},
            )
        )

    refreshed_task = await db_session.get(Task, task_id)
    refreshed_requirement = await db_session.get(
        ItemUpholsteryRequirement, requirement_id
    )
    refreshed_inventory = await db_session.get(
        UpholsteryInventory, inventory_id
    )
    assert refreshed_task.is_deleted is False
    assert refreshed_requirement.state == (
        ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
    )
    assert refreshed_inventory.current_amount_in_need_meters == Decimal("1")


async def test_upholstery_swap_uses_shared_cancellation_service(
    db_session, monkeypatch
):
    workspace, user, suffix = await _seed_workspace(db_session)
    _, _, item_upholstery, old_requirement, old_inventory = (
        await _seed_requirement_graph(
            db_session,
            workspace=workspace,
            user=user,
            suffix=suffix,
            scalar=300,
            state=ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
            amount=Decimal("1.500"),
            in_need=Decimal("1.500"),
            with_task=False,
        )
    )
    new_upholstery = Upholstery(
        client_id=f"uph_{suffix}_new",
        workspace_id=workspace.client_id,
        name=f"Replacement upholstery {suffix}",
        code=f"REPLACEMENT-{suffix}",
    )
    new_inventory = UpholsteryInventory(
        client_id=f"uin_{suffix}_new",
        workspace_id=workspace.client_id,
        upholstery_id=new_upholstery.client_id,
        current_stored_amount_meters=Decimal("0"),
        current_amount_in_need_meters=Decimal("0"),
        current_amount_in_use_meters=Decimal("0"),
        current_amount_ordered_meters=Decimal("0"),
        total_upholstery_used_meters=Decimal("0"),
        total_upholstery_used_inventory_meters=Decimal("0"),
        total_upholstery_used_surplus_meters=Decimal("0"),
        total_upholstery_surplus_meters=Decimal("0"),
        inventory_condition=UpholsteryInventoryConditionEnum.OUT_OF_STOCK,
    )
    db_session.add_all([new_upholstery, new_inventory])
    await db_session.flush()

    async def _fake_dispatch(_events):
        return None

    monkeypatch.setattr(
        "beyo_manager.services.commands.items.update_and_delete_item_upholstery.event_bus.dispatch",
        _fake_dispatch,
    )

    await update_item_upholstery(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "client_id": item_upholstery.client_id,
                "upholstery_id": new_upholstery.client_id,
            },
        )
    )
    await db_session.refresh(old_requirement)
    await db_session.refresh(old_inventory)
    await db_session.refresh(new_inventory)
    await db_session.refresh(item_upholstery)
    new_requirement = await db_session.get(
        ItemUpholsteryRequirement,
        item_upholstery.active_requirement_id,
    )

    assert old_requirement.state == (
        ItemUpholsteryRequirementStateEnum.FAILED
    )
    assert old_inventory.current_amount_in_need_meters == Decimal("0")
    assert new_requirement.client_id != old_requirement.client_id
    assert new_requirement.state == (
        ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
    )
    assert new_inventory.current_amount_in_need_meters == Decimal("1.500")
