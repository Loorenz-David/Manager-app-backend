"""Editing an upholstery order's amount (PLAN_edit_upholstery_order_amount_20261116).

The inventory's ordered bucket moves by the delta, and ``ordered`` / ``needs_ordering``
requirements follow the same allocation rules order creation uses."""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text, update

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.upholstery.enums import (
    InventoryMovementTriggerEnum,
    InventoryMovementTypeEnum,
    UpholsteryOrderStateEnum,
)
from beyo_manager.models import database
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.upholstery.upholstery_order_history_record import (
    UpholsteryOrderHistoryRecord,
)
from beyo_manager.services.commands.upholstery.create_upholstery_order import create_upholstery_order
from beyo_manager.services.commands.upholstery.receive_upholstery_order import receive_upholstery_order
from beyo_manager.services.commands.upholstery.update_upholstery_order_amount import (
    update_upholstery_order_amount,
)
from beyo_manager.services.queries.upholstery.upholstery_order_needs import list_upholstery_order_needs
from beyo_manager.services.run_service import run_service
from tests.integration.services.commands.upholstery.test_inventory_history_integration import (
    _ctx,
    _inventory,
    _ledger,
    _seed,
    dispatched,  # noqa: F401 — fixture
)

pytestmark = [pytest.mark.integration]

NO = ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
ORD = ItemUpholsteryRequirementStateEnum.ORDERED
BOUND = 0.4


async def _setup(db_session, amounts, *, order=None, stored="0.000"):
    """Requirements all needs_ordering; task i is due i days from now (1 = earliest)."""
    g = await _seed(
        db_session,
        stored=stored,
        in_need=str(sum(Decimal(a) for a in amounts)),
        requirements=[(a, NO) for a in amounts],
    )
    now = datetime.now(timezone.utc)
    for i, task_id in enumerate(g["task"], start=1):
        await db_session.execute(
            update(Task).where(Task.client_id == task_id).values(ready_by_at=now + timedelta(days=i))
        )
    await db_session.commit()  # the order commands open their own transaction
    if order is not None:
        created = await run_service(
            create_upholstery_order,
            _ctx(db_session, g, {"upholstery_id": g["uph"], "order_amount_meters": Decimal(order)}),
        )
        assert created.success, created.error
        g["order"] = created.data["client_id"]
    return g


async def _edit(db_session, g, amount):
    await db_session.commit()  # end the read transaction the assertions opened
    return await run_service(
        update_upholstery_order_amount,
        _ctx(db_session, g, {"client_id": g["order"], "order_amount_meters": Decimal(amount)}),
    )


async def _states(db_session, g):
    rows = (
        await db_session.execute(
            select(ItemUpholsteryRequirement)
            .where(ItemUpholsteryRequirement.client_id.in_(g["req"]))
            .execution_options(populate_existing=True)
        )
    ).scalars().all()
    by_id = {r.client_id: r for r in rows}
    return [by_id[r] for r in g["req"]]


async def _shortage(db_session, g):
    items = (
        await list_upholstery_order_needs(_ctx(db_session, g, query_params={"limit": 50, "offset": 0}))
    )["upholstery_needs_pagination"]["items"]
    return [i["amount_to_order_meters"] for i in items]


async def _order_history_count(db_session, order_id):
    return await db_session.scalar(
        select(func.count()).where(UpholsteryOrderHistoryRecord.upholstery_order_id == order_id)
    )


