"""Phase 1 step D — read tolerance for `transition_reason`, domain layer.

Nothing writes `transition_reason` in this phase, so every test here seeds the value
directly on an unsaved model instance (criterion 14). Without that the new branches
would never execute and would pass vacuously.
"""

from datetime import datetime, timezone

import pytest

from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.domain.transitions.labels import (
    is_transition_reason,
    resolve_transition_reason_label,
)
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.domain.users.serializers import (
    pause_reason_reference_is_unresolved,
    serialize_current_worker_shift_state,
)
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.services.queries.worker_stats.list_workers_linear_timeline import (
    build_recorded_shift_timeline,
)


pytestmark = pytest.mark.unit

BASE = datetime(2026, 7, 31, 9, tzinfo=timezone.utc)


def _shift_record(
    *,
    state: UserShiftStateEnum = UserShiftStateEnum.IN_PAUSE,
    reason: str | None = None,
    transition_reason: str | None = None,
    entered_at: datetime = BASE,
    exited_at: datetime | None = None,
) -> UserShiftStateRecord:
    return UserShiftStateRecord(
        workspace_id="ws_test",
        user_id="usr_test",
        state=state,
        entered_at=entered_at,
        exited_at=exited_at,
        reason=reason,
        transition_reason=transition_reason,
    )


def _catalog_reason(client_id: str = "par_catalog") -> PauseReason:
    return PauseReason(
        client_id=client_id,
        workspace_id="ws_test",
        name="Lunch break",
        image_url="https://example.test/lunch.webp",
    )


# --- the label map itself (criterion 12) ---------------------------------------------


def test_label_map_reproduces_the_catalog_strings_it_replaces() -> None:
    """Criterion 5 / master-plan success criterion 5: the human-visible string must not
    move. Measured on the `.env` database 2026-07-31:
    pause_ended_shift -> "Ended shift", pause_other_task_priority -> "Other task priority".
    """
    assert resolve_transition_reason_label("shift_ended")["name"] == "Ended shift"
    assert (
        resolve_transition_reason_label("other_task_priority")["name"]
        == "Other task priority"
    )


def test_every_enum_member_resolves() -> None:
    for member in TransitionReasonEnum:
        assert resolve_transition_reason_label(member.value) is not None, member


@pytest.mark.parametrize("value", [None, "par_01ABC", "pause_ended_shift", "unspecified", ""])
def test_non_transition_values_do_not_resolve(value: str | None) -> None:
    """Catalog ids, legacy slug strings and the published `unspecified` key must fall
    through to their existing resolution untouched."""
    assert resolve_transition_reason_label(value) is None
    assert is_transition_reason(value) is False


def test_returned_label_is_a_copy_callers_cannot_corrupt_the_map() -> None:
    first = resolve_transition_reason_label("shift_ended")
    first["name"] = "mutated"
    assert resolve_transition_reason_label("shift_ended")["name"] == "Ended shift"


# --- serialize_current_worker_shift_state (audit R6) ----------------------------------


def test_transition_reason_row_resolves_to_a_pause_reason_label() -> None:
    data = serialize_current_worker_shift_state(
        user_id="usr_test",
        current=_shift_record(transition_reason="other_task_priority"),
        pause_reason=None,
    )
    assert data["pause_reason"] == {
        "id": "other_task_priority",
        "name": "Other task priority",
        # The icon the replaced catalog row carried, restored from the code-owned map.
        # `None` here would blank the pause icon the kiosk renders.
        "image_url": (
            "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com"
            "/images/ws_workspace_test/pause_reasons/other_task_priority.webp"
        ),
    }
    # Criterion 17: the row must not gain a field. `reason_text` is absent, not null.
    assert "reason_text" not in data


