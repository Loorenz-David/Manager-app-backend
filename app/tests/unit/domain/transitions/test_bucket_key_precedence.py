"""`bucket_key`'s catalog-first ordering, asserted without a database.

Phase 2 asserted this through a `step_state_records` row carrying both explanations. Phase 4's
CHECK constraint makes that row unconstructible — T2 plus phase 1's no-`WORKER_PAUSED` ruling mean
a step record carries one or the other, and the database now enforces it.

The ordering is therefore **defensive** on that table rather than reachable, which is a reason to
assert it directly rather than to delete it: legacy rows written before the constraint, and any
future writer that reaches this code with both fields set, still depend on which one wins.
"""
from datetime import datetime, timezone

from beyo_manager.services.queries.worker_stats.get_worker_linear_timeline_breakdown import (
    _StepTimelineRecord,
)


def _record(*, reason: str | None, transition_reason: str | None) -> _StepTimelineRecord:
    return _StepTimelineRecord(
        record_id="ssr_x",
        step_id="tsp_x",
        state="paused",
        reason=reason,
        description=None,
        entered_at=datetime(2026, 7, 19, 9, tzinfo=timezone.utc),
        exited_at=datetime(2026, 7, 19, 10, tzinfo=timezone.utc),
        transition_reason=transition_reason,
    )


def test_catalog_reference_wins_when_a_record_carries_both():
    record = _record(reason="par_catalog", transition_reason="other_task_priority")
    assert record.bucket_key({"par_catalog"}) == "par_catalog"


def test_transition_reason_is_used_when_there_is_no_catalog_reference():
    record = _record(reason=None, transition_reason="shift_ended")
    assert record.bucket_key(set()) == "shift_ended"


def test_an_unresolvable_catalog_id_falls_through_rather_than_leaking():
    """The workspace-resolution guard: an id absent from the resolved set is not emitted.

    This is phase 1's blocking finding made structural — `bucket_key` requires the resolved set as
    an argument precisely so a foreign workspace's id cannot reach a workspace-scoped response.
    """
    record = _record(reason="par_from_another_workspace", transition_reason="shift_ended")
    assert record.bucket_key(set()) == "shift_ended"


def test_neither_channel_yields_no_key():
    assert _record(reason=None, transition_reason=None).bucket_key(set()) is None
