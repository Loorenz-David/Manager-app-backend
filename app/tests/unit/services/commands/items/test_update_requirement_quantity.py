from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import (
    ItemUpholsteryRequirementStateEnum,
    ItemUpholsterySourceEnum,
)
from beyo_manager.services.context import ServiceContext


class _ScalarResult:
    def __init__(self, value: Any):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _Begin:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Session:
    def __init__(self, *, execute_results: list[Any]):
        self.execute_results = list(execute_results)

    def in_transaction(self) -> bool:
        return False

    def begin(self):
        return _Begin()

    async def execute(self, _query):
        return _ScalarResult(self.execute_results.pop(0))


def _ctx(session: _Session, incoming_data: dict[str, Any]) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": "ws_1", "user_id": "usr_1"},
        incoming_data=incoming_data,
        session=cast(AsyncSession, session),
    )


@pytest.mark.unit
async def test_update_requirement_quantity_updates_deferred_selection_without_requirement(
    monkeypatch,
) -> None:
    command_module = __import__(
        "beyo_manager.services.commands.items.update_requirement_quantity",
        fromlist=["update_requirement_quantity"],
    )
    dispatched: list[list[Any]] = []

    async def fake_dispatch(events):
        dispatched.append(events)

    monkeypatch.setattr(command_module.event_bus, "dispatch", fake_dispatch)

    iup = SimpleNamespace(
        client_id="iup_1",
        active_requirement_id=None,
        source=ItemUpholsterySourceEnum.INTERNAL,
        upholstery_id=None,
        amount_meters=Decimal("1.500"),
        updated_by_id=None,
    )

    result = await command_module.update_requirement_quantity(
        _ctx(
            _Session(execute_results=[iup]),
            {"item_upholstery_id": "iup_1", "amount_meters": "2.500"},
        )
    )

    assert result == {}
    assert iup.amount_meters == Decimal("2.500")
    assert iup.updated_by_id == "usr_1"
    assert len(dispatched) == 1
    assert [event.event_name for event in dispatched[0]] == ["item:upholstery-updated"]


@pytest.mark.unit
async def test_update_requirement_quantity_updates_customer_quantity_without_inventory(
    monkeypatch,
) -> None:
    command_module = __import__(
        "beyo_manager.services.commands.items.update_requirement_quantity",
        fromlist=["update_requirement_quantity"],
    )
    dispatched: list[list[Any]] = []

    async def fake_dispatch(events):
        dispatched.append(events)

    monkeypatch.setattr(command_module.event_bus, "dispatch", fake_dispatch)

    iup = SimpleNamespace(
        client_id="iup_1",
        active_requirement_id="iur_1",
        source=ItemUpholsterySourceEnum.CUSTOMER,
        upholstery_id=None,
        amount_meters=None,
        updated_by_id=None,
    )
    requirement = SimpleNamespace(
        amount_meters=None,
        upholstery_inventory_id=None,
        state=ItemUpholsteryRequirementStateEnum.MISSING_QUANTITY,
        updated_by_id=None,
    )

    result = await command_module.update_requirement_quantity(
        _ctx(
            _Session(execute_results=[iup, requirement]),
            {"item_upholstery_id": "iup_1", "amount_meters": "2.500"},
        )
    )

    assert result == {}
    assert iup.amount_meters == Decimal("2.500")
    assert requirement.amount_meters == Decimal("2.500")
    assert requirement.state == ItemUpholsteryRequirementStateEnum.AVAILABLE
    assert [event.event_name for event in dispatched[0]] == [
        "item:upholstery-updated",
        "item:upholstery-requirement-state-changed",
    ]