def test_catalog_reference_wins_over_transition_reason() -> None:
    """Criterion 13 — precedence is asserted, not incidental. A catalog row means a
    human chose it, which outranks a system-typed transition."""
    data = serialize_current_worker_shift_state(
        user_id="usr_test",
        current=_shift_record(reason="par_catalog", transition_reason="shift_ended"),
        pause_reason=_catalog_reason(),
    )
    assert data["pause_reason"]["id"] == "par_catalog"
    assert data["pause_reason"]["name"] == "Lunch break"


def test_transition_reason_wins_over_free_text_reason() -> None:
    """Criterion 13, lower rung: typed transition outranks legacy free text, so no
    `reason_text` is emitted alongside a resolved transition label."""
    data = serialize_current_worker_shift_state(
        user_id="usr_test",
        current=_shift_record(reason="pause_meeting", transition_reason="shift_ended"),
        pause_reason=None,
    )
    assert data["pause_reason"]["id"] == "shift_ended"
    assert "reason_text" not in data


def test_transition_reason_ignored_when_not_paused() -> None:
    data = serialize_current_worker_shift_state(
        user_id="usr_test",
        current=_shift_record(
            state=UserShiftStateEnum.WORKING, transition_reason="shift_ended"
        ),
        pause_reason=None,
    )
    assert data["pause_reason"] is None


# --- zero behaviour change controls (criterion 17) ------------------------------------


def test_legacy_free_text_row_is_byte_identical_to_today() -> None:
    data = serialize_current_worker_shift_state(
        user_id="usr_test",
        current=_shift_record(reason="pause_meeting"),
        pause_reason=None,
    )
    assert data["reason_text"] == "pause_meeting"
    assert data["pause_reason"] is None


def test_dangling_catalog_id_still_reports_unresolved() -> None:
    record = _shift_record(reason="par_missing")
    assert pause_reason_reference_is_unresolved(record, None) is True
    data = serialize_current_worker_shift_state(
        user_id="usr_test", current=record, pause_reason=None
    )
    assert data["reason_text"] is None


def test_transition_row_is_not_reported_unresolved() -> None:
    record = _shift_record(reason=None, transition_reason="shift_ended")
    assert pause_reason_reference_is_unresolved(record, None) is False


def test_transition_row_outranks_a_dangling_catalog_id() -> None:
    """Criterion 13 for the unresolved probe: a row carrying both must not log a
    spurious 'unresolved pause reason' warning when it resolves through the map."""
    record = _shift_record(reason="par_missing", transition_reason="shift_ended")
    assert pause_reason_reference_is_unresolved(record, None) is False


# --- build_recorded_shift_timeline bucketing (audit R12) ------------------------------


def test_pause_bucket_key_falls_back_to_transition_reason() -> None:
    timeline = build_recorded_shift_timeline(
        [
            _shift_record(
                transition_reason="other_task_priority",
                entered_at=BASE,
                exited_at=BASE.replace(hour=10),
            )
        ],
        BASE,
        BASE.replace(hour=17),
        BASE.replace(hour=17),
    )
    assert timeline.pause_by_reason == {"other_task_priority": 3600}


def test_catalog_reason_still_wins_the_bucket_key() -> None:
    timeline = build_recorded_shift_timeline(
        [
            _shift_record(
                reason="par_catalog",
                transition_reason="other_task_priority",
                entered_at=BASE,
                exited_at=BASE.replace(hour=10),
            )
        ],
        BASE,
        BASE.replace(hour=17),
        BASE.replace(hour=17),
    )
    assert timeline.pause_by_reason == {"par_catalog": 3600}


def test_reasonless_pause_still_buckets_as_unspecified() -> None:
    """The literal `"unspecified"` key is part of the published contract (criterion 15)."""
    timeline = build_recorded_shift_timeline(
        [_shift_record(entered_at=BASE, exited_at=BASE.replace(hour=10))],
        BASE,
        BASE.replace(hour=17),
        BASE.replace(hour=17),
    )
    assert timeline.pause_by_reason == {"unspecified": 3600}
