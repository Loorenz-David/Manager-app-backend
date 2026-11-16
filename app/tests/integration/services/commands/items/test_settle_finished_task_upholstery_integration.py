"""A task that ends finished releases fabric it never got (incident 2026-11-16,
PRE-ORDER 29 / task #1014: forced ready as a duplicate while its requirement was
still ``needs_ordering``, so it stayed in the ordering list for weeks)."""

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
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import (
    ItemUpholsteryRequirement,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.models.tables.upholstery.upholstery_inventory_history_record import (
    UpholsteryInventoryHistoryRecord,
)
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.items.settle_finished_task_upholstery import (
    settle_finished_task_upholstery,
)
from beyo_manager.services.commands.tasks.cancel_task import cancel_task
from beyo_manager.services.commands.tasks.delete_task import delete_task
from beyo_manager.services.commands.tasks.force_task_ready import force_task_ready
from beyo_manager.services.commands.tasks.resolve_task import resolve_task
from beyo_manager.services.commands.tasks.restore_task import restore_task
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.upholstery.upholstery_order_needs import (
    get_upholstery_order_need_items,
    list_upholstery_order_needs,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NEEDS_ORDERING = ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
ORDERED = ItemUpholsteryRequirementStateEnum.ORDERED
AVAILABLE = ItemUpholsteryRequirementStateEnum.AVAILABLE
FAILED = ItemUpholsteryRequirementStateEnum.FAILED


def _ctx(db_session, workspace, user, incoming_data, **extra) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace.client_id,
            "user_id": user.client_id,
            "username": "settler",
            "role_name": "manager",
        },
        incoming_data=incoming_data,
        session=db_session,
        **extra,
    )


@pytest.fixture
def dispatched(monkeypatch):
    events: list = []

    async def _dispatch(batch):
        events.extend(batch)

    async def _noop(*_args, **_kwargs):
        return None

    async def _no_targets(*_args, **_kwargs):
        return []

    for module in ("force_task_ready", "resolve_task", "cancel_task", "delete_task", "restore_task"):
        base = f"beyo_manager.services.commands.tasks.{module}"
        monkeypatch.setattr(f"{base}.event_bus.dispatch", _dispatch)
        if module in ("force_task_ready", "resolve_task", "cancel_task"):
            monkeypatch.setattr(f"{base}.create_instant_task", _noop)
            monkeypatch.setattr(f"{base}.resolve_task_notification_targets", _no_targets)
    return events


async def _seed(db_session):
    suffix = uuid4().hex[:10]
    user = User(
        client_id=f"usr_{suffix}",
        username=f"settle-{suffix}",
        email=f"settle-{suffix}@example.com",
        password="hashed",
    )
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Settle {suffix}")
    db_session.add_all([user, workspace])
    await db_session.flush()
    return workspace, user, suffix


async def _seed_graph(
    db_session,
    workspace,
    user,
    key: str,
    *,
    req_state: ItemUpholsteryRequirementStateEnum,
    amount=Decimal("1.500"),
    task_state=TaskStateEnum.PENDING,
    in_need=Decimal("1.500"),
    stored=Decimal("0"),
):
    upholstery = Upholstery(
        client_id=f"uph_{key}", workspace_id=workspace.client_id,
        name=f"Tyg {key}", code=f"C-{key}",
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
        inventory_condition=UpholsteryInventoryConditionEnum.OUT_OF_STOCK,
    )
    item = Item(
        client_id=f"itm_{key}", workspace_id=workspace.client_id,
        article_number=f"A-{key}", sku=f"PRE-ORDER {key}",
        state=ItemStateEnum.PENDING, quantity=1,
    )
    task = Task(
        client_id=f"tsk_{key}", workspace_id=workspace.client_id,
        task_scalar_id=abs(hash(key)) % 10_000_000, task_type=TaskTypeEnum.PRE_ORDER,
        state=task_state, created_by_id=user.client_id,
    )
    db_session.add_all([upholstery, inventory, item, task])
    await db_session.flush()
    iup = ItemUpholstery(
        client_id=f"iup_{key}", workspace_id=workspace.client_id, item_id=item.client_id,
        upholstery_id=upholstery.client_id, name=upholstery.name, code=upholstery.code,
        amount_meters=amount, source=ItemUpholsterySourceEnum.INTERNAL,
        created_by_id=user.client_id,
    )
    db_session.add_all([
        iup,
        TaskItem(
            client_id=f"tim_{key}", workspace_id=workspace.client_id, task_id=task.client_id,
            item_id=item.client_id, role=TaskItemRoleEnum.PRIMARY, created_by_id=user.client_id,
        ),
    ])
    await db_session.flush()
    req = ItemUpholsteryRequirement(
        client_id=f"iur_{key}", workspace_id=workspace.client_id,
        item_upholstery_id=iup.client_id, upholstery_inventory_id=inventory.client_id,
        amount_meters=amount, source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
        state=req_state, created_by_id=user.client_id,
    )
    db_session.add(req)
    await db_session.flush()
    iup.active_requirement_id = req.client_id
    await db_session.flush()
    return task, item, iup, req, inventory, upholstery


