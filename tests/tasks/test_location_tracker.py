from __future__ import annotations

from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.location_tracker.push_item_locations import push_item_locations
from beyo_manager.services.commands.location_tracker.requests import (
    parse_push_item_locations_request,
    parse_search_item_locations_request,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.location_tracker.search_item_locations import search_item_locations
from beyo_manager.services.tasks.location_tracker.handle_push_item_locations import (
    handle_push_item_locations,
)


class _Begin:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Session:
    def in_transaction(self) -> bool:
        return False

    def begin(self):
        return _Begin()


def _ctx(
    session: _Session,
    incoming_data: dict[str, Any],
    *,
    query_params: dict[str, Any] | None = None,
) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": "ws_1", "user_id": "usr_1", "username": "alice"},
        incoming_data=incoming_data,
        query_params=query_params or {},
        session=cast(AsyncSession, session),
    )


@pytest.mark.asyncio
async def test_push_item_locations_enqueues_task_with_default_username(monkeypatch) -> None:
    session = _Session()
    create_task_calls: list[dict[str, Any]] = []

    async def _create_instant_task(**kwargs):
        create_task_calls.append(kwargs)

        class _Task:
            client_id = "tsk_1"

        return _Task()

    monkeypatch.setattr(
        "beyo_manager.services.commands.location_tracker.push_item_locations.create_instant_task",
        _create_instant_task,
    )

    result = await push_item_locations(
        _ctx(
            session,
            {
                "entries": [
                    {
                        "position": "Shelf A",
                        "item_targets": [{"article_number": "ART-1"}],
                    }
                ]
            },
        )
    )

    assert result == {"enqueued": True, "task_client_id": "tsk_1", "queued_count": 1}
    assert create_task_calls[0]["task_type"].value == "location_tracker_push_locations"
    assert create_task_calls[0]["payload"]["requested_by_user_id"] == "usr_1"
    assert create_task_calls[0]["payload"]["changes"] == [
        {
            "position": "Shelf A",
            "item_targets": [{"article_number": "ART-1", "sku": None}],
            "username": "alice",
        }
    ]


def test_push_item_locations_request_validation_rejects_empty_position() -> None:
    with pytest.raises(ValidationError):
        parse_push_item_locations_request(
            {
                "entries": [
                    {
                        "position": "  ",
                        "item_targets": [{"article_number": "ART-1"}],
                    }
                ]
            }
        )


def test_search_item_locations_request_validation_rejects_unknown_identity() -> None:
    with pytest.raises(ValidationError):
        parse_search_item_locations_request({"q": "chair", "item_identity": "article_number,barcode"})


@pytest.mark.asyncio
async def test_search_item_locations_maps_client_response(monkeypatch) -> None:
    session = _Session()

    class _Client:
        def __init__(self):
            self.calls: list[tuple[str, list[str]]] = []

        async def get_item_locations(self, q: str, item_identity: list[str]) -> list[dict[str, Any]]:
            self.calls.append((q, item_identity))
            return [
                {
                    "item_article_number": "ART-1",
                    "sku": "SKU-1",
                    "item_position": "Aisle 3",
                }
            ]

    client = _Client()
    monkeypatch.setattr(
        "beyo_manager.services.queries.location_tracker.search_item_locations.get_location_tracker_client",
        lambda: client,
    )

    result = await search_item_locations(
        _ctx(
            session,
            {},
            query_params={"q": "  desk  ", "item_identity": "sku"},
        )
    )

    assert client.calls == [("desk", ["sku"])]
    assert result == [
        {
            "item_article_number": "ART-1",
            "sku": "SKU-1",
            "item_position": "Aisle 3",
        }
    ]


@pytest.mark.asyncio
async def test_location_tracker_worker_propagates_external_service_error(monkeypatch) -> None:
    class _Client:
        async def patch_item_locations(self, changes):
            raise ExternalServiceError("Location tracker unavailable.")

    monkeypatch.setattr(
        "beyo_manager.services.tasks.location_tracker.handle_push_item_locations.get_location_tracker_client",
        lambda: _Client(),
    )

    with pytest.raises(ExternalServiceError):
        await handle_push_item_locations(
            {
                "changes": [
                    {
                        "position": "Shelf A",
                        "item_targets": [{"article_number": "ART-1", "sku": None}],
                        "username": "alice",
                    }
                ],
                "requested_by_user_id": "usr_1",
            },
            "tsk_1",
        )
