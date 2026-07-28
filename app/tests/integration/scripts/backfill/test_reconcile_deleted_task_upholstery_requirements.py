from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

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
from scripts.backfill.reconcile_deleted_task_upholstery_requirements import (
    reconcile_deleted_task_upholstery_requirements,
)


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _seed_deleted_task_requirement(db_session):
    suffix = uuid4().hex[:10]
    workspace = Workspace(
        client_id=f"ws_{suffix}",
        name=f"Reconciliation workspace {suffix}",
    )
    user = User(
        client_id=f"usr_{suffix}",
        username=f"reconcile-user-{suffix}",
        email=f"reconcile-user-{suffix}@example.com",
        password="hashed",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()

    upholstery = Upholstery(
        client_id=f"uph_{suffix}",
        workspace_id=workspace.client_id,
        name=f"Reconciliation upholstery {suffix}",
        code=f"RECONCILE-{suffix}",
    )
    inventory = UpholsteryInventory(
        client_id=f"uin_{suffix}",
        workspace_id=workspace.client_id,
        upholstery_id=upholstery.client_id,
        current_stored_amount_meters=Decimal("3.500"),
        current_amount_in_need_meters=Decimal("5.000"),
        current_amount_in_use_meters=Decimal("0"),
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
        article_number=f"TEST_DAVID_{suffix}",
        state=ItemStateEnum.PENDING,
        quantity=1,
    )
    task = Task(
        client_id=f"tsk_{suffix}",
        workspace_id=workspace.client_id,
        task_scalar_id=1,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        is_deleted=True,
        deleted_at=datetime.now(timezone.utc),
        deleted_by_id=user.client_id,
        created_by_id=user.client_id,
    )
    db_session.add_all([upholstery, inventory, item, task])
    await db_session.flush()

    item_upholstery = ItemUpholstery(
        client_id=f"iup_{suffix}",
        workspace_id=workspace.client_id,
        item_id=item.client_id,
        upholstery_id=upholstery.client_id,
        name=upholstery.name,
        code=upholstery.code,
        amount_meters=Decimal("1.500"),
        source=ItemUpholsterySourceEnum.INTERNAL,
    )
    task_item = TaskItem(
        client_id=f"tim_{suffix}",
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        item_id=item.client_id,
        role=TaskItemRoleEnum.PRIMARY,
    )
    db_session.add_all([item_upholstery, task_item])
    await db_session.flush()

    requirement = ItemUpholsteryRequirement(
        client_id=f"iur_{suffix}",
        workspace_id=workspace.client_id,
        item_upholstery_id=item_upholstery.client_id,
        upholstery_inventory_id=inventory.client_id,
        amount_meters=Decimal("1.500"),
        source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
        state=ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
    )
    db_session.add(requirement)
    await db_session.flush()
    item_upholstery.active_requirement_id = requirement.client_id
    await db_session.flush()
    return workspace, task, requirement, inventory, user


async def test_reconciliation_is_dry_run_first_filtered_and_idempotent(
    db_session,
):
    workspace, task, requirement, inventory, user = (
        await _seed_deleted_task_requirement(db_session)
    )

    preview = await reconcile_deleted_task_upholstery_requirements(
        db_session,
        dry_run=True,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
    )
    await db_session.refresh(requirement)
    await db_session.refresh(inventory)
    assert len(preview) == 1
    assert requirement.state == (
        ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
    )
    assert inventory.current_amount_in_need_meters == Decimal("5.000")

    ignored = await reconcile_deleted_task_upholstery_requirements(
        db_session,
        dry_run=False,
        workspace_id=workspace.client_id,
        task_id="tsk_not_the_target",
    )
    assert ignored == []

    changed = await reconcile_deleted_task_upholstery_requirements(
        db_session,
        dry_run=False,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
    )
    await db_session.refresh(requirement)
    await db_session.refresh(inventory)
    assert len(changed) == 1
    assert requirement.state == ItemUpholsteryRequirementStateEnum.FAILED
    assert requirement.updated_by_id == user.client_id
    assert inventory.current_amount_in_need_meters == Decimal("3.500")

    rerun = await reconcile_deleted_task_upholstery_requirements(
        db_session,
        dry_run=False,
        workspace_id=workspace.client_id,
        task_id=task.client_id,
    )
    assert rerun == []
