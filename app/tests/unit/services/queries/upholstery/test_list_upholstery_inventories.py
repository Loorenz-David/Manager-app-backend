from decimal import Decimal
from types import SimpleNamespace

import pytest

from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.upholstery.list_upholstery_inventories import (
    list_upholstery_inventories,
)


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def one_or_none(self):
        if not self._rows:
            return None
        return self._rows[0]


class _ScalarRowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Session:
    def __init__(self, inventory_rows, supplier_rows=None):
        self._inventory_rows = inventory_rows
        self._supplier_rows = supplier_rows or []
        self.execute_calls = 0
        self.first_query = None

    async def execute(self, _query):
        self.execute_calls += 1
        if self.execute_calls == 1:
            self.first_query = _query
            return _Result(self._inventory_rows)
        return _ScalarRowsResult(self._supplier_rows)


def _inventory(client_id: str):
    return SimpleNamespace(
        client_id=client_id,
        workspace_id="ws_1",
        upholstery_id=f"uph_{client_id}",
        inventory_condition=UpholsteryInventoryConditionEnum.AVAILABLE,
        current_stored_amount_meters=Decimal("4.500"),
        current_amount_in_need_meters=Decimal("1.750"),
        current_amount_ordered_meters=Decimal("1.250"),
        updated_at=None,
        created_at=None,
    )


def _compiled_sql(query) -> str:
    return str(query.compile(compile_kwargs={"literal_binds": True})).lower()


@pytest.mark.unit
async def test_list_upholstery_inventories_uses_partial_ordered_amount_from_inventory() -> None:
    inventory_rows = [
        (
            _inventory("uin_1"),
            "https://cdn.example.com/1.jpg",
            "Blue Velvet",
            "BLU-1",
            "https://supplier.example/blue-velvet",
            True,
        ),
        (
            _inventory("uin_2"),
            "https://cdn.example.com/2.jpg",
            "Green Linen",
            "GRN-2",
            "https://supplier.example/green-linen",
            False,
        ),
    ]
    session = _Session(
        inventory_rows,
        supplier_rows=[
            ("uph_uin_1", "nevotex"),
            ("uph_uin_2", "fargotex"),
        ],
    )
    ctx = ServiceContext(
        identity={"workspace_id": "ws_1"},
        incoming_data={},
        query_params={"limit": 50, "offset": 0},
        session=session,  # type: ignore[arg-type]
    )

    result = await list_upholstery_inventories(ctx)
    items = result["upholstery_inventories_pagination"]["items"]

    assert session.execute_calls == 2
    assert items[0]["client_id"] == "uin_1"
    assert items[0]["upholstery_id"] == "uph_uin_1"
    assert items[0]["upholstery_name"] == "Blue Velvet"
    assert items[0]["upholstery_code"] == "BLU-1"
    assert items[0]["favorite"] is True
    assert items[0]["page_link"] == "https://supplier.example/blue-velvet"
    assert items[0]["supplier_name"] == "nevotex"
    assert items[0]["current_amount_in_need_meters"] == "1.750"
    assert items[0]["current_amount_ordered_meters"] == "1.250"
    assert items[1]["client_id"] == "uin_2"
    assert items[1]["favorite"] is False
    assert items[1]["page_link"] == "https://supplier.example/green-linen"
    assert items[1]["supplier_name"] == "fargotex"
    assert items[1]["current_amount_in_need_meters"] == "1.750"
    assert items[1]["current_amount_ordered_meters"] == "1.250"
    assert result["upholstery_inventories_pagination"]["has_more"] is False


@pytest.mark.unit
async def test_list_upholstery_inventories_skips_count_query_when_page_is_empty() -> None:
    session = _Session([])
    ctx = ServiceContext(
        identity={"workspace_id": "ws_1"},
        incoming_data={},
        query_params={"limit": 50, "offset": 0},
        session=session,  # type: ignore[arg-type]
    )

    result = await list_upholstery_inventories(ctx)

    assert session.execute_calls == 1
    assert result["upholstery_inventories_pagination"]["items"] == []


@pytest.mark.unit
async def test_list_upholstery_inventories_adds_q_filter_for_name_and_code() -> None:
    inventory_rows = [(_inventory("uin_1"), None, "Blue Velvet", "BLU-1", None, True)]
    session = _Session(inventory_rows)
    ctx = ServiceContext(
        identity={"workspace_id": "ws_1"},
        incoming_data={},
        query_params={"limit": 50, "offset": 0, "q": "oak"},
        session=session,  # type: ignore[arg-type]
    )

    await list_upholstery_inventories(ctx)

    sql = _compiled_sql(session.first_query)
    assert "upholsteries.name" in sql
    assert "upholsteries.code" in sql
    assert "like lower('%oak%')" in sql


@pytest.mark.unit
async def test_list_upholstery_inventories_filters_favorite() -> None:
    inventory_rows = [(_inventory("uin_1"), None, "Blue Velvet", "BLU-1", None, True)]
    session = _Session(inventory_rows)
    ctx = ServiceContext(
        identity={"workspace_id": "ws_1"},
        incoming_data={},
        query_params={"limit": 50, "offset": 0, "favorite": True},
        session=session,  # type: ignore[arg-type]
    )

    await list_upholstery_inventories(ctx)

    sql = _compiled_sql(session.first_query)
    assert "upholsteries.favorite is true" in sql


@pytest.mark.unit
async def test_list_upholstery_inventories_filters_in_stock_true_to_available_and_low_stock() -> None:
    inventory_rows = [(_inventory("uin_1"), None, "Blue Velvet", "BLU-1", None, True)]
    session = _Session(inventory_rows)
    ctx = ServiceContext(
        identity={"workspace_id": "ws_1"},
        incoming_data={},
        query_params={"limit": 50, "offset": 0, "in_stock": True},
        session=session,  # type: ignore[arg-type]
    )

    await list_upholstery_inventories(ctx)

    sql = _compiled_sql(session.first_query)
    assert "inventory_condition in ('available', 'low_stock')" in sql


@pytest.mark.unit
async def test_list_upholstery_inventories_filters_in_stock_false_to_out_of_stock() -> None:
    inventory_rows = [(_inventory("uin_1"), None, "Blue Velvet", "BLU-1", None, True)]
    session = _Session(inventory_rows)
    ctx = ServiceContext(
        identity={"workspace_id": "ws_1"},
        incoming_data={},
        query_params={"limit": 50, "offset": 0, "in_stock": False},
        session=session,  # type: ignore[arg-type]
    )

    await list_upholstery_inventories(ctx)

    sql = _compiled_sql(session.first_query)
    assert "inventory_condition = 'out_of_stock'" in sql
