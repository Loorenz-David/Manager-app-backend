from types import SimpleNamespace

import pytest

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.services.commands.task_steps.mark_step_time_inaccurate import _apply_inaccurate_time_flag
from beyo_manager.services.commands.task_steps.transition_step_state import (
    _resolve_transition_credit_user_id,
    _should_mark_latest_record_inaccurate,
)


@pytest.mark.unit
def test_transition_credit_defaults_to_actor():
    ctx = SimpleNamespace(user_id="usr_actor")
    request = SimpleNamespace(credited_user_id=None)

    assert _resolve_transition_credit_user_id(ctx, request) == "usr_actor"


@pytest.mark.unit
def test_transition_credit_uses_override_user():
    ctx = SimpleNamespace(user_id="usr_actor")
    request = SimpleNamespace(credited_user_id="usr_credit")

    assert _resolve_transition_credit_user_id(ctx, request) == "usr_credit"


@pytest.mark.unit
def test_should_mark_latest_record_inaccurate_for_completed_transition():
    request = SimpleNamespace(
        mark_closing_record_inaccurate=True,
        new_state=TaskStepStateEnum.COMPLETED,
    )

    assert _should_mark_latest_record_inaccurate(request, TaskStepStateEnum.WORKING) is True


@pytest.mark.unit
def test_should_not_mark_latest_record_inaccurate_for_non_completed_transition():
    request = SimpleNamespace(
        mark_closing_record_inaccurate=True,
        new_state=TaskStepStateEnum.PAUSED,
    )

    assert _should_mark_latest_record_inaccurate(request, TaskStepStateEnum.WORKING) is False


@pytest.mark.unit
def test_apply_inaccurate_time_flag_marks_step_and_record_flags():
    record = SimpleNamespace(
        recorded_time_marked_wrong=False,
        taken_from_average=False,
        updated_at=None,
    )
    step = SimpleNamespace(
        recorded_time_marked_wrong=False,
        taken_from_average=False,
        updated_at=None,
    )
    now = object()

    _apply_inaccurate_time_flag(record, step, now)

    assert record.recorded_time_marked_wrong is True
    assert record.taken_from_average is True
    assert step.recorded_time_marked_wrong is True
    assert step.taken_from_average is True
    assert record.updated_at is now
    assert step.updated_at is now
