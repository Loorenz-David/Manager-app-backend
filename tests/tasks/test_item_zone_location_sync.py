from __future__ import annotations

from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.tasks.enums import TaskPostHandlingStateEnum
from beyo_manager.domain.tasks.enums import TaskTypeEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_post_handling import TaskPostHandling
from beyo_manager.services.commands.items.create_item import create_item
from beyo_manager.services.commands.items.find_or_create_item import find_or_create_item
from beyo_manager.services.commands.items.requests import (
    CreateItemRequest,
    FindOrCreateItemRequest,
    UpdateItemRequest,
)
from beyo_manager.services.commands.items.update_item import _update_item_in_session
from beyo_manager.services.commands.location_tracker.enqueue_item_zone_push import (
    enqueue_item_zone_location_push,
)
from beyo_manager.services.commands.task_post_handling.complete_task_post_handling import (
    complete_task_post_handling,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


class _Begin:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _ScalarResult:
    def __init__(self, value: Any):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _Session:
    def __init__(self, *, execute_results: list[Any] | None = None, get_results: dict[str, Any] | None = None):
        self._execute_results = list(execute_results or [])
        self._get_results = dict(get_results or {})
        self.added: list[Any] = []

    def in_transaction(self) -> bool:
        return False

    def begin(self):
        return _Begin()

    async def execute(self, _statement):
        if not self._execute_results:
            raise AssertionError("Unexpected execute call.")
        return _ScalarResult(self._execute_results.pop(0))

    async def get(self, _model, client_id: str):
        return self._get_results.get(client_id)

    def add(self, value: Any) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        return None


def _ctx(session: _Session, incoming_data: dict[str, Any]) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": "ws_1", "user_id": "usr_1", "username": "alice"},
        incoming_data=incoming_data,
        session=cast(AsyncSession, session),
    )


@pytest.mark.asyncio
async def test_enqueue_item_zone_location_push_enqueues_existing_job(monkeypatch) -> None:
    create_task_calls: list[dict[str, Any]] = []

    async def _create_instant_task(**kwargs):
        create_task_calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        "beyo_manager.services.commands.location_tracker.enqueue_item_zone_push.create_instant_task",
        _create_instant_task,
    )

    item = Item(
        client_id="itm_1",
        workspace_id="ws_1",
        article_number="ART-1",
        item_zone=" Shelf A ",
    )

    enqueued = await enqueue_item_zone_location_push(
        object(),
        item,
        username="alice",
        requested_by_user_id="usr_1",
    )

    assert enqueued is True
    assert create_task_calls[0]["task_type"].value == "location_tracker_push_locations"
    assert create_task_calls[0]["max_try"] == 3
    assert create_task_calls[0]["payload"] == {
        "changes": [
            {
                "position": "Shelf A",
                "item_targets": [{"article_number": "ART-1"}],
                "username": "alice",
            }
        ],
        "requested_by_user_id": "usr_1",
    }


@pytest.mark.asyncio
async def test_enqueue_item_zone_location_push_skips_when_missing_zone_or_target(monkeypatch) -> None:
    create_task_calls: list[dict[str, Any]] = []

    async def _create_instant_task(**kwargs):
        create_task_calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        "beyo_manager.services.commands.location_tracker.enqueue_item_zone_push.create_instant_task",
        _create_instant_task,
    )

    no_zone = Item(client_id="itm_1", workspace_id="ws_1", article_number="ART-1", item_zone="   ")
    no_target = Item(client_id="itm_2", workspace_id="ws_1", item_zone="Zone A")

    assert await enqueue_item_zone_location_push(object(), no_zone, username="alice", requested_by_user_id="usr_1") is False
    assert await enqueue_item_zone_location_push(object(), no_target, username="alice", requested_by_user_id="usr_1") is False
    assert create_task_calls == []


@pytest.mark.asyncio
async def test_create_item_triggers_zone_push_when_item_zone_present(monkeypatch) -> None:
    session = _Session()
    push_calls: list[str | None] = []

    async def _enqueue(_session, item, **_kwargs):
        push_calls.append(item.item_zone)
        return True

    async def _history(**_kwargs):
        return None

    async def _dispatch(_events):
        return None

    monkeypatch.setattr(
        "beyo_manager.services.commands.items.create_item.parse_create_item_request",
        lambda _data: CreateItemRequest(article_number="ART-1", item_zone="Zone A"),
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.items.create_item.enqueue_item_zone_location_push",
        _enqueue,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.items.create_item._create_history_record_in_session",
        _history,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.items.create_item.event_bus.dispatch",
        _dispatch,
    )

    await create_item(_ctx(session, {}))

    assert push_calls == ["Zone A"]


