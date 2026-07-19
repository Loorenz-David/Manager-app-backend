"""Pure unit tests for the wall-clock (linear) timeline sweep — no DB."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from beyo_manager.domain.analytics.linear_timeline import (
    UNSPECIFIED_REASON,
    LinearInterval,
    compute_linear_segments,
    compute_linear_timeline,
)

T0 = datetime(2026, 7, 18, 9, 0, tzinfo=timezone.utc)
NOW = datetime(2026, 7, 18, 23, 0, tzinfo=timezone.utc)
WINDOW_START = datetime(2026, 7, 18, 0, 0, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 7, 19, 0, 0, tzinfo=timezone.utc)


def _min(m: int) -> datetime:
    return T0 + timedelta(minutes=m)


def _iv(rid, *, state="paused", reason=None, start=0, end=60, step=None):
    return LinearInterval(
        record_id=rid,
        state=state,
        reason=reason,
        entered_at=_min(start),
        exited_at=None if end is None else _min(end),
        step_id=step or f"step_{rid}",
    )


def _run(intervals):
    return compute_linear_timeline(intervals, WINDOW_START, WINDOW_END, NOW)


def _segs(intervals, hard_breaks=()):
    return compute_linear_segments(intervals, WINDOW_START, WINDOW_END, NOW, hard_breaks=hard_breaks)


def test_single_pause_interval():
    out = _run([_iv("a", state="paused", reason="pause_lunch_break", start=0, end=10)])
    assert out.paused_seconds == 600
    assert out.working_seconds == 0
    assert out.pause_by_reason == {"pause_lunch_break": 600}


def test_two_overlapping_pauses_counted_once_on_the_clock():
    # Same 10 minutes paused twice → 10 min wall-clock, not 20.
    out = _run(
        [
            _iv("a", state="paused", reason="pause_lunch_break", start=0, end=10),
            _iv("b", state="paused", reason="pause_lunch_break", start=0, end=10),
        ]
    )
    assert out.paused_seconds == 600
    assert out.pause_by_reason == {"pause_lunch_break": 600}


def test_two_disjoint_pauses_add_up():
    out = _run(
        [
            _iv("a", state="paused", reason="pause_coffee_break", start=0, end=10),
            _iv("b", state="paused", reason="pause_lunch_break", start=20, end=35),
        ]
    )
    assert out.paused_seconds == 600 + 900
    assert out.pause_by_reason == {"pause_coffee_break": 600, "pause_lunch_break": 900}


def test_working_wins_over_concurrent_pause():
    # Worker works [0,60] on item A while item B sits paused [10,30]:
    # the whole overlap is working, so pause contributes nothing.
    out = _run(
        [
            _iv("a", state="working", start=0, end=60),
            _iv("b", state="paused", reason="pause_meeting", start=10, end=30),
        ]
    )
    assert out.working_seconds == 3600
    assert out.paused_seconds == 0
    assert out.pause_by_reason == {}


def test_pause_only_counts_when_not_working():
    # Work [0,20], then pause [20,50] with no work → 30 min real pause between/after work.
    out = _run(
        [
            _iv("a", state="working", start=0, end=20),
            _iv("b", state="paused", reason="pause_other_task_priority", start=20, end=50),
        ]
    )
    assert out.working_seconds == 1200
    assert out.paused_seconds == 1800
    assert out.pause_by_reason == {"pause_other_task_priority": 1800}


def test_partial_overlap_of_work_and_pause():
    # Pause [0,30]; work starts halfway at [15,45]. Working wins on [15,30].
    # Pause effective only on [0,15] = 15 min; working on [15,45] = 30 min.
    out = _run(
        [
            _iv("p", state="paused", reason="pause_coffee_break", start=0, end=30),
            _iv("w", state="working", start=15, end=45),
        ]
    )
    assert out.working_seconds == 1800
    assert out.paused_seconds == 900
    assert out.pause_by_reason == {"pause_coffee_break": 900}


def test_overlapping_pauses_different_reasons_attributed_to_earliest_open():
    # Lunch [0,30] and meeting [10,40] overlap. Each instant credits the earliest-started
    # pause that is still open there: lunch owns [0,30] (incl. the [10,30] overlap); once
    # lunch ends, meeting owns [30,40]. Union = 40 min, split 30 + 10.
    out = _run(
        [
            _iv("lunch", state="paused", reason="pause_lunch_break", start=0, end=30),
            _iv("meeting", state="paused", reason="pause_meeting", start=10, end=40),
        ]
    )
    assert out.paused_seconds == 40 * 60  # [0,40] union
    assert out.pause_by_reason == {"pause_lunch_break": 30 * 60, "pause_meeting": 10 * 60}


def test_missing_reason_bucketed_as_unspecified():
    out = _run([_iv("a", state="paused", reason=None, start=0, end=5)])
    assert out.pause_by_reason == {UNSPECIFIED_REASON: 300}


def test_ended_shift_is_its_own_bucket_not_pause():
    out = _run([_iv("a", state="ended_shift", start=0, end=10)])
    assert out.ended_shift_seconds == 600
    assert out.paused_seconds == 0
    assert out.working_seconds == 0


def test_open_interval_clamped_to_now():
    # Open pause entered 30 min before NOW → 30 min, ended at NOW.
    entered = NOW - timedelta(minutes=30)
    out = compute_linear_timeline(
        [LinearInterval("a", "paused", "pause_meeting", entered, None)],
        WINDOW_START,
        WINDOW_END,
        NOW,
    )
    assert out.paused_seconds == 1800


def test_interval_clamped_to_window():
    # Pause spans from before the window; only the in-window portion counts.
    out = compute_linear_timeline(
        [LinearInterval("a", "paused", "pause_lunch_break", WINDOW_START - timedelta(hours=2), _min(10))],
        WINDOW_START,
        WINDOW_END,
        NOW,
    )
    # From WINDOW_START (00:00) to _min(10) (09:10) = 9h10m.
    assert out.paused_seconds == int((_min(10) - WINDOW_START).total_seconds())


def test_empty_input():
    out = _run([])
    assert out.working_seconds == 0
    assert out.paused_seconds == 0
    assert out.ended_shift_seconds == 0
    assert out.pause_by_reason == {}


def test_stale_pause_capped_by_resume_becomes_idle():
    # Worker pauses A for lunch [0,60], resumes on B [30,50], B ends and nothing starts.
    # Lunch is capped at the resume (30): [0,30] lunch, [30,50] work, [50,60] IDLE — the
    # trailing gap no longer bleeds into lunch.
    out = _run(
        [
            _iv("A", state="paused", reason="pause_lunch_break", start=0, end=60),
            _iv("B", state="working", start=30, end=50),
        ]
    )
    assert out.working_seconds == 20 * 60
    assert out.paused_seconds == 30 * 60
    assert out.idle_seconds == 10 * 60
    assert out.pause_by_reason == {"pause_lunch_break": 30 * 60}


def test_idle_gap_between_two_work_bursts_with_no_pause():
    # No pause at all; two work bursts with a bare gap → the gap is idle, not pause.
    out = _run(
        [
            _iv("w1", state="working", start=0, end=10),
            _iv("w2", state="working", start=50, end=60),
        ]
    )
    assert out.working_seconds == 20 * 60
    assert out.idle_seconds == 40 * 60
    assert out.paused_seconds == 0
    assert out.pause_by_reason == {}


def test_fresh_repause_after_resume_still_counts():
    # Pause A (lunch), resume on B, then genuinely pause B (coffee): the coffee pause is a
    # new interval after the resume, so it counts — only the stale lunch tail would idle.
    out = _run(
        [
            _iv("A", state="paused", reason="pause_lunch_break", start=0, end=30),
            _iv("B", state="working", start=30, end=50),
            _iv("Bp", state="paused", reason="pause_coffee_break", start=50, end=70),
        ]
    )
    assert out.working_seconds == 20 * 60
    assert out.paused_seconds == 50 * 60
    assert out.idle_seconds == 0
    assert out.pause_by_reason == {"pause_coffee_break": 20 * 60, "pause_lunch_break": 30 * 60}


def test_brief_work_blip_turns_rest_of_pause_into_idle():
    # The accepted tradeoff: a 2-min work blip consumes the pause; the remaining paused
    # time (nobody re-paused) becomes idle rather than lunch.
    out = _run(
        [
            _iv("A", state="paused", reason="pause_lunch_break", start=0, end=60),
            _iv("blip", state="working", start=10, end=12),
        ]
    )
    assert out.working_seconds == 2 * 60
    assert out.paused_seconds == 10 * 60
    assert out.idle_seconds == 48 * 60
    assert out.pause_by_reason == {"pause_lunch_break": 10 * 60}


def test_buckets_partition_the_active_span():
    out = _run(
        [
            _iv("A", state="paused", reason="pause_lunch_break", start=0, end=60),
            _iv("B", state="working", start=30, end=50),
        ]
    )
    total = out.working_seconds + out.paused_seconds + out.ended_shift_seconds + out.idle_seconds
    assert total == 60 * 60  # first activity (0) → last boundary (60)


def test_pause_by_reason_reconciles_with_total():
    out = _run(
        [
            _iv("a", state="paused", reason="pause_coffee_break", start=0, end=7),
            _iv("b", state="paused", reason="pause_lunch_break", start=10, end=23),
            _iv("c", state="paused", reason="pause_meeting", start=30, end=31),
        ]
    )
    assert sum(out.pause_by_reason.values()) == out.paused_seconds


# ---------------------------------------------------------------------------
# compute_linear_segments (the drawable partition)
# ---------------------------------------------------------------------------


def test_segments_partition_pause_work_idle():
    segs = _segs(
        [
            _iv("A", state="paused", reason="pause_lunch_break", start=0, end=60, step="s_A"),
            _iv("B", state="working", start=30, end=50, step="s_B"),
        ]
    )
    assert [(s.state, s.reason, s.seconds, s.step_ids) for s in segs] == [
        ("paused", "pause_lunch_break", 1800, ("s_A",)),
        ("working", None, 1200, ("s_B",)),
        ("idle", None, 600, ()),  # capped-lunch tail → idle, no steps
    ]


def test_segments_merge_concurrent_working_into_one_run_unioning_steps():
    # Two batchable working items overlap; the whole run is one working segment whose
    # steps are the union (the raw sub-segments as batch composition changes are merged).
    segs = _segs(
        [
            _iv("X", state="working", start=0, end=20, step="s_X"),
            _iv("Y", state="working", start=10, end=30, step="s_Y"),
        ]
    )
    assert len(segs) == 1
    assert segs[0].state == "working"
    assert segs[0].seconds == 30 * 60
    assert segs[0].step_ids == ("s_X", "s_Y")


def test_segments_do_not_merge_across_a_hard_break():
    # A continuous working run split at a forced day boundary (min 30) → two segments.
    segs = _segs(
        [_iv("W", state="working", start=0, end=60, step="s_W")],
        hard_breaks=[_min(30)],
    )
    assert [(s.state, s.start, s.end) for s in segs] == [
        ("working", _min(0), _min(30)),
        ("working", _min(30), _min(60)),
    ]
    assert all(s.step_ids == ("s_W",) for s in segs)


def test_segments_do_not_merge_pauses_with_different_reasons():
    segs = _segs(
        [
            _iv("l", state="paused", reason="pause_lunch_break", start=0, end=10),
            _iv("c", state="paused", reason="pause_coffee_break", start=10, end=20),
        ]
    )
    assert [(s.state, s.reason) for s in segs] == [
        ("paused", "pause_lunch_break"),
        ("paused", "pause_coffee_break"),
    ]


def test_segment_is_open_when_run_reaches_now_via_open_record():
    entered = NOW - timedelta(minutes=30)
    segs = compute_linear_segments(
        [LinearInterval("o", "working", None, entered, None, step_id="s_o")],
        WINDOW_START,
        WINDOW_END,
        NOW,
    )
    assert len(segs) == 1
    assert segs[0].state == "working"
    assert segs[0].is_open is True
    assert segs[0].end == NOW


def test_segment_records_carry_true_record_times():
    # A working block from two batch records; each record keeps its own raw span.
    segs = _segs(
        [
            _iv("X", state="working", start=0, end=20, step="s_X"),
            _iv("Y", state="working", start=10, end=30, step="s_Y"),
        ]
    )
    assert len(segs) == 1
    recs = {r.record_id: r for r in segs[0].records}
    assert recs["X"].entered_at == _min(0) and recs["X"].exited_at == _min(20)
    assert recs["Y"].entered_at == _min(10) and recs["Y"].exited_at == _min(30)
    assert all(r.state == "working" and r.is_open is False for r in segs[0].records)


def test_paused_block_records_keep_their_own_reasons():
    # Two items paused concurrently for different reasons. The block is attributed to the
    # earliest (lunch), but both records are present, each with its own reason.
    segs = _segs(
        [
            _iv("l", state="paused", reason="pause_lunch_break", start=0, end=30),
            _iv("m", state="paused", reason="pause_meeting", start=0, end=30),
        ]
    )
    assert len(segs) == 1
    assert segs[0].reason == "pause_lunch_break"  # block owner
    assert {(r.record_id, r.reason) for r in segs[0].records} == {
        ("l", "pause_lunch_break"),
        ("m", "pause_meeting"),
    }


def test_idle_segment_has_no_records():
    segs = _segs(
        [
            _iv("w1", state="working", start=0, end=10, step="s1"),
            _iv("w2", state="working", start=50, end=60, step="s2"),
        ]
    )
    idle = [s for s in segs if s.state == "idle"]
    assert len(idle) == 1
    assert idle[0].records == ()


def test_open_record_marked_open_in_segment_records():
    entered = NOW - timedelta(minutes=30)
    segs = compute_linear_segments(
        [LinearInterval("o", "working", None, entered, None, step_id="s_o")],
        WINDOW_START,
        WINDOW_END,
        NOW,
    )
    assert segs[0].records[0].is_open is True
    assert segs[0].records[0].exited_at is None


def test_segments_reconcile_with_aggregate_totals():
    intervals = [
        _iv("A", state="paused", reason="pause_lunch_break", start=0, end=60, step="s_A"),
        _iv("B", state="working", start=30, end=50, step="s_B"),
    ]
    segs = _segs(intervals)
    agg = _run(intervals)
    by_state = {"working": 0, "paused": 0, "ended_shift": 0, "idle": 0}
    for s in segs:
        by_state[s.state] += s.seconds
    assert by_state["working"] == agg.working_seconds
    assert by_state["paused"] == agg.paused_seconds
    assert by_state["idle"] == agg.idle_seconds
