"""`reason_text` three-way conformance, asserted against the published contract.

Handoff `HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` §5.3 states:

    `reason_text` is three-way: absent / string / `null` (see §4).

and §4 defines each arm:

    **absent** (normal case, the reason resolved into `pause_reason`); **a string** (very
    old pause carrying free text instead of a catalog reason -> `pause_reason: null` +
    `reason_text: "<raw>"`, render the text); **`null`** (the pause references a catalog
    reason that cannot be resolved -- render a neutral "paused, reason unavailable"; the
    backend deliberately does not expose the raw identifier).

Four cases, one per kind of row this system can now produce, each asserting which arm it
lands on. `pause_reason` is asserted alongside because §4 ties the two together: the
"absent" arm is defined by the reason having resolved *into* `pause_reason`.
"""

from datetime import datetime, timezone

import pytest

from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.domain.users.serializers import serialize_current_worker_shift_state
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.users.user_declared_state_record import (
    UserDeclaredStateRecord,
)
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord


pytestmark = pytest.mark.unit

BASE = datetime(2026, 7, 31, 9, tzinfo=timezone.utc)


def _paused_row(*, reason: str | None, transition_reason: str | None) -> UserShiftStateRecord:
    return UserShiftStateRecord(
        workspace_id="ws_test",
        user_id="usr_test",
        state=UserShiftStateEnum.IN_PAUSE,
        entered_at=BASE,
        exited_at=None,
        reason=reason,
        transition_reason=transition_reason,
    )


def _catalog_reason(client_id: str = "par_lunch") -> PauseReason:
    return PauseReason(
        client_id=client_id,
        workspace_id="ws_test",
        name="Lunch break",
        image_url="https://example.test/lunch.webp",
    )


# Case 1 — a system transition (what this phase started writing).
def test_system_transition_omits_reason_text_and_resolves_into_pause_reason() -> None:
    data = serialize_current_worker_shift_state(
        user_id="usr_test",
        current=_paused_row(
            reason=None,
            transition_reason=TransitionReasonEnum.OTHER_TASK_PRIORITY.value,
        ),
        pause_reason=None,
    )

    # §4 "absent (normal case, the reason resolved into `pause_reason`)".
    assert "reason_text" not in data
    assert data["pause_reason"] == {
        "id": TransitionReasonEnum.OTHER_TASK_PRIORITY.value,
        "name": "Other task priority",
        "image_url": (
            "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com"
            "/images/ws_workspace_test/pause_reasons/other_task_priority.webp"
        ),
    }
    assert data["declared_state"] is None


# Case 2 — a worker-chosen catalog pause (unchanged by this phase).
def test_worker_chosen_catalog_pause_omits_reason_text() -> None:
    reason = _catalog_reason()
    data = serialize_current_worker_shift_state(
        user_id="usr_test",
        current=_paused_row(reason=reason.client_id, transition_reason=None),
        pause_reason=reason,
    )

    assert "reason_text" not in data
    assert data["pause_reason"] == {
        "id": "par_lunch",
        "name": "Lunch break",
        "image_url": "https://example.test/lunch.webp",
    }


# Case 3 — a declared state: the one row carrying BOTH representations.
def test_declared_state_omits_reason_text_and_keeps_its_catalog_reference() -> None:
    reason = _catalog_reason("par_cleaning")
    reason.name = "Cleaning"
    declaration = UserDeclaredStateRecord(
        client_id="uds_test",
        workspace_id="ws_test",
        user_id="usr_test",
        pause_reason_id=reason.client_id,
        description=None,
        entered_at=BASE,
        created_by_id="usr_test",
    )
    data = serialize_current_worker_shift_state(
        user_id="usr_test",
        current=_paused_row(
            reason=reason.client_id,
            transition_reason=TransitionReasonEnum.WORKER_DECLARED_STATE.value,
        ),
        pause_reason=reason,
        declared_record=declaration,
        declared_pause_reason=reason,
    )

    assert "reason_text" not in data
    # §4: the catalog reference still describes the pause, and `declared_state` is
    # non-null "only when the pause is a worker declaration".
    assert data["pause_reason"]["id"] == "par_cleaning"
    assert data["declared_state"]["id"] == "uds_test"
    assert data["declared_state"]["pause_reason"]["name"] == "Cleaning"


# Case 4 — a legacy free-text row (pre-cutover history).
def test_legacy_free_text_row_returns_reason_text_as_a_string() -> None:
    data = serialize_current_worker_shift_state(
        user_id="usr_test",
        current=_paused_row(reason="Late lunch", transition_reason=None),
        pause_reason=None,
    )

    # §4 "a string ... -> `pause_reason: null` + `reason_text: \"<raw>\"`".
    assert data["pause_reason"] is None
    assert data["reason_text"] == "Late lunch"


# The third arm of the three-way, kept here so all of §5.3 is covered in one place.
def test_unresolvable_catalog_id_returns_reason_text_null_without_leaking_the_id() -> None:
    data = serialize_current_worker_shift_state(
        user_id="usr_test",
        current=_paused_row(reason="par_deleted", transition_reason=None),
        pause_reason=None,
    )

    # §4 "`null` ... the backend deliberately does not expose the raw identifier".
    assert data["pause_reason"] is None
    assert data["reason_text"] is None
    assert "par_deleted" not in str(data)


# Criterion 15 — every legacy shape `UserShiftStateRecord.reason` actually holds.
# The distinct set measured on the dev database is: `par_…` ids, legacy slug strings, and
# the literal `"unspecified"`. Rows written before the cutover are not backfilled by this
# phase, so each must still render exactly as it did.
@pytest.mark.parametrize(
    "legacy_reason",
    [
        "pause_lunch_break",
        "pause_case_created",
        "waiting_for_upholstery",
        "unspecified",
    ],
)
def test_legacy_slug_shaped_reasons_still_render_as_text(legacy_reason: str) -> None:
    data = serialize_current_worker_shift_state(
        user_id="usr_test",
        current=_paused_row(reason=legacy_reason, transition_reason=None),
        pause_reason=None,
    )

    assert data["pause_reason"] is None
    assert data["reason_text"] == legacy_reason


def test_legacy_catalog_id_that_still_resolves_renders_the_catalog_object() -> None:
    reason = _catalog_reason("par_legacy")
    data = serialize_current_worker_shift_state(
        user_id="usr_test",
        current=_paused_row(reason=reason.client_id, transition_reason=None),
        pause_reason=reason,
    )

    assert "reason_text" not in data
    assert data["pause_reason"]["id"] == "par_legacy"