async def test_increase_covers_waiting_items_earliest_due_first(db_session, dispatched):
    g = await _setup(db_session, ["1.500", "1.500"], order="1.500")
    assert [r.state for r in await _states(db_session, g)] == [ORD, NO]
    history_before = await _order_history_count(db_session, g["order"])
    dispatched.clear()

    outcome = await _edit(db_session, g, "3.000")

    assert outcome.success, outcome.error
    assert outcome.data == {
        "client_id": g["order"], "state": "ordered",
        "order_amount_meters": 3.0, "received_amount_meters": None,
    }
    assert [r.state for r in await _states(db_session, g)] == [ORD, ORD]
    assert (await _inventory(db_session, g["inv"])).current_amount_ordered_meters == Decimal("3.000")
    assert await _shortage(db_session, g) == []

    parent = [r for r in await _ledger(db_session, g["inv"]) if r.parent_record_id is None][-1]
    assert parent.movement_type == InventoryMovementTypeEnum.ORDER_AMOUNT_CHANGED
    assert parent.trigger == InventoryMovementTriggerEnum.ORDER_AMOUNT_CHANGED.value
    assert parent.quantity_meters == Decimal("1.500")
    assert parent.upholstery_order_id == g["order"]
    children = [r for r in await _ledger(db_session, g["inv"]) if r.parent_record_id == parent.client_id]
    assert [(c.requirement_id, c.requirement_from_state, c.requirement_to_state) for c in children] == [
        (g["req"][1], NO, ORD)
    ]
    assert await _order_history_count(db_session, g["order"]) == history_before + 1

    assert [(e.event_name, e.extra) for e in dispatched if e.event_name.startswith(("upholstery:order", "item:"))] == [
        ("upholstery:order-updated", {"state": "ordered", "order_amount_meters": 3.0}),
        ("item:upholstery-requirement-state-changed", {"ids": [g["iup"][1]], "new_state": "ordered"}),
    ]


async def test_decrease_returns_latest_due_items_to_needs_ordering(db_session, dispatched):
    g = await _setup(db_session, ["1.500", "1.500", "1.500"], order="4.500")
    assert [r.state for r in await _states(db_session, g)] == [ORD, ORD, ORD]
    dispatched.clear()

    outcome = await _edit(db_session, g, "1.500")

    assert outcome.success, outcome.error
    first, second, third = await _states(db_session, g)
    assert [first.state, second.state, third.state] == [ORD, NO, NO]
    assert first.ordered_at is not None
    assert second.ordered_at is None and third.ordered_at is None
    assert (await _inventory(db_session, g["inv"])).current_amount_ordered_meters == Decimal("1.500")
    assert await _shortage(db_session, g) == [3.0]
    demoted = [e for e in dispatched if e.extra.get("new_state") == "needs_ordering"]
    assert [e.extra["ids"] for e in demoted] == [sorted(g["iup"][1:])]


async def test_decrease_still_covers_a_smaller_item_that_fits(db_session, dispatched):
    """Skip-and-continue: 3 m (due first) and 1 m (due later) on a 4 m order, cut to 1 m."""
    g = await _setup(db_session, ["3.000", "1.000"], order="4.000")

    assert (await _edit(db_session, g, "1.000")).success

    big, small = await _states(db_session, g)
    assert (big.state, small.state) == (NO, ORD)
    parent = [r for r in await _ledger(db_session, g["inv"]) if r.parent_record_id is None][-1]
    children = [r for r in await _ledger(db_session, g["inv"]) if r.parent_record_id == parent.client_id]
    # the small one was demoted and re-promoted in the same call: no net transition
    assert [(c.requirement_id, c.requirement_to_state) for c in children] == [(g["req"][0], NO)]


async def test_cannot_go_below_received_and_equal_closes_the_order(db_session, dispatched):
    g = await _setup(db_session, ["2.000", "3.000"], order="5.000")
    received = await run_service(
        receive_upholstery_order,
        _ctx(db_session, g, {"client_id": g["order"], "received_amount_meters": Decimal("2")}),
    )
    assert received.success and received.data["state"] == "partially_received"
    ledger_before = len(await _ledger(db_session, g["inv"]))

    too_low = await _edit(db_session, g, "1.500")
    assert not too_low.success
    assert "2.000 m already received" in str(too_low.error)
    assert len(await _ledger(db_session, g["inv"])) == ledger_before

    closed = await _edit(db_session, g, "2.000")
    assert closed.success, closed.error
    assert closed.data["state"] == "received"
    assert (await _inventory(db_session, g["inv"])).current_amount_ordered_meters == Decimal("0.000")
    # the 3 m item lost its incoming fabric
    assert [r.state for r in await _states(db_session, g)][1] == NO


