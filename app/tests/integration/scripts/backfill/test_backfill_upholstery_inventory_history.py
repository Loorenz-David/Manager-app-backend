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
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.upholstery.enums import (
    InventoryMovementTypeEnum,
    UpholsteryInventoryConditionEnum,
    UpholsteryOrderStateEnum,
)
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.models.tables.upholstery.upholstery_inventory_history_record import (
    UpholsteryInventoryHistoryRecord as Rec,
)
from beyo_manager.models.tables.upholstery.upholstery_order import UpholsteryOrder
from beyo_manager.models.tables.upholstery.upholstery_order_history_record import (
    UpholsteryOrderHistoryRecord,
)
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from scripts.backfill.backfill_upholstery_inventory_history import (
    backfill_upholstery_inventory_history,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime.now(timezone.utc)


async def _seed(db_session):
    s = uuid4().hex[:8]
    ws, user, uph, inv = f"ws_{s}", f"usr_{s}", f"uph_{s}", f"uin_{s}"
    db_session.add_all(
        [Workspace(client_id=ws, name="ws"), User(client_id=user, username=f"u{s}", email=f"{s}@x.com", password="x")]
    )
    await db_session.flush()
    db_session.add(Upholstery(client_id=uph, workspace_id=ws, name=f"Linen {s}"))
    await db_session.flush()
    db_session.add(
        UpholsteryInventory(
            client_id=inv,
            workspace_id=ws,
            upholstery_id=uph,
            current_stored_amount_meters=Decimal("1"),
            inventory_condition=UpholsteryInventoryConditionEnum.AVAILABLE,
        )
    )
    await db_session.flush()
    # The migration baseline: everything older than this is reconstructable.
    db_session.add(
        Rec(
            client_id=f"uih_{s}_base",
            workspace_id=ws,
            upholstery_inventory_id=inv,
            movement_type=InventoryMovementTypeEnum.OPENING_BALANCE,
            trigger="migration_baseline",
            after_stored_meters=Decimal("1"),
            created_at=NOW - timedelta(days=1),
            reconstruction_key=f"baseline:{inv}",
        )
    )
    old_task = Task(
        client_id=f"tsk_{s}_old", workspace_id=ws, task_scalar_id=1, task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.WORKING, created_by_id=user, created_at=NOW - timedelta(days=30),
    )
    item = Item(client_id=f"itm_{s}", workspace_id=ws, state=ItemStateEnum.PENDING, quantity=1)
    order = UpholsteryOrder(
        client_id=f"uor_{s}", workspace_id=ws, upholstery_inventory_id=inv, order_amount_meters=Decimal("6"),
        state=UpholsteryOrderStateEnum.RECEIVED, received_amount_meters=Decimal("6"), created_by_id=user,
    )
    db_session.add_all([old_task, item, order])
    await db_session.flush()
    db_session.add_all(
        [
            TaskItem(client_id=f"tim_{s}", workspace_id=ws, task_id=old_task.client_id, item_id=item.client_id,
                     role=TaskItemRoleEnum.PRIMARY, created_by_id=user),
            ItemUpholstery(client_id=f"iup_{s}", workspace_id=ws, item_id=item.client_id, upholstery_id=uph,
                           source=ItemUpholsterySourceEnum.INTERNAL),
            UpholsteryOrderHistoryRecord(workspace_id=ws, upholstery_order_id=order.client_id,
                                         state=UpholsteryOrderStateEnum.ORDERED, changed_at=NOW - timedelta(days=9),
                                         snapshot_order_amount_meters=Decimal("6"), created_by_id=user),
            UpholsteryOrderHistoryRecord(workspace_id=ws, upholstery_order_id=order.client_id,
                                         state=UpholsteryOrderStateEnum.RECEIVED, changed_at=NOW - timedelta(days=5),
                                         created_by_id=user),
        ]
    )
    await db_session.flush()
    db_session.add(
        ItemUpholsteryRequirement(
            client_id=f"iur_{s}", workspace_id=ws, item_upholstery_id=f"iup_{s}", upholstery_inventory_id=inv,
            amount_meters=Decimal("2"), source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
            state=ItemUpholsteryRequirementStateEnum.COMPLETED, created_by_id=user,
            created_at=NOW - timedelta(days=10), ordered_at=NOW - timedelta(days=9) + timedelta(hours=1),
            in_use_at=NOW - timedelta(days=4),
            completed_at=NOW + timedelta(hours=1),  # after the baseline → recorded live, not backfilled
        )
    )
    await db_session.flush()
    return {"ws": ws, "inv": inv, "user": user, "order": order.client_id, "task": old_task.client_id, "s": s}


async def _reconstructed(db_session, inv):
    rows = await db_session.execute(
        select(Rec).where(Rec.upholstery_inventory_id == inv, Rec.is_reconstructed.is_(True)).order_by(Rec.created_at)
    )
    return rows.scalars().all()


async def test_dry_run_writes_nothing(db_session):
    g = await _seed(db_session)
    await backfill_upholstery_inventory_history(db_session, dry_run=True, workspace_id=g["ws"])
    assert await _reconstructed(db_session, g["inv"]) == []


async def test_backfill_maps_pre_baseline_events_and_is_idempotent(db_session):
    g = await _seed(db_session)
    inserted = await backfill_upholstery_inventory_history(db_session, dry_run=False, workspace_id=g["ws"])
    rows = await _reconstructed(db_session, g["inv"])
    assert inserted == len(rows) == 5

    by_key = {r.reconstruction_key.split(":")[0] + ":" + r.reconstruction_key.split(":")[-1]: r for r in rows}
    assert [r.movement_type for r in rows] == [
        InventoryMovementTypeEnum.NEED_ADDED,
        InventoryMovementTypeEnum.ORDER_PLACED,
        InventoryMovementTypeEnum.REQUIREMENT_STATE_CHANGED,
        InventoryMovementTypeEnum.ORDER_RECEIVED,
        InventoryMovementTypeEnum.RESERVED_FOR_USE,
    ]
    placed = next(r for r in rows if r.movement_type == InventoryMovementTypeEnum.ORDER_PLACED)
    received = next(r for r in rows if r.movement_type == InventoryMovementTypeEnum.ORDER_RECEIVED)
    assert placed.quantity_meters == Decimal("6.000") and placed.created_by_id == g["user"]
    assert received.quantity_meters == Decimal("6.000")  # single receipt → amount is unambiguous
    assert received.upholstery_order_id == g["order"]
    need = by_key["iur:created"]
    assert need.task_id == g["task"] and need.created_by_id == g["user"]
    assert by_key["iur:ordered"].requirement_to_state == ItemUpholsteryRequirementStateEnum.ORDERED
    assert all(r.trigger == "reconstructed" and r.before_stored_meters is None and r.after_stored_meters is None
               and r.parent_record_id is None for r in rows)
    assert "iur:completed" not in by_key  # completed after the baseline

    again = await backfill_upholstery_inventory_history(db_session, dry_run=False, workspace_id=g["ws"])
    assert again == 0
    assert len(await _reconstructed(db_session, g["inv"])) == 5
