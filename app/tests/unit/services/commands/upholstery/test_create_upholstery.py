from decimal import Decimal
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.services.commands.upholstery.create_upholstery import create_upholstery
from beyo_manager.services.commands.upholstery.requests import parse_create_upholstery_request
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
    def __init__(self, *, get_results: list[Any] | None = None, execute_results: list[Any] | None = None):
        self.get_results = list(get_results or [])
        self.execute_results = list(execute_results or [])
        self.added: list[Any] = []
        self.flush_calls = 0

    def begin(self):
        return _Begin()

    async def get(self, _model, _client_id):
        if self.get_results:
            return self.get_results.pop(0)
        return None

    async def execute(self, _query):
        if self.execute_results:
            return _ScalarResult(self.execute_results.pop(0))
        return _ScalarResult(None)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flush_calls += 1


def _ctx(session: _Session, incoming_data: dict[str, Any]) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": "ws_1", "user_id": "usr_1"},
        incoming_data=incoming_data,
        session=cast(AsyncSession, session),
    )


@pytest.mark.unit
async def test_create_upholstery_creates_inline_category_and_links_it() -> None:
    # Provides an explicit client_id so category.client_id is set at construction time.
    # The DB-generated client_id path (create_category without client_id) requires a real
    # flush to assign the value and can only be verified in an integration test.
    session = _Session()

    result = await create_upholstery(
        _ctx(
            session,
            {
                "client_id": "uph_01ARZ3NDEKTSV4RRFFQ69G5FAA",
                "name": "Blue Velvet",
                "current_stored_amount_meters": Decimal("2.000"),
                "create_category": {
                    "client_id": "upc_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                    "name": "Mobeltyger",
                    "image_url": None,
                    "favorite": False,
                },
            },
        )
    )

    category = session.added[0]
    upholstery = session.added[1]
    inventory = session.added[2]

    assert category.name == "Mobeltyger"
    assert upholstery.upholstery_category_id == "upc_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert inventory.upholstery_id == "uph_01ARZ3NDEKTSV4RRFFQ69G5FAA"
    assert session.flush_calls == 2
    assert result["upholstery"]["upholstery_category"]["id"] == "upc_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert result["upholstery"]["upholstery_category"]["name"] == "Mobeltyger"


@pytest.mark.unit
async def test_create_upholstery_rejects_inline_category_name_conflict() -> None:
    session = _Session(execute_results=[None, object()])

    with pytest.raises(ConflictError, match="category with this name already exists"):
        await create_upholstery(
            _ctx(
                session,
                {
                    "client_id": "uph_01ARZ3NDEKTSV4RRFFQ69G5FAA",
                    "name": "Blue Velvet",
                    "create_category": {
                        "client_id": "upc_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                        "name": "Mobeltyger",
                    },
                },
            )
        )

    assert session.added == []


@pytest.mark.unit
async def test_create_upholstery_creates_supplier_link_and_page_link() -> None:
    session = _Session()

    result = await create_upholstery(
        _ctx(
            session,
            {
                "client_id": "uph_01ARZ3NDEKTSV4RRFFQ69G5FAB",
                "name": "Green Linen",
                "page_link": "https://supplier.example/products/green-linen",
                "supplier_name": "Nevotex",
                "supplier_base_url": "https://supplier.example",
            },
        )
    )

    upholstery = session.added[0]
    inventory = session.added[1]
    supplier = session.added[2]
    supplier_link = session.added[3]

    assert upholstery.page_link == "https://supplier.example/products/green-linen"
    assert inventory.upholstery_id == "uph_01ARZ3NDEKTSV4RRFFQ69G5FAB"
    assert supplier.name == "Nevotex"
    assert supplier.base_url == "https://supplier.example"
    assert supplier_link.upholstery_id == "uph_01ARZ3NDEKTSV4RRFFQ69G5FAB"
    assert supplier_link.preferred is True
    assert result["upholstery"]["page_link"] == "https://supplier.example/products/green-linen"
    assert result["upholstery"]["supplier_name"] == "Nevotex"


@pytest.mark.unit
def test_parse_create_upholstery_request_requires_supplier_name_when_supplier_details_present() -> None:
    with pytest.raises(
        ValidationError,
        match="supplier_name is required when supplier details are provided",
    ):
        parse_create_upholstery_request(
            {
                "name": "Green Linen",
                "supplier_base_url": "https://supplier.example",
            }
        )
