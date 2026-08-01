"""A step payload must never render an unexplained pause (review round 1, R2).

Phase 1's R9 test asserts `pause_reason: null` for a transition-typed row and therefore
passes identically before and after this fix — it could not have caught the defect. These
tests assert the opposite: that a **name renders**. They fail against the working tree as
it stood at the end of round 1, where both serializers emitted `null` for a system
transition and the frontend's `pause_reason?.name` went empty.

The shape asserted here is the published `PauseReason` object (`packages/tasks/src/types.ts`
→ `LatestStateRecordSchema.pause_reason` is `PauseReasonSchema.nullable()`), whose fields
are all required and whose `slug` is a non-nullable string. A partial object would fail
client-side validation for the whole step payload, which is worse than a null — so
completeness is asserted field by field, not just `name`.
"""

from datetime import datetime, timezone

import pytest

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.serializers import (
    serialize_step_latest_state_record,
    serialize_step_state_record_light,
)
from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord


pytestmark = pytest.mark.unit

BASE = datetime(2026, 7, 31, 9, tzinfo=timezone.utc)

# Every key the published `PauseReason` schema requires.
_REQUIRED_FIELDS = {
    "client_id",
    "name",
    "image_url",
    "pause_type",
    "description",
    "requires_description",
    "is_system_managed",
    "slug",
    "created_at",
    "created_by_id",
    "updated_at",
    "updated_by_id",
}


def _record(
    *,
    state: TaskStepStateEnum,
    transition_reason: str | None = None,
    pause_reason: PauseReason | None = None,
) -> StepStateRecord:
    record = StepStateRecord(
        client_id="ssr_test",
        workspace_id="ws_test",
        step_id="tsp_test",
        state=state,
        pause_reason_id=pause_reason.client_id if pause_reason is not None else None,
        transition_reason=transition_reason,
        entered_at=BASE,
        exited_at=None,
        created_at=BASE,
        created_by_id="usr_test",
    )
    record.pause_reason = pause_reason
    return record


def _catalog_reason() -> PauseReason:
    return PauseReason(
        client_id="par_lunch",
        workspace_id="ws_test",
        name="Lunch break",
        image_url="https://example.test/lunch.webp",
        pause_type=PauseTypeEnum.PERSONAL,
        description=None,
        requires_description=False,
        is_system_managed=False,
        slug="pause_lunch_break",
        created_at=BASE,
        created_by_id=None,
    )


# --- the two rows this phase started writing -------------------------------------------


@pytest.mark.parametrize(
    "serializer",
    [serialize_step_latest_state_record, serialize_step_state_record_light],
)
def test_ended_shift_record_renders_a_name_and_icon(serializer) -> None:
    data = serializer(
        _record(
            state=TaskStepStateEnum.PAUSED,
            transition_reason=TransitionReasonEnum.SHIFT_ENDED.value,
        )
    )

    reason = data["pause_reason"]
    assert reason is not None, "a clocked-out step would render an unexplained pause"
    assert reason["name"] == "Ended shift"
    assert reason["image_url"].endswith("/pause_reasons/ended_shift.webp")
    assert reason["slug"] == "pause_ended_shift"


@pytest.mark.parametrize(
    "serializer",
    [serialize_step_latest_state_record, serialize_step_state_record_light],
)
def test_task_switch_auto_pause_renders_a_name_and_icon(serializer) -> None:
    data = serializer(
        _record(
            state=TaskStepStateEnum.PAUSED,
            transition_reason=TransitionReasonEnum.OTHER_TASK_PRIORITY.value,
        )
    )

    reason = data["pause_reason"]
    assert reason is not None, "an auto-paused step would render an unexplained pause"
    assert reason["name"] == "Other task priority"
    assert reason["image_url"].endswith("/pause_reasons/other_task_priority.webp")
    assert reason["slug"] == "pause_other_task_priority"


# --- shape completeness: a partial object fails client validation entirely ---------------


def test_synthesized_object_carries_every_published_field() -> None:
    data = serialize_step_latest_state_record(
        _record(
            state=TaskStepStateEnum.PAUSED,
            transition_reason=TransitionReasonEnum.OTHER_TASK_PRIORITY.value,
        )
    )

    reason = data["pause_reason"]
    assert set(reason) == _REQUIRED_FIELDS
    # `slug` and `created_at` are non-nullable in the published schema.
    assert isinstance(reason["slug"], str)
    assert isinstance(reason["created_at"], str)
    assert isinstance(reason["requires_description"], bool)
    assert isinstance(reason["is_system_managed"], bool)
    assert reason["pause_type"] in {PauseTypeEnum.PERSONAL.value, PauseTypeEnum.BLOCKER.value}


def test_synthesized_object_matches_the_catalog_objects_key_set() -> None:
    """The two channels must be indistinguishable in shape, or one of them fails to parse."""
    catalog = serialize_step_latest_state_record(
        _record(state=TaskStepStateEnum.PAUSED, pause_reason=_catalog_reason())
    )["pause_reason"]
    synthesized = serialize_step_latest_state_record(
        _record(
            state=TaskStepStateEnum.PAUSED,
            transition_reason=TransitionReasonEnum.SHIFT_ENDED.value,
        )
    )["pause_reason"]

    assert set(catalog) == set(synthesized)


# --- the unchanged half -----------------------------------------------------------------


def test_worker_chosen_catalog_pause_is_untouched() -> None:
    reason = _catalog_reason()
    data = serialize_step_latest_state_record(
        _record(state=TaskStepStateEnum.PAUSED, pause_reason=reason)
    )["pause_reason"]

    assert data["client_id"] == "par_lunch"
    assert data["name"] == "Lunch break"
    assert data["slug"] == "pause_lunch_break"
    assert data["is_system_managed"] is False


def test_record_explaining_itself_neither_way_still_serializes_null() -> None:
    """A working record has no pause reason at all — it must not gain a synthetic one."""
    data = serialize_step_latest_state_record(_record(state=TaskStepStateEnum.WORKING))

    assert data["pause_reason"] is None
