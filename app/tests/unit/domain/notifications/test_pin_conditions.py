import pytest

from beyo_manager.domain.notifications.pin_conditions import (
    pin_conditions_match,
    validate_pin_conditions,
)
from beyo_manager.domain.notifications.pin_cleanup import cleanup_task_pins
from beyo_manager.domain.notifications.pinned_subscribers import resolve_pinned_subscribers
from beyo_manager.domain.presence.enums import EntityType
from beyo_manager.errors.validation import ValidationError


def test_pin_conditions_match_null_and_empty() -> None:
    assert pin_conditions_match(None, {"state": "completed"}) is True
    assert pin_conditions_match([], {"state": "completed"}) is True


def test_state_condition_match_truth_table() -> None:
    assert pin_conditions_match(
        [{"type": "state", "op": "in", "value": ["completed", "paused"]}],
        {"state": "completed"},
    )
    assert pin_conditions_match(
        [{"type": "state", "op": "eq", "value": "paused"}],
        {"state": "paused"},
    )
    assert pin_conditions_match(
        [{"type": "state", "op": "not_in", "value": ["failed", "cancelled"]}],
        {"state": "working"},
    )
    assert not pin_conditions_match(
        [{"type": "state", "op": "in", "value": ["completed"]}],
        {"state": "working"},
    )
    assert not pin_conditions_match(
        [{"type": "state", "op": "eq", "value": "completed"}],
        {},
    )


def test_state_conditions_are_and_semantics() -> None:
    conditions = [
        {"type": "state", "op": "in", "value": ["completed", "paused"]},
        {"type": "state", "op": "not_in", "value": ["paused"]},
    ]

    assert pin_conditions_match(conditions, {"state": "completed"})
    assert not pin_conditions_match(conditions, {"state": "paused"})


def test_state_condition_match_returns_false_for_malformed_or_unknown_op() -> None:
    assert not pin_conditions_match(
        [{"type": "state", "op": "eq", "value": ["completed"]}],
        {"state": "completed"},
    )
    assert not pin_conditions_match(
        [{"type": "state", "op": "contains", "value": "completed"}],
        {"state": "completed"},
    )


def test_validate_pin_conditions_rejects_unknown_type_and_op() -> None:
    with pytest.raises(ValidationError):
        validate_pin_conditions(EntityType.TASK_STEP.value, [{"type": "size", "op": "eq", "value": "x"}])

    with pytest.raises(ValidationError):
        validate_pin_conditions(
            EntityType.TASK_STEP.value,
            [{"type": "state", "op": "contains", "value": ["completed"]}],
        )


def test_validate_pin_conditions_rejects_cross_entity_state() -> None:
    with pytest.raises(ValidationError):
        validate_pin_conditions(
            EntityType.ITEM_UPHOLSTERY.value,
            [{"type": "state", "op": "in", "value": ["paused"]}],
        )


def test_time_condition_validates_shape_but_does_not_evaluate() -> None:
    condition = {"type": "time", "op": "between", "value": ["2026-06-19T10:00:00Z", "2026-06-19T11:00:00Z"]}

    validate_pin_conditions(EntityType.TASK_STEP.value, [condition])
    with pytest.raises(NotImplementedError):
        pin_conditions_match([condition], {"time": "2026-06-19T10:30:00Z"})


def test_unknown_condition_type_logs_warning_and_returns_false(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING"):
        matched = pin_conditions_match(
            [{"type": "mystery", "op": "eq", "value": "x"}],
            {"state": "completed"},
        )

    assert matched is False
    assert "Unknown pin condition type" in caplog.text


class _Rows:
    def __init__(self, rows: list[tuple[str, str, list[dict] | None, bool]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[str, str, list[dict] | None, bool]]:
        return self._rows


class _Session:
    def __init__(self, rows: list[tuple[str, str, list[dict] | None, bool]]) -> None:
        self.rows = rows
        self.statements: list[object] = []

    async def execute(self, statement: object) -> _Rows:
        self.statements.append(statement)
        return _Rows(self.rows)


@pytest.mark.asyncio
async def test_resolve_pinned_subscribers_filters_and_deletes_fire_once() -> None:
    session = _Session(
        [
            (
                "pin_matching_once",
                "user_matching_once",
                [{"type": "state", "op": "eq", "value": "completed"}],
                True,
            ),
            (
                "pin_matching_permanent",
                "user_matching_permanent",
                None,
                False,
            ),
            (
                "pin_miss",
                "user_miss",
                [{"type": "state", "op": "eq", "value": "paused"}],
                True,
            ),
        ]
    )

    result = await resolve_pinned_subscribers(
        session,
        EntityType.TASK_STEP.value,
        "step_1",
        {"state": "completed"},
    )

    assert result == {"user_matching_once", "user_matching_permanent"}
    assert len(session.statements) == 2


class _ScalarRows:
    def __init__(self, values: list[str]) -> None:
        self._values = values

    def scalars(self) -> "_ScalarRows":
        return self

    def all(self) -> list[str]:
        return self._values


class _CleanupSession:
    def __init__(self) -> None:
        self.statements: list[object] = []

    async def execute(self, statement: object) -> _ScalarRows:
        self.statements.append(statement)
        return _ScalarRows([])


@pytest.mark.asyncio
async def test_cleanup_task_pins_deletes_by_major_entity() -> None:
    session = _CleanupSession()

    await cleanup_task_pins(session, "task_1")

    assert len(session.statements) == 1
