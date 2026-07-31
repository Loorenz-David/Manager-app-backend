"""The prefix branch's suppression arm is dead for every stored row shape (criterion 11).

`pause_reason_reference_is_unresolved` contains the one remaining prefix inspection in
this domain: it separates a `par_…` id that failed to resolve (published contract
`HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` §4: render `reason_text: null`,
never the raw identifier) from a legacy string (render it). The branch itself cannot be
removed — that three-way is a published, operator-owned contract, and its `null` arm is
asserted by `test_reason_text_contract_conformance.py`.

What the phase-3 backfill changes is its **input population**. The migration
(`97b60e06d42a`) removes the last system catalog references, after which every value
`user_shift_state_records.reason` still holds is one of:

* `NULL` — with or without a `transition_reason`,
* a `par_…` id that resolves to a catalog row in its own workspace (worker-chosen;
  catalog rows are never hard-deleted, so the reference cannot dangle),
* a legacy slug string or the literal `"unspecified"`.

That complete set is measured, not assumed: the migration's zero-remaining-references
assertion plus the rehearsal queries recorded in the phase 3 plan's Review log establish
that no stored row carries an unresolvable `par_…` id. This module proves the other
half: for each shape in that set, the suppression arm is not taken — so no stored row
reaches the prefix branch's `True` case, and the branch is dead code with respect to
real data while remaining in place as contract-mandated defence.
"""

from datetime import datetime, timezone

import pytest

from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.domain.users.serializers import (
    pause_reason_reference_is_unresolved,
    serialize_current_worker_shift_state,
)
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord


pytestmark = pytest.mark.unit

BASE = datetime(2026, 7, 31, 9, tzinfo=timezone.utc)

# The complete distinct set of non-null, non-`par_` values measured on the `.env`
# database (phase 1 inventory, re-confirmed in the phase 3 rehearsal). The backfill
# leaves all of them in place.
LEGACY_VALUES = (
    "pause_case_created",
    "pause_coffee_break",
    "pause_lunch_break",
    "pause_meeting",
    "pause_other_task_priority",
    "waiting_for_upholstery",
    "unspecified",
)


def _paused_row(*, reason: str | None, transition_reason: str | None = None) -> UserShiftStateRecord:
    return UserShiftStateRecord(
        workspace_id="ws_test",
        user_id="usr_test",
        state=UserShiftStateEnum.IN_PAUSE,
        entered_at=BASE,
        exited_at=None,
        reason=reason,
        transition_reason=transition_reason,
    )


def test_backfilled_shape_resolves_through_the_map_not_the_prefix_branch() -> None:
    """The shape the migration writes: catalog reference gone, transition typed."""
    row = _paused_row(reason=None, transition_reason="other_task_priority")
    assert pause_reason_reference_is_unresolved(row, None) is False
    data = serialize_current_worker_shift_state(
        user_id="usr_test", current=row, pause_reason=None
    )
    assert data["pause_reason"]["name"] == "Other task priority"
    assert "reason_text" not in data


@pytest.mark.parametrize("legacy", LEGACY_VALUES)
def test_legacy_values_never_enter_the_suppression_arm(legacy: str) -> None:
    row = _paused_row(reason=legacy)
    assert pause_reason_reference_is_unresolved(row, None) is False
    data = serialize_current_worker_shift_state(
        user_id="usr_test", current=row, pause_reason=None
    )
    assert data["reason_text"] == legacy


def test_a_resolving_catalog_id_never_enters_the_suppression_arm() -> None:
    reason = PauseReason(
        client_id="par_worker_chosen",
        workspace_id="ws_test",
        name="Lunch break",
        image_url=None,
    )
    row = _paused_row(reason=reason.client_id)
    assert pause_reason_reference_is_unresolved(row, reason) is False
    data = serialize_current_worker_shift_state(
        user_id="usr_test", current=row, pause_reason=reason
    )
    assert data["pause_reason"]["id"] == "par_worker_chosen"
    assert "reason_text" not in data


def test_null_reason_rows_never_enter_the_suppression_arm() -> None:
    assert pause_reason_reference_is_unresolved(_paused_row(reason=None), None) is False