@pytest.mark.asyncio
async def test_find_or_create_item_triggers_zone_push_for_update_branch(monkeypatch) -> None:
    existing = Item(client_id="itm_1", workspace_id="ws_1", article_number="ART-1")
    session = _Session(execute_results=[existing])
    push_calls: list[str | None] = []

    async def _enqueue(_session, item, **_kwargs):
        push_calls.append(item.item_zone)
        return True

    monkeypatch.setattr(
        "beyo_manager.services.commands.items.find_or_create_item.parse_find_or_create_item_request",
        lambda _data: FindOrCreateItemRequest(article_number="ART-1", item_zone="Zone B"),
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.items.find_or_create_item.enqueue_item_zone_location_push",
        _enqueue,
    )

    result = await find_or_create_item(_ctx(session, {}))

    assert result == {"client_id": "itm_1", "was_created": False}
    assert existing.item_zone == "Zone B"
    assert push_calls == ["Zone B"]


@pytest.mark.asyncio
async def test_find_or_create_item_triggers_zone_push_for_create_branch(monkeypatch) -> None:
    session = _Session(execute_results=[None])
    push_calls: list[str | None] = []

    async def _enqueue(_session, item, **_kwargs):
        push_calls.append(item.item_zone)
        return True

    monkeypatch.setattr(
        "beyo_manager.services.commands.items.find_or_create_item.parse_find_or_create_item_request",
        lambda _data: FindOrCreateItemRequest(article_number="ART-1", item_zone="Zone C"),
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.items.find_or_create_item.enqueue_item_zone_location_push",
        _enqueue,
    )

    result = await find_or_create_item(_ctx(session, {}))

    assert result["was_created"] is True
    assert push_calls == ["Zone C"]


@pytest.mark.asyncio
async def test_update_item_in_session_updates_item_zone_and_leaves_item_position_untouched(monkeypatch) -> None:
    item = Item(
        client_id="itm_1",
        workspace_id="ws_1",
        article_number="ART-1",
        item_position="Warehouse Row 1",
        item_zone="Old Zone",
    )
    session = _Session(execute_results=[item])
    push_calls: list[str | None] = []

    async def _enqueue(_session, updated_item, **_kwargs):
        push_calls.append(updated_item.item_zone)
        return True

    async def _history(**_kwargs):
        return None

    monkeypatch.setattr(
        "beyo_manager.services.commands.items.update_item.enqueue_item_zone_location_push",
        _enqueue,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.items.update_item._create_history_record_in_session",
        _history,
    )

    updated_item, events = await _update_item_in_session(
        cast(AsyncSession, session),
        workspace_id="ws_1",
        user_id="usr_1",
        username="alice",
        request=UpdateItemRequest(client_id="itm_1", item_zone="New Zone"),
    )

    assert updated_item.item_zone == "New Zone"
    assert updated_item.item_position == "Warehouse Row 1"
    assert push_calls == ["New Zone"]
    assert len(events) == 1
    assert isinstance(events[0], WorkspaceEvent)
    assert events[0].event_name == "item:updated"