async def _order_list(db_session, workspace, user):
    ctx = _ctx(db_session, workspace, user, {}, query_params={"limit": 50, "offset": 0})
    return (await list_upholstery_order_needs(ctx))["upholstery_needs_pagination"]["items"]


async def _refresh(db_session, *rows):
    for row in rows:
        await db_session.refresh(row)


# --- the incident ---------------------------------------------------------------------


async def test_force_ready_releases_needs_ordering_fabric_and_leaves_the_order_list(
    db_session, dispatched
):
    """PRE-ORDER 29: forced ready (no steps run) while still needs_ordering."""
    workspace, user, suffix = await _seed(db_session)
    task, _, iup, req, inventory, upholstery = await _seed_graph(
        db_session, workspace, user, f"{suffix}a", req_state=NEEDS_ORDERING
    )
    assert [row["upholstery_id"] for row in await _order_list(db_session, workspace, user)] == [
        upholstery.client_id
    ]

    await force_task_ready(
        _ctx(db_session, workspace, user, {
            "client_id": task.client_id, "reason": "Item is duplicate and ready",
            "mark_inaccurate": True,
        })
    )
    await _refresh(db_session, task, req, inventory)

    assert task.state == TaskStateEnum.READY
    assert req.state == FAILED
    assert req.failed_at is not None
    assert req.completed_at is None, "cancelled, never recorded as used"
    assert inventory.current_amount_in_need_meters == Decimal("0.000")
    assert inventory.total_upholstery_used_meters == Decimal("0")
    assert await _order_list(db_session, workspace, user) == []
    need_items = await get_upholstery_order_need_items(
        _ctx(db_session, workspace, user, {"upholstery_id": upholstery.client_id},
             query_params={"limit": 50, "offset": 0})
    )
    assert need_items["tasks_pagination"]["items"] == []

    ledger = (
        await db_session.execute(
            select(UpholsteryInventoryHistoryRecord).where(
                UpholsteryInventoryHistoryRecord.upholstery_inventory_id == inventory.client_id
            )
        )
    ).scalars().all()
    assert [row.trigger for row in ledger] == ["task_finished"]

    settle_events = [
        e for e in dispatched if e.event_name == "item:upholstery-requirement-state-changed"
    ]
    assert [(e.client_id, e.extra) for e in settle_events] == [
        (iup.client_id, {"new_state": "failed"})
    ]


@pytest.mark.parametrize(
    "command, start_state",
    [
        (resolve_task, TaskStateEnum.READY),
        (cancel_task, TaskStateEnum.WORKING),
    ],
)
async def test_terminal_commands_release_ordered_fabric(
    db_session, dispatched, command, start_state
):
    workspace, user, suffix = await _seed(db_session)
    task, _, _, req, inventory, _ = await _seed_graph(
        db_session, workspace, user, f"{suffix}b", req_state=ORDERED,
        amount=Decimal("3.500"), in_need=Decimal("5.000"), task_state=start_state,
    )

    await command(_ctx(db_session, workspace, user, {"client_id": task.client_id}))
    await _refresh(db_session, req, inventory)

    assert req.state == FAILED
    assert inventory.current_amount_in_need_meters == Decimal("1.500")


# --- what it must NOT touch ---------------------------------------------------------


async def test_allocated_fabric_is_left_alone(db_session, dispatched):
    """`available` fabric was allocated; settling only cancels what never arrived."""
    workspace, user, suffix = await _seed(db_session)
    task, _, _, req, inventory, _ = await _seed_graph(
        db_session, workspace, user, f"{suffix}c", req_state=AVAILABLE,
        stored=Decimal("2.000"),
    )

    await force_task_ready(
        _ctx(db_session, workspace, user, {
            "client_id": task.client_id, "reason": "done", "mark_inaccurate": True,
        })
    )
    await _refresh(db_session, req, inventory)

    assert req.state == AVAILABLE
    assert inventory.current_amount_in_need_meters == Decimal("1.500")


async def test_item_still_on_an_unfinished_task_keeps_its_demand(db_session, dispatched):
    workspace, user, suffix = await _seed(db_session)
    task, item, _, req, inventory, _ = await _seed_graph(
        db_session, workspace, user, f"{suffix}d", req_state=NEEDS_ORDERING
    )
    other = Task(
        client_id=f"tsk_{suffix}d2", workspace_id=workspace.client_id, task_scalar_id=999_001,
        task_type=TaskTypeEnum.INTERNAL, state=TaskStateEnum.WORKING,
        created_by_id=user.client_id,
    )
    db_session.add(other)
    await db_session.flush()
    db_session.add(
        TaskItem(
            client_id=f"tim_{suffix}d2", workspace_id=workspace.client_id,
            task_id=other.client_id, item_id=item.client_id,
            role=TaskItemRoleEnum.RELATED, created_by_id=user.client_id,
        )
    )
    await db_session.flush()

    await force_task_ready(
        _ctx(db_session, workspace, user, {
            "client_id": task.client_id, "reason": "done", "mark_inaccurate": True,
        })
    )
    await _refresh(db_session, req, inventory)

    assert req.state == NEEDS_ORDERING
    assert inventory.current_amount_in_need_meters == Decimal("1.500")


