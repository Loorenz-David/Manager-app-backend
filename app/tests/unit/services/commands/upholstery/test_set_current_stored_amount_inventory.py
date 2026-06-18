from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.upholstery.set_current_stored_amount_inventory import (
    _demote_available_requirements,
    set_current_stored_amount_inventory,
)
from beyo_manager.services.commands.upholstery.requests import (
    parse_set_current_stored_amount_inventory_request,
)
from beyo_manager.services.context import ServiceContext


def _requirement(item_upholstery_id: str, amount: str, *, created_at: datetime) -> SimpleNamespace:
    return SimpleNamespace(
        item_upholstery_id=item_upholstery_id,
        amount_meters=Decimal(amount),
        state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
        created_at=created_at,
        updated_at=None,
        updated_by_id=None,
    )


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _Begin:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Session:
    def __init__(self, inventory):
        self.inventory = inventory
        self.flush_calls = 0
        self.execute_calls = 0

    def begin(self):
        return _Begin()

    async def execute(self, _query):
        self.execute_calls += 1
        return _ScalarResult(self.inventory)

    async def flush(self):
        self.flush_calls += 1


def _ctx(session: _Session, *, stored: str) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": "ws_1", "user_id": "usr_1", "role_name": "manager"},
        incoming_data={
            "client_id": "uin_1",
            "current_stored_amount_meters": Decimal(stored),
        },
        session=cast(AsyncSession, session),
    )


@pytest.mark.unit
def test_parse_set_current_stored_amount_inventory_request_quantizes_and_rejects_negative() -> None:
    parsed = parse_set_current_stored_amount_inventory_request(
        {"client_id": "uin_1", "current_stored_amount_meters": Decimal("1.2346")}
    )

    assert parsed.current_stored_amount_meters == Decimal("1.235")

    with pytest.raises(ValidationError, match="current_stored_amount_meters must be >= 0"):
        parse_set_current_stored_amount_inventory_request(
            {"client_id": "uin_1", "current_stored_amount_meters": Decimal("-0.001")}
        )


@pytest.mark.unit
def test_demote_available_requirements_prefers_no_deadline_then_latest_deadline_then_newest() -> None:
    now = datetime.now(timezone.utc)
    no_deadline = _requirement("iup_no_deadline", "1.000", created_at=now - timedelta(hours=2))
    late_deadline = _requirement("iup_late", "1.000", created_at=now - timedelta(hours=3))
    early_deadline = _requirement("iup_early", "1.000", created_at=now - timedelta(hours=1))

    demoted_ids = _demote_available_requirements(
        candidates=[early_deadline, late_deadline, no_deadline],
        new_stored_amount_meters=Decimal("1.000"),
        ready_by_at_map={
            "iup_late": now + timedelta(days=3),
            "iup_early": now + timedelta(days=1),
        },
        actor_id="usr_1",
    )

    assert demoted_ids == ["iup_no_deadline", "iup_late"]
    assert no_deadline.state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
    assert late_deadline.state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
    assert early_deadline.state == ItemUpholsteryRequirementStateEnum.AVAILABLE