@pytest.mark.asyncio
async def test_complete_task_post_handling_prefers_request_completion_zone(monkeypatch) -> None:
    post_handling = TaskPostHandling(
        client_id="tph_1",
        workspace_id="ws_1",
        task_id="tsk_1",
        state=TaskPostHandlingStateEnum.FILLED,
    )
    task = Task(
        client_id="tsk_1",
        workspace_id="ws_1",
        task_scalar_id=1,
        task_type=TaskTypeEnum.INTERNAL,
        assortment="Fallback",
    )
    primary_item = Item(client_id="itm_1", workspace_id="ws_1")
    session = _Session(execute_results=[post_handling, task])
    dispatched_events: list[Any] = []
    update_requests: list[UpdateItemRequest] = []

    async def _load_primary_item(*_args, **_kwargs):
        return primary_item

    async def _update_item(*_args, request, **_kwargs):
        update_requests.append(request)
        return primary_item, [WorkspaceEvent(event_name="item:updated", client_id="itm_1", workspace_id="ws_1")]

    async def _history(**_kwargs):
        return None

    async def _dispatch(events):
        dispatched_events.extend(events)

    monkeypatch.setattr(
        "beyo_manager.services.commands.task_post_handling.complete_task_post_handling._load_primary_item",
        _load_primary_item,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_post_handling.complete_task_post_handling._update_item_in_session",
        _update_item,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_post_handling.complete_task_post_handling._create_history_record_in_session",
        _history,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_post_handling.complete_task_post_handling.event_bus.dispatch",
        _dispatch,
    )

    result = await complete_task_post_handling(
        _ctx(session, {"task_id": "tsk_1", "completion_zone": "  Final Zone  "})
    )

    assert result == {"client_id": "tph_1"}
    assert update_requests[0].item_zone == "Final Zone"
    assert "item_position" not in update_requests[0].model_fields_set
    assert [event.event_name for event in dispatched_events] == [
        "item:updated",
        "task_post_handling:completed",
    ]


@pytest.mark.asyncio
async def test_complete_task_post_handling_falls_back_to_task_assortment(monkeypatch) -> None:
    post_handling = TaskPostHandling(
        client_id="tph_1",
        workspace_id="ws_1",
        task_id="tsk_1",
        state=TaskPostHandlingStateEnum.FILLED,
    )
    task = Task(
        client_id="tsk_1",
        workspace_id="ws_1",
        task_scalar_id=1,
        task_type=TaskTypeEnum.INTERNAL,
        assortment="Assortment Zone",
    )
    primary_item = Item(client_id="itm_1", workspace_id="ws_1")
    session = _Session(execute_results=[post_handling, task])
    update_requests: list[UpdateItemRequest] = []

    async def _load_primary_item(*_args, **_kwargs):
        return primary_item

    async def _update_item(*_args, request, **_kwargs):
        update_requests.append(request)
        return primary_item, []

    async def _history(**_kwargs):
        return None

    async def _dispatch(_events):
        return None

    monkeypatch.setattr(
        "beyo_manager.services.commands.task_post_handling.complete_task_post_handling._load_primary_item",
        _load_primary_item,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_post_handling.complete_task_post_handling._update_item_in_session",
        _update_item,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_post_handling.complete_task_post_handling._create_history_record_in_session",
        _history,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_post_handling.complete_task_post_handling.event_bus.dispatch",
        _dispatch,
    )

    await complete_task_post_handling(_ctx(session, {"task_id": "tsk_1", "completion_zone": "   "}))

    assert update_requests[0].item_zone == "Assortment Zone"


@pytest.mark.asyncio
async def test_complete_task_post_handling_skips_item_write_when_no_effective_zone(monkeypatch) -> None:
    post_handling = TaskPostHandling(
        client_id="tph_1",
        workspace_id="ws_1",
        task_id="tsk_1",
        state=TaskPostHandlingStateEnum.FILLED,
    )
    task = Task(
        client_id="tsk_1",
        workspace_id="ws_1",
        task_scalar_id=1,
        task_type=TaskTypeEnum.INTERNAL,
        assortment=None,
    )
    session = _Session(execute_results=[post_handling, task])
    dispatched_events: list[Any] = []
    update_calls = 0

    async def _update_item(*_args, **_kwargs):
        nonlocal update_calls
        update_calls += 1
        return Item(client_id="itm_1", workspace_id="ws_1"), []

    async def _history(**_kwargs):
        return None

    async def _dispatch(events):
        dispatched_events.extend(events)

    monkeypatch.setattr(
        "beyo_manager.services.commands.task_post_handling.complete_task_post_handling._update_item_in_session",
        _update_item,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_post_handling.complete_task_post_handling._create_history_record_in_session",
        _history,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.task_post_handling.complete_task_post_handling.event_bus.dispatch",
        _dispatch,
    )

    result = await complete_task_post_handling(_ctx(session, {"task_id": "tsk_1"}))

    assert result == {"client_id": "tph_1"}
    assert update_calls == 0
    assert [event.event_name for event in dispatched_events] == ["task_post_handling:completed"]
