"""Integration coverage for `restore_task` and the deleted-task detail read.

A restore must undo exactly what makes a task "deleted" (the flag and its two stamps),
leave a history trail, and announce itself as `task:updated` so every app refreshes.
It must also bring back the upholstery need the deletion cancelled — and only that one.
"""

from __future__ import annotations

import itertools
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum
from beyo_manager.domain.items.enums import (
    ItemStateEnum,
    ItemUpholsteryRequirementSourceEnum,
    ItemUpholsteryRequirementStateEnum,
    ItemUpholsterySourceEnum,
)
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.history.history_record import HistoryRecord
from beyo_manager.models.tables.history.history_record_link import HistoryRecordLink
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.tasks.delete_task import delete_task
from beyo_manager.services.commands.tasks.restore_task import restore_task
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.tasks.tasks import get_task


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

_scalar_id_counter = itertools.count(1)


def _ctx(db_session, *, workspace_id, user_id, task_id, query_params=None):
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "manager",
            "username": "restorer",
        },
        incoming_data={"client_id": task_id},
        query_params=query_params or {},
        session=db_session,
    )


async def _seed(db_session) -> tuple[Workspace, User, Task]:
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    task = Task(
        client_id=f"tsk_{suffix}",
        workspace_id=workspace.client_id,
        task_scalar_id=next(_scalar_id_counter),
        task_type=TaskTypeEnum.PRE_ORDER,
        state=TaskStateEnum.PENDING,
        created_by_id=user.client_id,
        customer_name_snapshot="Restored Customer",
        primary_phone_number="+46700000000",
    )
    db_session.add(task)
    await db_session.flush()
    return workspace, user, task


def _capture_events(monkeypatch) -> list:
    captured: list = []

    async def _dispatch(events):
        captured.extend(events)

    for module in ("delete_task", "restore_task"):
        monkeypatch.setattr(
            f"beyo_manager.services.commands.tasks.{module}.event_bus.dispatch",
            _dispatch,
        )
    return captured


async def test_restore_brings_a_deleted_task_back(db_session, monkeypatch):
    events = _capture_events(monkeypatch)
    workspace, user, task = await _seed(db_session)
    ctx_args = dict(workspace_id=workspace.client_id, user_id=user.client_id, task_id=task.client_id)

    await delete_task(_ctx(db_session, **ctx_args))
    await db_session.refresh(task)
    assert task.is_deleted is True
    events.clear()

    result = await restore_task(_ctx(db_session, **ctx_args))

    assert result == {"client_id": task.client_id}
    await db_session.refresh(task)
    assert task.is_deleted is False
    assert task.deleted_at is None
    assert task.deleted_by_id is None
    assert task.updated_by_id == user.client_id
    assert [(e.event_name, e.client_id) for e in events] == [("task:updated", task.client_id)]

    record = await db_session.scalar(
        select(HistoryRecord)
        .join(HistoryRecordLink, HistoryRecordLink.history_record_id == HistoryRecord.client_id)
        .where(
            HistoryRecordLink.entity_client_id == task.client_id,
            HistoryRecord.field_name == "is_deleted",
        )
    )
    assert record is not None
    assert record.change_type == HistoryRecordChangeTypeEnum.UPDATED
    assert record.from_value == {"is_deleted": True}
    assert record.to_value == {"is_deleted": False}
    assert record.description == f"restorer restored task #{task.task_scalar_id}"


async def test_restore_refuses_a_task_that_is_not_deleted(db_session, monkeypatch):
    _capture_events(monkeypatch)
    workspace, user, task = await _seed(db_session)

    with pytest.raises(ConflictError):
        await restore_task(
            _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, task_id=task.client_id)
        )


async def test_restore_refuses_an_unknown_or_foreign_task(db_session, monkeypatch):
    _capture_events(monkeypatch)
    workspace, user, task = await _seed(db_session)
    other_workspace, _, _ = await _seed(db_session)
    task.is_deleted = True
    await db_session.flush()

    with pytest.raises(NotFound):
        await restore_task(
            _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, task_id="tsk_missing")
        )
    with pytest.raises(NotFound):
        await restore_task(
            _ctx(db_session, workspace_id=other_workspace.client_id, user_id=user.client_id, task_id=task.client_id)
        )


async def test_get_task_reads_a_deleted_task_only_when_asked(db_session, monkeypatch):
    _capture_events(monkeypatch)
    workspace, user, task = await _seed(db_session)
    ctx_args = dict(workspace_id=workspace.client_id, user_id=user.client_id, task_id=task.client_id)
    await delete_task(_ctx(db_session, **ctx_args))

    with pytest.raises(NotFound):
        await get_task(_ctx(db_session, **ctx_args))

    detail = await get_task(_ctx(db_session, **ctx_args, query_params={"include_deleted": True}))
    assert detail["task"]["is_deleted"] is True
    assert detail["task"]["customer_name_snapshot"] == "Restored Customer"
    assert detail["task"]["primary_phone_number"] == "+46700000000"


