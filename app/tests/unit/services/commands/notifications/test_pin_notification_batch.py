from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from beyo_manager.domain.presence.enums import EntityType
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.commands.notifications.edit_pin_notification import edit_pin_notification
from beyo_manager.services.commands.notifications.pin_notification import pin_notification
from beyo_manager.services.commands.notifications.requests import parse_unpin_batch_request
from beyo_manager.services.commands.notifications.unpin_notification import unpin_notification
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.notifications.list_pins import list_pins


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def scalars(self) -> "_ScalarResult":
        return self

    def all(self):
        return self._values


class _TupleResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.pins: list[NotificationPin] = []
        self._in_transaction = False

    def in_transaction(self) -> bool:
        return self._in_transaction

    @asynccontextmanager
    async def begin(self):
        previous = self._in_transaction
        self._in_transaction = True
        try:
            yield
        finally:
            self._in_transaction = previous

    def add(self, obj) -> None:
        if isinstance(obj, User):
            self.users[obj.client_id] = obj
        elif isinstance(obj, NotificationPin):
            self.pins.append(obj)

    async def flush(self) -> None:
        return None

    async def execute(self, statement):
        sql = str(statement)
        params = statement.compile().params

        if sql.startswith("SELECT") and "JOIN users" in sql:
            pins = [pin for pin in self.pins if pin.user_id == params["user_id_1"]]
            if "entity_client_id_1" in params:
                allowed = set(params["entity_client_id_1"])
                pins = [pin for pin in pins if pin.entity_client_id in allowed]
            elif "major_client_entity_id_1" in params:
                allowed = set(params["major_client_entity_id_1"])
                pins = [pin for pin in pins if pin.major_client_entity_id in allowed]
            rows = [(pin, self.users[pin.user_id]) for pin in pins]
            return _TupleResult(rows)

        if sql.startswith("SELECT") and "FROM notification_pins" in sql:
            pins = [pin for pin in self.pins if pin.user_id == params["user_id_1"]]
            if "param_1" in params:
                allowed_pairs = set(tuple(pair) for pair in params["param_1"])
                pins = [
                    pin for pin in pins
                    if (pin.entity_type, pin.entity_client_id) in allowed_pairs
                ]
            elif "client_id_1" in params:
                allowed_ids = set(params["client_id_1"])
                pins = [pin for pin in pins if pin.client_id in allowed_ids]
            return _ScalarResult(pins)

        if sql.startswith("DELETE FROM notification_pins"):
            remaining: list[NotificationPin] = []
            for pin in self.pins:
                should_delete = pin.user_id == params.get("user_id_1")
                if "client_id_1" in params:
                    should_delete = should_delete and pin.client_id in set(params["client_id_1"])
                elif "major_entity_type_1" in params:
                    should_delete = (
                        should_delete
                        and pin.major_entity_type == params["major_entity_type_1"]
                        and pin.major_client_entity_id in set(params["major_client_entity_id_1"])
                    )
                if not should_delete:
                    remaining.append(pin)
            self.pins = remaining
            return _ScalarResult([])

        raise AssertionError(f"Unexpected SQL in fake session: {sql}")


def _ctx(session: _FakeSession, *, incoming_data: dict, user_id: str) -> ServiceContext:
    return ServiceContext(
        identity={"user_id": user_id, "username": "tester", "workspace_id": "ws_test"},
        incoming_data=incoming_data,
        session=session,  # type: ignore[arg-type]
    )


def _make_user(*, suffix: str) -> User:
    return User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
        created_at=datetime.now(timezone.utc),
    )