async def test_closed_orders_are_refused(db_session, dispatched):
    g = await _setup(db_session, ["1.000"], order="1.000")
    assert (await run_service(
        receive_upholstery_order,
        _ctx(db_session, g, {"client_id": g["order"], "received_amount_meters": Decimal("1")}),
    )).success

    outcome = await _edit(db_session, g, "2.000")

    assert not outcome.success
    assert "can no longer be changed" in str(outcome.error)


async def test_uncounted_order_changes_only_the_field(db_session, dispatched):
    g = await _setup(db_session, ["1.000"])
    created = await run_service(
        create_upholstery_order,
        _ctx(db_session, g, {
            "upholstery_id": g["uph"], "order_amount_meters": Decimal("1"),
            "state": UpholsteryOrderStateEnum.PENDING,
        }),
    )
    g["order"] = created.data["client_id"]
    ledger_before = len(await _ledger(db_session, g["inv"]))

    outcome = await _edit(db_session, g, "4.000")

    assert outcome.success and outcome.data["order_amount_meters"] == 4.0
    assert len(await _ledger(db_session, g["inv"])) == ledger_before
    assert (await _inventory(db_session, g["inv"])).current_amount_ordered_meters == Decimal("0.000")
    assert [r.state for r in await _states(db_session, g)] == [NO]


async def test_same_amount_writes_nothing(db_session, dispatched):
    g = await _setup(db_session, ["1.000"], order="1.000")
    ledger_before = len(await _ledger(db_session, g["inv"]))
    history_before = await _order_history_count(db_session, g["order"])
    dispatched.clear()

    outcome = await _edit(db_session, g, "1.000")

    assert outcome.success
    assert len(await _ledger(db_session, g["inv"])) == ledger_before
    assert await _order_history_count(db_session, g["order"]) == history_before
    assert [e for e in dispatched if e.event_name.startswith(("upholstery:order", "item:"))] == []


@pytest.mark.parametrize(
    "command, concurrent_write, data, refusal",
    [
        # A receipt commits while the edit waits: the edit must see it and refuse.
        (
            "edit",
            "UPDATE upholstery_orders SET received_amount_meters = 2, state = 'partially_received' "
            "WHERE client_id = :o",
            {"order_amount_meters": Decimal("1")},
            "already received",
        ),
        # An edit commits while the receipt waits: the receipt must see the new cap.
        (
            "receive",
            "UPDATE upholstery_orders SET order_amount_meters = 1 WHERE client_id = :o",
            {"received_amount_meters": Decimal("2")},
            "exceeds the ordered amount",
        ),
    ],
)
async def test_edit_and_receive_read_the_order_under_its_row_lock(
    db_session, dispatched, command, concurrent_write, data, refusal
):
    """Each command must check against the order as committed by whoever held the row,
    not a value read before it waited (a plain read would pass the check, then block on
    its own UPDATE, then write past the new limit)."""
    g = await _setup(db_session, ["2.000"], order="2.000")
    lock_session = database._session_factory()
    work_session = database._session_factory()
    task = None
    fn = update_upholstery_order_amount if command == "edit" else receive_upholstery_order
    try:
        await lock_session.begin()
        await lock_session.execute(text(concurrent_write), {"o": g["order"]})
        task = asyncio.create_task(
            run_service(fn, _ctx(work_session, g, {"client_id": g["order"], **data}))
        )
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(task), timeout=BOUND)
        blocked = not task.done()

        await lock_session.commit()
        outcome = await asyncio.wait_for(task, timeout=5)
        assert blocked is True
        assert not outcome.success, outcome.data
        assert refusal in str(outcome.error)
    finally:
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await lock_session.close()
        await work_session.close()