# --- upholstery need -------------------------------------------------------------


async def _seed_upholstery_graph(
    db_session,
    workspace: Workspace,
    user: User,
    task: Task,
    *,
    state: ItemUpholsteryRequirementStateEnum,
    amount: Decimal,
    stored: Decimal,
    in_need: Decimal,
):
    key = uuid4().hex[:8]
    upholstery = Upholstery(
        client_id=f"uph_{key}",
        workspace_id=workspace.client_id,
        name=f"Velvet {key}",
        code=f"VEL-{key}",
    )
    inventory = UpholsteryInventory(
        client_id=f"uin_{key}",
        workspace_id=workspace.client_id,
        upholstery_id=upholstery.client_id,
        current_stored_amount_meters=stored,
        current_amount_in_need_meters=in_need,
        current_amount_in_use_meters=Decimal("0"),
        current_amount_ordered_meters=Decimal("0"),
        total_upholstery_used_meters=Decimal("0"),
        total_upholstery_used_inventory_meters=Decimal("0"),
        total_upholstery_used_surplus_meters=Decimal("0"),
        total_upholstery_surplus_meters=Decimal("0"),
        inventory_condition=UpholsteryInventoryConditionEnum.AVAILABLE,
    )
    item = Item(
        client_id=f"itm_{key}",
        workspace_id=workspace.client_id,
        article_number=f"ART-{key}",
        state=ItemStateEnum.PENDING,
        quantity=1,
    )
    db_session.add_all([upholstery, inventory, item])
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
    db_session.add_all([
        item_upholstery,
        TaskItem(
            client_id=f"tim_{key}",
            workspace_id=workspace.client_id,
            task_id=task.client_id,
            item_id=item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=user.client_id,
        ),
    ])
    await db_session.flush()
    requirement = ItemUpholsteryRequirement(
        client_id=f"iur_{key}",
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
    return item, item_upholstery, requirement, inventory


async def _current_context(db_session, item_id: str) -> tuple[ItemUpholstery, ItemUpholsteryRequirement]:
    current = (
        await db_session.execute(
            select(ItemUpholstery).where(
                ItemUpholstery.item_id == item_id,
                ItemUpholstery.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    assert len(current) == 1
    requirement = await db_session.scalar(
        select(ItemUpholsteryRequirement).where(
            ItemUpholsteryRequirement.client_id == current[0].active_requirement_id
        )
    )
    return current[0], requirement


@pytest.mark.parametrize(
    ("previous_state", "stored", "revived_state"),
    [
        # Not enough fabric in stock: the need goes back on the order list.
        (ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING, Decimal("1.000"), ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING),
        # Enough fabric: it is reserved from stock again.
        (ItemUpholsteryRequirementStateEnum.AVAILABLE, Decimal("10.000"), ItemUpholsteryRequirementStateEnum.AVAILABLE),
    ],
)
async def test_restore_brings_back_the_upholstery_need(
    db_session, monkeypatch, previous_state, stored, revived_state
):
    events = _capture_events(monkeypatch)
    workspace, user, task = await _seed(db_session)
    item, old_context, old_requirement, inventory = await _seed_upholstery_graph(
        db_session, workspace, user, task,
        state=previous_state, amount=Decimal("2.500"), stored=stored, in_need=Decimal("2.500"),
    )
    ctx_args = dict(workspace_id=workspace.client_id, user_id=user.client_id, task_id=task.client_id)

    await delete_task(_ctx(db_session, **ctx_args))
    await db_session.refresh(old_requirement)
    await db_session.refresh(inventory)
    assert old_requirement.state == ItemUpholsteryRequirementStateEnum.FAILED
    assert inventory.current_amount_in_need_meters == Decimal("0")
    events.clear()

    await restore_task(_ctx(db_session, **ctx_args))

    await db_session.refresh(old_context)
    await db_session.refresh(old_requirement)
    await db_session.refresh(inventory)
    # The failed context stays as history; a fresh one carries the need again.
    assert old_context.is_deleted is True
    assert old_requirement.state == ItemUpholsteryRequirementStateEnum.FAILED
    new_context, new_requirement = await _current_context(db_session, item.client_id)
    assert new_context.client_id != old_context.client_id
    assert new_context.upholstery_id == old_context.upholstery_id
    assert new_requirement.state == revived_state
    assert new_requirement.amount_meters == Decimal("2.500")
    assert new_requirement.upholstery_inventory_id == inventory.client_id
    assert inventory.current_amount_in_need_meters == Decimal("2.500")
    assert [e.event_name for e in events] == [
        "task:updated",
        "item:updated",
        "item:upholstery-created",
    ]
    assert events[2].client_id == new_context.client_id


async def test_restore_leaves_a_requirement_failed_for_another_reason(db_session, monkeypatch):
    _capture_events(monkeypatch)
    workspace, user, task = await _seed(db_session)
    item, old_context, old_requirement, inventory = await _seed_upholstery_graph(
        db_session, workspace, user, task,
        state=ItemUpholsteryRequirementStateEnum.FAILED,
        amount=Decimal("1.000"), stored=Decimal("0"), in_need=Decimal("0"),
    )
    old_requirement.failed_at = datetime.now(timezone.utc) - timedelta(days=3)
    await db_session.flush()
    ctx_args = dict(workspace_id=workspace.client_id, user_id=user.client_id, task_id=task.client_id)

    await delete_task(_ctx(db_session, **ctx_args))
    await restore_task(_ctx(db_session, **ctx_args))

    current, requirement = await _current_context(db_session, item.client_id)
    assert current.client_id == old_context.client_id
    assert requirement.client_id == old_requirement.client_id
    await db_session.refresh(inventory)
    assert inventory.current_amount_in_need_meters == Decimal("0")


async def test_restore_leaves_upholstery_that_moved_on_since_the_deletion(db_session, monkeypatch):
    _capture_events(monkeypatch)
    workspace, user, task = await _seed(db_session)
    item, old_context, _, inventory = await _seed_upholstery_graph(
        db_session, workspace, user, task,
        state=ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
        amount=Decimal("1.000"), stored=Decimal("0"), in_need=Decimal("1.000"),
    )
    ctx_args = dict(workspace_id=workspace.client_id, user_id=user.client_id, task_id=task.client_id)
    await delete_task(_ctx(db_session, **ctx_args))

    # Someone gave the item a new upholstery context in the meantime.
    old_context.is_deleted = True
    replacement = ItemUpholstery(
        client_id=f"iup_new_{uuid4().hex[:8]}",
        workspace_id=workspace.client_id,
        item_id=item.client_id,
        upholstery_id=old_context.upholstery_id,
        amount_meters=Decimal("4.000"),
        source=ItemUpholsterySourceEnum.INTERNAL,
        created_by_id=user.client_id,
    )
    db_session.add(replacement)
    await db_session.flush()
    replacement_requirement = ItemUpholsteryRequirement(
        workspace_id=workspace.client_id,
        item_upholstery_id=replacement.client_id,
        upholstery_inventory_id=inventory.client_id,
        amount_meters=Decimal("4.000"),
        source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
        state=ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
        created_by_id=user.client_id,
    )
    db_session.add(replacement_requirement)
    await db_session.flush()
    replacement.active_requirement_id = replacement_requirement.client_id
    await db_session.flush()

    await restore_task(_ctx(db_session, **ctx_args))

    current, requirement = await _current_context(db_session, item.client_id)
    assert current.client_id == replacement.client_id
    assert requirement.client_id == replacement_requirement.client_id


async def test_restore_leaves_an_item_another_active_task_holds(db_session, monkeypatch):
    _capture_events(monkeypatch)
    workspace, user, task = await _seed(db_session)
    item, old_context, old_requirement, inventory = await _seed_upholstery_graph(
        db_session, workspace, user, task,
        state=ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
        amount=Decimal("1.000"), stored=Decimal("0"), in_need=Decimal("1.000"),
    )
    other_task = Task(
        client_id=f"tsk_other_{uuid4().hex[:8]}",
        workspace_id=workspace.client_id,
        task_scalar_id=next(_scalar_id_counter),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.WORKING,
        created_by_id=user.client_id,
    )
    db_session.add(other_task)
    await db_session.flush()
    db_session.add(
        TaskItem(
            client_id=f"tim_other_{uuid4().hex[:8]}",
            workspace_id=workspace.client_id,
            task_id=other_task.client_id,
            item_id=item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=user.client_id,
        )
    )
    await db_session.flush()
    ctx_args = dict(workspace_id=workspace.client_id, user_id=user.client_id, task_id=task.client_id)

    await delete_task(_ctx(db_session, **ctx_args))
    await restore_task(_ctx(db_session, **ctx_args))

    current, requirement = await _current_context(db_session, item.client_id)
    assert current.client_id == old_context.client_id
    assert requirement.state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
    await db_session.refresh(inventory)
    assert inventory.current_amount_in_need_meters == Decimal("1.000")