def _make_pin(
    *,
    user_id: str,
    client_id: str,
    entity_type: str = EntityType.TASK_STEP.value,
    entity_client_id: str = "tsp_default",
    conditions: list[dict] | None = None,
    fire_once: bool = False,
    major_entity_type: str | None = EntityType.TASK.value,
    major_client_entity_id: str | None = "tsk_default",
) -> NotificationPin:
    return NotificationPin(
        client_id=client_id,
        user_id=user_id,
        entity_type=entity_type,
        entity_client_id=entity_client_id,
        conditions=conditions,
        fire_once=fire_once,
        major_entity_type=major_entity_type,
        major_client_entity_id=major_client_entity_id,
        pinned_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_pin_notification_creates_new_pin() -> None:
    suffix = uuid4().hex[:8]
    session = _FakeSession()
    user = _make_user(suffix=suffix)
    session.add(user)

    result = await pin_notification(
        _ctx(
            session,
            user_id=user.client_id,
            incoming_data={
                "items": [
                    {
                        "client_id": f"npin_{suffix}",
                        "entity_type": EntityType.TASK_STEP.value,
                        "entity_client_id": "tsp_1",
                        "major_entity_type": EntityType.TASK.value,
                        "major_client_entity_id": "tsk_1",
                        "conditions": [{"type": "state", "op": "eq", "value": "completed"}],
                        "fire_once": True,
                    }
                ]
            },
        )
    )

    assert result == {"pins": [{"client_id": f"npin_{suffix}"}]}
    assert len(session.pins) == 1
    assert session.pins[0].entity_client_id == "tsp_1"
    assert session.pins[0].major_client_entity_id == "tsk_1"


@pytest.mark.asyncio
async def test_pin_notification_repin_overwrites_fields_and_preserves_existing_client_id() -> None:
    suffix = uuid4().hex[:8]
    session = _FakeSession()
    user = _make_user(suffix=suffix)
    session.add(user)
    session.add(
        _make_pin(
            user_id=user.client_id,
            client_id=f"npin_existing_{suffix}",
            entity_client_id="tsp_same",
            conditions=None,
            fire_once=False,
            major_client_entity_id="tsk_old",
        )
    )

    result = await pin_notification(
        _ctx(
            session,
            user_id=user.client_id,
            incoming_data={
                "items": [
                    {
                        "client_id": f"npin_new_{suffix}",
                        "entity_type": EntityType.TASK_STEP.value,
                        "entity_client_id": "tsp_same",
                        "major_entity_type": EntityType.TASK.value,
                        "major_client_entity_id": "tsk_new",
                        "conditions": [{"type": "state", "op": "in", "value": ["completed"]}],
                        "fire_once": True,
                    }
                ]
            },
        )
    )

    assert result == {"pins": [{"client_id": f"npin_existing_{suffix}"}]}
    assert len(session.pins) == 1
    assert session.pins[0].major_client_entity_id == "tsk_new"
    assert session.pins[0].fire_once is True


@pytest.mark.asyncio
async def test_pin_notification_duplicate_pair_raises_validation_error_before_write() -> None:
    suffix = uuid4().hex[:8]
    session = _FakeSession()
    user = _make_user(suffix=suffix)
    session.add(user)

    with pytest.raises(ValidationError):
        await pin_notification(
            _ctx(
                session,
                user_id=user.client_id,
                incoming_data={
                    "items": [
                        {
                            "client_id": f"npin_a_{suffix}",
                            "entity_type": EntityType.TASK_STEP.value,
                            "entity_client_id": "tsp_dup",
                        },
                        {
                            "client_id": f"npin_b_{suffix}",
                            "entity_type": EntityType.TASK_STEP.value,
                            "entity_client_id": "tsp_dup",
                        },
                    ]
                },
            )
        )

    assert session.pins == []


@pytest.mark.asyncio
async def test_unpin_notification_deletes_by_client_id() -> None:
    suffix = uuid4().hex[:8]
    session = _FakeSession()
    user = _make_user(suffix=suffix)
    session.add(user)
    session.add(_make_pin(user_id=user.client_id, client_id=f"npin_{suffix}"))

    await unpin_notification(
        _ctx(
            session,
            user_id=user.client_id,
            incoming_data={"items": [{"client_id": f"npin_{suffix}"}]},
        )
    )

    assert session.pins == []


@pytest.mark.asyncio
async def test_unpin_notification_deletes_by_major_entity() -> None:
    suffix = uuid4().hex[:8]
    session = _FakeSession()
    user = _make_user(suffix=suffix)
    session.add(user)
    session.add(_make_pin(user_id=user.client_id, client_id=f"npin_1_{suffix}", major_client_entity_id="tsk_target"))
    session.add(_make_pin(user_id=user.client_id, client_id=f"npin_2_{suffix}", entity_client_id="tsp_other", major_client_entity_id="tsk_target"))

    await unpin_notification(
        _ctx(
            session,
            user_id=user.client_id,
            incoming_data={
                "items": [{"major_entity_type": EntityType.TASK.value, "major_client_entity_id": "tsk_target"}]
            },
        )
    )

    assert session.pins == []


@pytest.mark.asyncio
async def test_unpin_notification_empty_list_is_no_op() -> None:
    suffix = uuid4().hex[:8]
    session = _FakeSession()
    user = _make_user(suffix=suffix)
    session.add(user)
    session.add(_make_pin(user_id=user.client_id, client_id=f"npin_{suffix}"))

    result = await unpin_notification(_ctx(session, user_id=user.client_id, incoming_data={"items": []}))

    assert result == {}
    assert len(session.pins) == 1


@pytest.mark.asyncio
async def test_edit_pin_notification_updates_conditions_and_fire_once() -> None:
    suffix = uuid4().hex[:8]
    session = _FakeSession()
    user = _make_user(suffix=suffix)
    session.add(user)
    session.add(_make_pin(user_id=user.client_id, client_id=f"npin_{suffix}", conditions=None, fire_once=False))

    result = await edit_pin_notification(
        _ctx(
            session,
            user_id=user.client_id,
            incoming_data={
                "items": [
                    {
                        "client_id": f"npin_{suffix}",
                        "conditions": [{"type": "state", "op": "eq", "value": "completed"}],
                        "fire_once": True,
                    }
                ]
            },
        )
    )

    assert result == {}
    assert session.pins[0].conditions == [{"type": "state", "op": "eq", "value": "completed"}]
    assert session.pins[0].fire_once is True


@pytest.mark.asyncio
async def test_edit_pin_notification_missing_pin_is_skipped() -> None:
    suffix = uuid4().hex[:8]
    session = _FakeSession()
    user = _make_user(suffix=suffix)
    session.add(user)

    result = await edit_pin_notification(
        _ctx(
            session,
            user_id=user.client_id,
            incoming_data={
                "items": [
                    {
                        "client_id": f"npin_missing_{suffix}",
                        "conditions": [{"type": "state", "op": "eq", "value": "completed"}],
                        "fire_once": True,
                    }
                ]
            },
        )
    )

    assert result == {}


@pytest.mark.asyncio
async def test_edit_pin_notification_invalid_condition_raises_validation_error() -> None:
    suffix = uuid4().hex[:8]
    session = _FakeSession()
    user = _make_user(suffix=suffix)
    session.add(user)
    session.add(_make_pin(user_id=user.client_id, client_id=f"npin_{suffix}", entity_type=EntityType.TASK_STEP.value))

    with pytest.raises(ValidationError):
        await edit_pin_notification(
            _ctx(
                session,
                user_id=user.client_id,
                incoming_data={
                    "items": [
                        {
                            "client_id": f"npin_{suffix}",
                            "conditions": [{"type": "state", "op": "in", "value": ["not_a_real_state"]}],
                            "fire_once": False,
                        }
                    ]
                },
            )
        )


@pytest.mark.asyncio
async def test_list_pins_filters_by_entity_client_ids() -> None:
    suffix = uuid4().hex[:8]
    session = _FakeSession()
    user = _make_user(suffix=suffix)
    session.add(user)
    session.add(_make_pin(user_id=user.client_id, client_id=f"npin_1_{suffix}", entity_client_id="tsp_a"))
    session.add(_make_pin(user_id=user.client_id, client_id=f"npin_2_{suffix}", entity_client_id="tsp_b"))

    result = await list_pins(
        _ctx(session, user_id=user.client_id, incoming_data={"entity_client_ids": ["tsp_a"], "major_client_entity_ids": None})
    )

    assert len(result["pins"]) == 1
    assert result["pins"][0]["entity_client_id"] == "tsp_a"


@pytest.mark.asyncio
async def test_list_pins_filters_by_major_client_entity_ids() -> None:
    suffix = uuid4().hex[:8]
    session = _FakeSession()
    user = _make_user(suffix=suffix)
    session.add(user)
    session.add(_make_pin(user_id=user.client_id, client_id=f"npin_1_{suffix}", major_client_entity_id="tsk_x"))
    session.add(_make_pin(user_id=user.client_id, client_id=f"npin_2_{suffix}", entity_client_id="tsp_other", major_client_entity_id="tsk_x"))

    result = await list_pins(
        _ctx(session, user_id=user.client_id, incoming_data={"entity_client_ids": None, "major_client_entity_ids": ["tsk_x"]})
    )

    assert len(result["pins"]) == 2


@pytest.mark.asyncio
async def test_list_pins_returns_empty_when_both_filters_none() -> None:
    suffix = uuid4().hex[:8]
    session = _FakeSession()
    user = _make_user(suffix=suffix)
    session.add(user)

    result = await list_pins(
        _ctx(session, user_id=user.client_id, incoming_data={"entity_client_ids": None, "major_client_entity_ids": None})
    )

    assert result == {"pins": []}


def test_unpin_item_partial_major_pair_message() -> None:
    with pytest.raises(ValidationError, match="major_entity_type and major_client_entity_id must both be provided together."):
        parse_unpin_batch_request([{"major_entity_type": "task"}])


def test_unpin_item_both_modes_message() -> None:
    with pytest.raises(ValidationError, match="Provide either client_id or major entity targeting, not both."):
        parse_unpin_batch_request([{"client_id": "npin_test", "major_entity_type": "task", "major_client_entity_id": "tsk_1"}])


def test_unpin_item_neither_mode_message() -> None:
    with pytest.raises(ValidationError, match="Provide either client_id or both major_entity_type \\+ major_client_entity_id."):
        parse_unpin_batch_request([{}])