@pytest.mark.unit
async def test_set_current_stored_amount_inventory_promotes_expected_candidates(monkeypatch) -> None:
    inventory = SimpleNamespace(
        client_id="uin_1",
        current_stored_amount_meters=Decimal("2.000"),
        current_amount_in_need_meters=Decimal("5.000"),
        current_amount_ordered_meters=Decimal("0.000"),
        low_stock_threshold_meters=None,
        inventory_condition=UpholsteryInventoryConditionEnum.OUT_OF_STOCK,
        updated_at=None,
        updated_by_id=None,
        workspace_id="ws_1",
        is_deleted=False,
    )
    order_req = _requirement(
        "iup_1",
        "2.000",
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    order_req.state = ItemUpholsteryRequirementStateEnum.ORDERED
    needs_req = _requirement(
        "iup_2",
        "1.000",
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    needs_req.state = ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
    session = _Session(inventory)
    dispatched = []

    async def _fake_load_candidates(**kwargs):
        states = kwargs["states"]
        if states == [ItemUpholsteryRequirementStateEnum.AVAILABLE]:
            return []
        return [order_req, needs_req]

    async def _fake_fetch_ready_by_at(*_args, **_kwargs):
        return {}

    async def _fake_dispatch(events):
        dispatched.extend(events)

    monkeypatch.setattr(
        "beyo_manager.services.commands.upholstery.set_current_stored_amount_inventory._load_requirement_candidates",
        _fake_load_candidates,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.upholstery.set_current_stored_amount_inventory.fetch_earliest_ready_by_at",
        _fake_fetch_ready_by_at,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.upholstery.set_current_stored_amount_inventory.event_bus.dispatch",
        _fake_dispatch,
    )

    await set_current_stored_amount_inventory(_ctx(session, stored="5.000"))

    assert inventory.current_stored_amount_meters == Decimal("5.000")
    assert inventory.current_amount_in_need_meters == Decimal("5.000")
    assert inventory.inventory_condition == UpholsteryInventoryConditionEnum.OUT_OF_STOCK
    assert order_req.state == ItemUpholsteryRequirementStateEnum.AVAILABLE
    assert needs_req.state == ItemUpholsteryRequirementStateEnum.AVAILABLE
    assert session.flush_calls == 1
    assert len(dispatched) == 1
    assert dispatched[0].extra == {
        "ids": ["iup_1", "iup_2"],
        "new_state": ItemUpholsteryRequirementStateEnum.AVAILABLE.value,
    }


@pytest.mark.unit
async def test_set_current_stored_amount_inventory_demotes_low_priority_available_first(monkeypatch) -> None:
    inventory = SimpleNamespace(
        client_id="uin_1",
        current_stored_amount_meters=Decimal("3.000"),
        current_amount_in_need_meters=Decimal("5.000"),
        current_amount_ordered_meters=Decimal("0.000"),
        low_stock_threshold_meters=None,
        inventory_condition=UpholsteryInventoryConditionEnum.OUT_OF_STOCK,
        updated_at=None,
        updated_by_id=None,
        workspace_id="ws_1",
        is_deleted=False,
    )
    older_available = _requirement(
        "iup_1",
        "2.000",
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    newer_available = _requirement(
        "iup_2",
        "1.000",
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    session = _Session(inventory)
    dispatched = []
    call_index = {"value": 0}

    async def _fake_load_candidates(**kwargs):
        call_index["value"] += 1
        states = kwargs["states"]
        if states == [ItemUpholsteryRequirementStateEnum.AVAILABLE]:
            return [older_available, newer_available]
        if call_index["value"] == 2:
            return []
        return [newer_available]

    async def _fake_fetch_ready_by_at(*_args, **_kwargs):
        return {}

    async def _fake_dispatch(events):
        dispatched.extend(events)

    monkeypatch.setattr(
        "beyo_manager.services.commands.upholstery.set_current_stored_amount_inventory._load_requirement_candidates",
        _fake_load_candidates,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.upholstery.set_current_stored_amount_inventory.fetch_earliest_ready_by_at",
        _fake_fetch_ready_by_at,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.upholstery.set_current_stored_amount_inventory.event_bus.dispatch",
        _fake_dispatch,
    )

    await set_current_stored_amount_inventory(_ctx(session, stored="2.000"))

    assert inventory.current_stored_amount_meters == Decimal("2.000")
    assert inventory.current_amount_in_need_meters == Decimal("5.000")
    assert older_available.state == ItemUpholsteryRequirementStateEnum.AVAILABLE
    assert newer_available.state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
    assert session.flush_calls == 1
    assert len(dispatched) == 1
    assert dispatched[0].extra == {
        "ids": ["iup_2"],
        "new_state": ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING.value,
    }


@pytest.mark.unit
async def test_set_current_stored_amount_inventory_noop_emits_no_events(monkeypatch) -> None:
    inventory = SimpleNamespace(
        client_id="uin_1",
        current_stored_amount_meters=Decimal("2.000"),
        current_amount_in_need_meters=Decimal("5.000"),
        current_amount_ordered_meters=Decimal("0.000"),
        low_stock_threshold_meters=None,
        inventory_condition=UpholsteryInventoryConditionEnum.OUT_OF_STOCK,
        updated_at=None,
        updated_by_id=None,
        workspace_id="ws_1",
        is_deleted=False,
    )
    session = _Session(inventory)
    dispatched = []

    async def _fake_dispatch(events):
        dispatched.extend(events)

    monkeypatch.setattr(
        "beyo_manager.services.commands.upholstery.set_current_stored_amount_inventory.event_bus.dispatch",
        _fake_dispatch,
    )

    await set_current_stored_amount_inventory(_ctx(session, stored="2.000"))

    assert inventory.updated_by_id is None
    assert session.flush_calls == 0
    assert dispatched == []


@pytest.mark.unit
async def test_set_current_stored_amount_inventory_not_found_raises() -> None:
    session = _Session(None)

    with pytest.raises(NotFound, match="UpholsteryInventory not found."):
        await set_current_stored_amount_inventory(_ctx(session, stored="1.000"))