async def test_unfinished_net_state_settles_nothing(db_session):
    workspace, user, suffix = await _seed(db_session)
    task, _, _, req, inventory, _ = await _seed_graph(
        db_session, workspace, user, f"{suffix}e", req_state=NEEDS_ORDERING,
        task_state=TaskStateEnum.WORKING,
    )

    events = await settle_finished_task_upholstery(
        db_session,
        [(task, TaskStateEnum.READY)],  # e.g. reopened ready -> working
        workspace_id=workspace.client_id,
        actor_user_id=user.client_id,
        now=datetime.now(timezone.utc),
    )
    await _refresh(db_session, req, inventory)

    assert events == []
    assert req.state == NEEDS_ORDERING
    assert inventory.current_amount_in_need_meters == Decimal("1.500")


async def test_settling_twice_is_a_no_op(db_session):
    workspace, user, suffix = await _seed(db_session)
    task, _, _, req, inventory, _ = await _seed_graph(
        db_session, workspace, user, f"{suffix}f", req_state=NEEDS_ORDERING,
        task_state=TaskStateEnum.READY,
    )
    kwargs = dict(
        workspace_id=workspace.client_id, actor_user_id=user.client_id,
        now=datetime.now(timezone.utc),
    )

    first = await settle_finished_task_upholstery(db_session, [(task, TaskStateEnum.WORKING)], **kwargs)
    second = await settle_finished_task_upholstery(db_session, [(task, TaskStateEnum.WORKING)], **kwargs)
    await _refresh(db_session, req, inventory)

    assert len(first) == 1 and second == []
    assert req.state == FAILED
    assert inventory.current_amount_in_need_meters == Decimal("0.000")


# --- restore ---------------------------------------------------------------------------


async def test_restoring_a_finished_task_does_not_revive_a_fabric_need(db_session, dispatched):
    workspace, user, suffix = await _seed(db_session)
    task, item, iup, req, inventory, _ = await _seed_graph(
        db_session, workspace, user, f"{suffix}g", req_state=AVAILABLE,
        task_state=TaskStateEnum.READY, stored=Decimal("2.000"),
    )

    await delete_task(_ctx(db_session, workspace, user, {"client_id": task.client_id}))
    await restore_task(_ctx(db_session, workspace, user, {"client_id": task.client_id}))
    await _refresh(db_session, task, inventory)

    assert task.is_deleted is False and task.state == TaskStateEnum.READY
    live = (
        await db_session.execute(
            select(ItemUpholsteryRequirement)
            .join(ItemUpholstery, ItemUpholstery.client_id == ItemUpholsteryRequirement.item_upholstery_id)
            .where(
                ItemUpholstery.item_id == item.client_id,
                ItemUpholstery.is_deleted.is_(False),
                ItemUpholsteryRequirement.state != FAILED,
            )
        )
    ).scalars().all()
    assert live == []
    assert inventory.current_amount_in_need_meters == Decimal("0.000")
    assert await _order_list(db_session, workspace, user) == []


# --- one-off cleanup script ---------------------------------------------------------


async def test_backfill_settles_stranded_rows_and_only_those(db_session):
    from scripts.backfill.settle_finished_task_upholstery import settle_finished_tasks

    workspace, user, suffix = await _seed(db_session)
    _, _, _, stranded, stranded_inv, _ = await _seed_graph(
        db_session, workspace, user, f"{suffix}h", req_state=NEEDS_ORDERING,
        task_state=TaskStateEnum.READY,
    )
    _, _, _, live, live_inv, _ = await _seed_graph(
        db_session, workspace, user, f"{suffix}i", req_state=NEEDS_ORDERING,
        task_state=TaskStateEnum.WORKING,
    )

    cancelled = await settle_finished_tasks(
        db_session, workspace_id=workspace.client_id, task_id=None
    )
    await _refresh(db_session, stranded, stranded_inv, live, live_inv)

    assert [row.requirement_id for row in cancelled] == [stranded.client_id]
    assert stranded.state == FAILED
    assert stranded_inv.current_amount_in_need_meters == Decimal("0.000")
    assert live.state == NEEDS_ORDERING
    assert live_inv.current_amount_in_need_meters == Decimal("1.500")
    trigger = (
        await db_session.execute(
            select(UpholsteryInventoryHistoryRecord.trigger).where(
                UpholsteryInventoryHistoryRecord.upholstery_inventory_id == stranded_inv.client_id
            )
        )
    ).scalars().all()
    assert trigger == ["maintenance_script"]
    assert await settle_finished_tasks(
        db_session, workspace_id=workspace.client_id, task_id=None
    ) == []
