from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.errors.not_found import NotFound
from beyo_manager.services.commands.items.create_item_upholstery import create_item_upholstery
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
    def __init__(self, *, execute_results: list[Any] | None = None):
        self.execute_results = list(execute_results or [])
        self.added: list[Any] = []
        self.flush_calls = 0

    def in_transaction(self) -> bool:
        return False

    def begin(self):
        return _Begin()

    async def execute(self, _query):
        if self.execute_results:
            return _ScalarResult(self.execute_results.pop(0))
        return _ScalarResult(None)

    async def get(self, _model, _client_id):
        return None

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
async def test_create_item_upholstery_rejects_missing_internal_upholstery() -> None:
    session = _Session(execute_results=[object(), None])

    with pytest.raises(NotFound, match="Upholstery not found"):
        await create_item_upholstery(
            _ctx(
                session,
                {
                    "item_id": "itm_1",
                    "upholstery_id": "uph_missing",
                    "source": "internal",
                },
            )
        )

    assert session.added == []
    assert session.flush_calls == 0
