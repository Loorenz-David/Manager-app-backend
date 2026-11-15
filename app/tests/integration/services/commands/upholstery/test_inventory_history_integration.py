"""Upholstery inventory ledger: every movement path writes a truthful, chained history row, and
the history query reads it back with children, tasks, pagination and integrity."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from beyo_manager.domain.items.enums import (
    ItemStateEnum,
    ItemUpholsteryRequirementSourceEnum,
    ItemUpholsteryRequirementStateEnum,
    ItemUpholsterySourceEnum,
)
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.upholstery.enums import (
    InventoryMovementTriggerEnum,
    InventoryMovementTypeEnum,
    UpholsteryInventoryConditionEnum,
)
from beyo_manager.errors.validation import ValidationError
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
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.items.create_item_upholstery import create_item_upholstery
from beyo_manager.services.commands.items.mark_requirements_in_use import mark_requirements_in_use
from beyo_manager.services.commands.tasks.delete_task import delete_task
from beyo_manager.services.commands.upholstery._inventory_history import InventoryMovementContext
from beyo_manager.services.commands.upholstery._inventory_mutations import add_ordered
from beyo_manager.services.commands.upholstery.add_ordered_to_inventory import add_ordered_to_inventory
from beyo_manager.services.commands.upholstery.create_upholstery_order import create_upholstery_order
from beyo_manager.services.commands.upholstery.receive_upholstery_order import receive_upholstery_order
from beyo_manager.services.commands.upholstery.set_current_stored_amount_inventory import (
    set_current_stored_amount_inventory,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.upholstery.get_upholstery_inventory_history import (
    get_upholstery_inventory_history,
)
from beyo_manager.services.run_service import run_service


@pytest.fixture
def dispatched(monkeypatch):
    events = []

    async def _fake_dispatch(batch):
        events.extend(batch)

    monkeypatch.setattr("beyo_manager.services.infra.events.event_bus.dispatch", _fake_dispatch)
    return events


def _ctx(session, g, incoming=None, query_params=None) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": g["ws"],
            "user_id": g["user"],
            "username": g["username"],
            "role_name": "manager",
        },
        incoming_data=incoming or {},
        query_params=query_params or {},
        session=session,
    )


async def _seed(db_session, *, stored="2.000", in_need="0.000", requirements=()):
    """Workspace + user + upholstery + inventory; each requirement spec gets its own item,
    item upholstery and task (PRIMARY link). Returns ids in a dict."""
    s = uuid4().hex[:8]
    g = {
        "ws": f"ws_{s}",
        "user": f"usr_{s}",
        "username": f"mgr-{s}",
        "uph": f"uph_{s}",
        "inv": f"uin_{s}",
        "req": [],
        "iup": [],
        "item": [],
        "task": [],
    }
    db_session.add_all(
        [
            Workspace(client_id=g["ws"], name="ws"),
            User(client_id=g["user"], username=g["username"], email=f"{s}@example.com", password="x"),
        ]
    )
    await db_session.flush()
    db_session.add(Upholstery(client_id=g["uph"], workspace_id=g["ws"], name=f"Velvet {s}"))
    await db_session.flush()
    db_session.add(
        UpholsteryInventory(
            client_id=g["inv"],
            workspace_id=g["ws"],
            upholstery_id=g["uph"],
            current_stored_amount_meters=Decimal(stored),
            current_amount_in_need_meters=Decimal(in_need),
            current_amount_in_use_meters=Decimal("0"),
            current_amount_ordered_meters=Decimal("0"),
            total_upholstery_used_meters=Decimal("0"),
            total_upholstery_used_inventory_meters=Decimal("0"),
            total_upholstery_used_surplus_meters=Decimal("0"),
            total_upholstery_surplus_meters=Decimal("0"),
            inventory_condition=UpholsteryInventoryConditionEnum.AVAILABLE,
        )
    )
    await db_session.flush()
    for i, (amount, state) in enumerate(requirements, start=1):
        item_id, iup_id, req_id, task_id = f"itm_{s}_{i}", f"iup_{s}_{i}", f"iur_{s}_{i}", f"tsk_{s}_{i}"
        db_session.add_all(
            [
                Item(client_id=item_id, workspace_id=g["ws"], state=ItemStateEnum.PENDING, quantity=1),
                Task(
                    client_id=task_id,
                    workspace_id=g["ws"],
                    task_scalar_id=i,
                    task_type=TaskTypeEnum.INTERNAL,
                    state=TaskStateEnum.WORKING,
                    title=f"Chair {i}",
                    created_by_id=g["user"],
                ),
            ]
        )
        await db_session.flush()
        db_session.add_all(
            [
                TaskItem(
                    client_id=f"tim_{s}_{i}",
                    workspace_id=g["ws"],
                    task_id=task_id,
                    item_id=item_id,
                    role=TaskItemRoleEnum.PRIMARY,
                    created_by_id=g["user"],
                ),
                ItemUpholstery(
                    client_id=iup_id,
                    workspace_id=g["ws"],
                    item_id=item_id,
                    upholstery_id=g["uph"],
                    source=ItemUpholsterySourceEnum.INTERNAL,
                    amount_meters=Decimal(amount),
                ),
            ]
        )
        await db_session.flush()
        db_session.add(
            ItemUpholsteryRequirement(
                client_id=req_id,
                workspace_id=g["ws"],
                item_upholstery_id=iup_id,
                upholstery_inventory_id=g["inv"],
                amount_meters=Decimal(amount),
                source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
                state=state,
                created_at=datetime.now(timezone.utc) - timedelta(days=10 - i),
            )
        )
        await db_session.flush()
        (await db_session.get(ItemUpholstery, iup_id)).active_requirement_id = req_id
        await db_session.flush()
        g["req"].append(req_id)
        g["iup"].append(iup_id)
        g["item"].append(item_id)
        g["task"].append(task_id)
    return g


async def _ledger(db_session, inv_id):
    return (
        (
            await db_session.execute(
                select(Rec)
                .where(Rec.upholstery_inventory_id == inv_id)
                .order_by(Rec.created_at, Rec.client_id)
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )


async def _inventory(db_session, inv_id) -> UpholsteryInventory:
    return (
        await db_session.execute(
            select(UpholsteryInventory)
            .where(UpholsteryInventory.client_id == inv_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


@pytest.mark.integration
async def test_order_create_and_receive_record_movements_children_and_chain(db_session, dispatched):
    g = await _seed(
        db_session,
        stored="0.000",
        in_need="5.000",
        requirements=[("2.000", ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING),
                      ("3.000", ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING)],
    )
    await db_session.commit()  # the order commands open their own transaction

    created = await run_service(
        create_upholstery_order,
        _ctx(db_session, g, {"upholstery_id": g["uph"], "order_amount_meters": Decimal("5")}),
    )
    assert created.success, created.error
    order_id = created.data["client_id"]
    received_outcome = await run_service(
        receive_upholstery_order,
        _ctx(db_session, g, {"client_id": order_id, "received_amount_meters": Decimal("2")}),
    )
    assert received_outcome.success, received_outcome.error

    rows = await _ledger(db_session, g["inv"])
    parents = [r for r in rows if r.parent_record_id is None]
    assert [p.movement_type for p in parents] == [
        InventoryMovementTypeEnum.ORDER_PLACED,
        InventoryMovementTypeEnum.ORDER_RECEIVED,
    ]
    placed, received = parents
    assert placed.trigger == InventoryMovementTriggerEnum.ORDER_CREATED.value
    assert placed.upholstery_order_id == order_id
    assert placed.created_by_id == g["user"]
    assert placed.username_snapshot == g["username"]
    assert (placed.before_ordered_meters, placed.after_ordered_meters) == (Decimal("0.000"), Decimal("5.000"))
    assert (received.before_stored_meters, received.after_stored_meters) == (Decimal("0.000"), Decimal("2.000"))
    assert received.after_ordered_meters == Decimal("3.000")
    # chain: receipt continues the placement, pointer is the receipt
    assert placed.previous_record_id is None
    assert received.previous_record_id == placed.client_id
    assert (await _inventory(db_session, g["inv"])).latest_projection_history_id == received.client_id
    # one correlation per service run: children share their parent's, runs don't share
    assert placed.correlation_id != received.correlation_id

    placed_children = [r for r in rows if r.parent_record_id == placed.client_id]
    assert {(c.requirement_id, c.requirement_from_state, c.requirement_to_state) for c in placed_children} == {
        (g["req"][0], ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING, ItemUpholsteryRequirementStateEnum.ORDERED),
        (g["req"][1], ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING, ItemUpholsteryRequirementStateEnum.ORDERED),
    }
    assert {c.task_id for c in placed_children} == set(g["task"])
    assert {c.correlation_id for c in placed_children} == {placed.correlation_id}
    assert placed.details["resolved_count"] == 2

    # 2 m received → only the older 2 m requirement fits; the 3 m one stays ORDERED.
    received_children = [r for r in rows if r.parent_record_id == received.client_id]
    assert [(c.requirement_id, c.requirement_to_state) for c in received_children] == [
        (g["req"][0], ItemUpholsteryRequirementStateEnum.AVAILABLE)
    ]
    assert received.details["unresolved_requirement_ids"] == [g["req"][1]]

    history = await get_upholstery_inventory_history(
        _ctx(db_session, g, {"client_id": g["inv"]}, {"limit": 20})
    )
    assert [r["movement_type"] for r in history["records"]] == ["order_received", "order_placed"]
    top = history["records"][0]
    assert top["delta"]["stored"] == "2.000" and top["delta"]["ordered"] == "-2.000"
    assert top["created_by"]["username"] == g["username"]
    assert top["upholstery_order"]["client_id"] == order_id
    assert [c["task"]["client_id"] for c in top["children"]] == [g["task"][0]]
    assert top["children"][0]["task"]["task_scalar_id"] == 1
    assert top["children"][0]["requirement"]["to_state"] == "available"
    assert top["chain_break"] is False
    assert history["integrity"]["status"] == "consistent"
    assert history["integrity"]["pointer_matches"] is True


@pytest.mark.integration
async def test_manual_stored_set_records_old_value_and_drift_is_detected(db_session, dispatched):
    g = await _seed(
        db_session,
        stored="1.000",
        in_need="2.000",
        requirements=[("2.000", ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING)],
    )
    await db_session.commit()

    await set_current_stored_amount_inventory(
        _ctx(db_session, g, {"client_id": g["inv"], "current_stored_amount_meters": Decimal("4")})
    )
    rows = await _ledger(db_session, g["inv"])
    stored_set = next(r for r in rows if r.parent_record_id is None)
    assert stored_set.movement_type == InventoryMovementTypeEnum.STORED_SET
    assert stored_set.trigger == InventoryMovementTriggerEnum.MANUAL_STORED_SET.value
    assert (stored_set.before_stored_meters, stored_set.after_stored_meters) == (Decimal("1.000"), Decimal("4.000"))
    child = next(r for r in rows if r.parent_record_id == stored_set.client_id)
    assert (child.requirement_id, child.requirement_to_state, child.task_id) == (
        g["req"][0],
        ItemUpholsteryRequirementStateEnum.AVAILABLE,
        g["task"][0],
    )

    # An out-of-band change (direct SQL, script, unrecorded path) shows up as drift.
    await db_session.execute(
        text("UPDATE upholstery_inventory SET current_stored_amount_meters = 9 WHERE client_id = :id"),
        {"id": g["inv"]},
    )
    await db_session.commit()
    history = await get_upholstery_inventory_history(_ctx(db_session, g, {"client_id": g["inv"]}))
    assert history["integrity"]["status"] == "drift"
    assert history["integrity"]["drift"]["stored"] == "5.000"

    # The next recorded movement starts from the drifted totals → flagged as a chain break.
    await db_session.commit()
    await add_ordered_to_inventory(_ctx(db_session, g, {"client_id": g["inv"], "quantity": Decimal("1")}))
    history = await get_upholstery_inventory_history(_ctx(db_session, g, {"client_id": g["inv"]}))
    latest = history["records"][0]
    assert latest["movement_type"] == "order_placed"
    assert latest["trigger"] == "manual_add_ordered"
    assert latest["chain_break"] is True
    assert history["integrity"]["status"] == "consistent"


@pytest.mark.integration
async def test_delete_task_records_released_need_with_task(db_session, dispatched):
    g = await _seed(
        db_session,
        stored="0.000",
        in_need="2.000",
        requirements=[("2.000", ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING)],
    )
    await delete_task(_ctx(db_session, g, {"client_id": g["task"][0]}))

    rows = await _ledger(db_session, g["inv"])
    assert len(rows) == 1
    rec = rows[0]
    assert rec.movement_type == InventoryMovementTypeEnum.NEED_ADJUSTED
    assert rec.trigger == InventoryMovementTriggerEnum.TASK_DELETED.value
    assert rec.quantity_meters == Decimal("-2.000")
    assert (rec.before_in_need_meters, rec.after_in_need_meters) == (Decimal("2.000"), Decimal("0.000"))
    assert rec.task_id == g["task"][0]
    assert (rec.requirement_id, rec.requirement_from_state, rec.requirement_to_state) == (
        g["req"][0],
        ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
        ItemUpholsteryRequirementStateEnum.FAILED,
    )
    assert rec.anomaly is None


@pytest.mark.integration
async def test_clamped_need_is_recorded_as_anomaly(db_session, dispatched):
    # The projection already lost track of this requirement's need (in_need 0 < 2 m).
    g = await _seed(
        db_session,
        stored="0.000",
        in_need="0.000",
        requirements=[("2.000", ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING)],
    )
    await delete_task(_ctx(db_session, g, {"client_id": g["task"][0]}))
    (rec,) = await _ledger(db_session, g["inv"])
    assert rec.anomaly == "in_need_clamped_at_zero"
    assert rec.after_in_need_meters == Decimal("0.000")


@pytest.mark.integration
async def test_failed_movement_leaves_no_ledger_row(db_session, dispatched):
    g = await _seed(
        db_session,
        stored="1.000",
        in_need="2.000",
        requirements=[("2.000", ItemUpholsteryRequirementStateEnum.AVAILABLE)],
    )
    with pytest.raises(ValidationError):
        await mark_requirements_in_use(_ctx(db_session, g, {"item_upholstery_id": g["iup"][0]}))
    assert await _ledger(db_session, g["inv"]) == []


@pytest.mark.integration
async def test_item_upholstery_creation_references_the_persisted_requirement(db_session, dispatched):
    g = await _seed(db_session, stored="10.000")
    s = g["ws"].split("_", 1)[1]
    item_id = f"itm_{s}_new"
    db_session.add(Item(client_id=item_id, workspace_id=g["ws"], state=ItemStateEnum.PENDING, quantity=1))
    await db_session.flush()

    result = await create_item_upholstery(
        _ctx(
            db_session,
            g,
            {
                "item_id": item_id,
                "upholstery_id": g["uph"],
                "source": ItemUpholsterySourceEnum.INTERNAL.value,
                "amount_meters": "3",
            },
        )
    )
    iup = await db_session.get(ItemUpholstery, result["client_id"])
    (rec,) = await _ledger(db_session, g["inv"])
    assert rec.movement_type == InventoryMovementTypeEnum.NEED_ADDED
    assert rec.trigger == InventoryMovementTriggerEnum.ITEM_UPHOLSTERY_SET.value
    assert rec.requirement_id == iup.active_requirement_id
    assert rec.item_id == item_id
    assert rec.requirement_to_state == ItemUpholsteryRequirementStateEnum.AVAILABLE
    assert (rec.before_in_need_meters, rec.after_in_need_meters) == (Decimal("0.000"), Decimal("3.000"))


@pytest.mark.integration
async def test_history_cursor_pages_without_duplicates_when_new_rows_arrive(db_session, dispatched):
    g = await _seed(db_session)
    for qty in ("1", "2", "3"):
        await add_ordered(
            db_session,
            g["ws"],
            g["inv"],
            Decimal(qty),
            movement=InventoryMovementContext.system(
                db_session, InventoryMovementTriggerEnum.MAINTENANCE_SCRIPT, actor_id=g["user"]
            ),
        )

    first = await get_upholstery_inventory_history(
        _ctx(db_session, g, {"client_id": g["inv"]}, {"limit": 2})
    )
    assert [r["quantity_meters"] for r in first["records"]] == ["3.000", "2.000"]
    assert first["pagination"]["has_more"] is True
    assert first["integrity"] is not None

    # a new movement lands at the top between page loads
    await add_ordered(
        db_session,
        g["ws"],
        g["inv"],
        Decimal("4"),
        movement=InventoryMovementContext.system(db_session, InventoryMovementTriggerEnum.MAINTENANCE_SCRIPT),
    )
    second = await get_upholstery_inventory_history(
        _ctx(db_session, g, {"client_id": g["inv"]}, {"limit": 2, "cursor": first["pagination"]["next_cursor"]})
    )
    assert [r["quantity_meters"] for r in second["records"]] == ["1.000"]
    assert second["pagination"] == {"limit": 2, "has_more": False, "next_cursor": None}
    assert second["integrity"] is None
    assert second["records"][0]["created_by"]["client_id"] == g["user"]

    with pytest.raises(ValidationError):
        await get_upholstery_inventory_history(
            _ctx(db_session, g, {"client_id": g["inv"]}, {"cursor": "not-a-cursor"})
        )


@pytest.mark.integration
async def test_history_is_workspace_scoped(db_session, dispatched):
    from beyo_manager.errors.not_found import NotFound

    g = await _seed(db_session)
    other = await _seed(db_session)
    with pytest.raises(NotFound):
        await get_upholstery_inventory_history(_ctx(db_session, other, {"client_id": g["inv"]}))


@pytest.mark.integration
async def test_run_service_emits_one_inventory_event_after_success_only(db_session, dispatched):
    g = await _seed(db_session)
    await db_session.commit()

    outcome = await run_service(
        add_ordered_to_inventory, _ctx(db_session, g, {"client_id": g["inv"], "quantity": Decimal("2")})
    )
    assert outcome.success
    inventory_events = [e for e in dispatched if e.event_name == "upholstery:inventory-updated"]
    assert [(e.client_id, e.workspace_id) for e in inventory_events] == [(g["inv"], g["ws"])]

    dispatched.clear()
    outcome = await run_service(
        add_ordered_to_inventory, _ctx(db_session, g, {"client_id": "uin_missing", "quantity": Decimal("2")})
    )
    assert not outcome.success
    assert [e for e in dispatched if e.event_name == "upholstery:inventory-updated"] == []
    assert "uih_touched" not in db_session.info
    assert "uih_correlation_id" not in db_session.info
