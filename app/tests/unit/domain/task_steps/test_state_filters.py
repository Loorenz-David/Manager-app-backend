import pytest

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.task_steps.state_filters import (
    parse_step_readiness_filter,
    parse_step_state_filter,
)
from beyo_manager.errors.validation import ValidationError


def test_current_members_parse_to_enum_members():
    assert parse_step_state_filter("pending,working,paused") == [
        TaskStepStateEnum.PENDING,
        TaskStepStateEnum.WORKING,
        TaskStepStateEnum.PAUSED,
    ]


def test_blank_and_absent_filters_are_empty():
    assert parse_step_state_filter(None) == []
    assert parse_step_state_filter("") == []
    assert parse_step_state_filter(" , ,") == []
    assert parse_step_readiness_filter(None) == []


def test_whitespace_around_values_is_tolerated():
    assert parse_step_state_filter(" working , paused ") == [
        TaskStepStateEnum.WORKING,
        TaskStepStateEnum.PAUSED,
    ]


def test_retired_ended_shift_resolves_to_paused():
    """The value the workers app still sends must not reach Postgres.

    `2645b4327b17` removed `ended_shift` from `task_step_state_enum`, and `TaskStep.state` is a
    native enum — an unmapped value is bound as-is and raises
    `InvalidTextRepresentationError` in the driver, i.e. a 500 on a request the caller had every
    reason to think was valid. It resolves to `PAUSED` because that is the state those steps
    were reclassified into, so the filter still selects the population the caller asked for.
    """
    assert parse_step_state_filter("ended_shift") == [TaskStepStateEnum.PAUSED]


def test_the_workers_app_default_filter_set_survives_the_alias_collision():
    """`DEFAULT_STATE_FILTERS` sends `paused` *and* `ended_shift`; both map onto `PAUSED`.

    Without the dedupe the `IN` clause would carry `paused` twice — harmless in SQL, but the
    parsed list is also what a caller-facing count iterates over, where a duplicate key is not.
    """
    assert parse_step_state_filter("pending,working,paused,ended_shift") == [
        TaskStepStateEnum.PENDING,
        TaskStepStateEnum.WORKING,
        TaskStepStateEnum.PAUSED,
    ]


def test_unknown_value_is_refused_rather_than_dropped():
    """Dropping it would silently widen the result set to every state.

    A request filtered to one bad value alone would come back unfiltered — the caller sees a list
    they did not ask for and no indication anything went wrong. 422 says which value was rejected.
    """
    with pytest.raises(ValidationError) as exc:
        parse_step_state_filter("working,not_a_state")
    assert "not_a_state" in str(exc.value)
    assert "working" in str(exc.value)  # the allowed set is named in the message


def test_readiness_filter_parses_and_refuses_the_same_way():
    assert parse_step_readiness_filter("ready,blocked") == [
        TaskStepReadinessStatusEnum.READY,
        TaskStepReadinessStatusEnum.BLOCKED,
    ]
    with pytest.raises(ValidationError):
        parse_step_readiness_filter("ready,almost_ready")


def test_ended_shift_is_not_a_readiness_alias():
    """The alias belongs to the state filter alone — nothing retired a readiness value."""
    with pytest.raises(ValidationError):
        parse_step_readiness_filter("ended_shift")
