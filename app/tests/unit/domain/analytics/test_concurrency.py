"""Pure unit tests for concurrency-averaged batch time — no DB."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from beyo_manager.domain.analytics.concurrency import (
    TimeInterval,
    averaged_seconds_by_record,
    wasted_seconds_by_record,
)

T0 = datetime(2026, 7, 18, 9, 0, tzinfo=timezone.utc)
NOW = datetime(2026, 7, 18, 23, 0, tzinfo=timezone.utc)


def _min(m: int) -> datetime:
    return T0 + timedelta(minutes=m)


def _iv(rid, *, state="working", start=0, end=60, wrong=False, batch=True, step=None):
    return TimeInterval(
        record_id=rid, step_id=step or f"step_{rid}", state=state,
        entered_at=_min(start), exited_at=None if end is None else _min(end),
        marked_wrong=wrong, is_batchable=batch,
    )


def _approx(a, b, tol=1.0):
    return abs(a - b) <= tol


def test_single_interval_full_time():
    out = averaged_seconds_by_record([_iv("a", start=0, end=60)], NOW)
    assert _approx(out["a"], 3600)


def test_n_identical_batch_intervals_split_evenly():
    ivs = [_iv(f"r{i}", start=0, end=60) for i in range(5)]  # 5 steps, 60 min each
    out = averaged_seconds_by_record(ivs, NOW)
    for i in range(5):
        assert _approx(out[f"r{i}"], 3600 / 5)          # 720s each
    assert _approx(sum(out.values()), 3600)             # Σ == real 60 min


def test_late_join_drift_worked_example():
    # 6 batchable [0,70] + 1 batchable [10,70]. Early: 10/6 + 60/7 min; late: 60/7 min.
    ivs = [_iv(f"e{i}", start=0, end=70) for i in range(6)]
    ivs.append(_iv("late", start=10, end=70))
    out = averaged_seconds_by_record(ivs, NOW)
    early_expected = (10 / 6 + 60 / 7) * 60      # seconds
    late_expected = (60 / 7) * 60
    for i in range(6):
        assert _approx(out[f"e{i}"], early_expected)
    assert _approx(out["late"], late_expected)
    assert _approx(sum(out.values()), 70 * 60)   # batch Σ == real 70 min


def test_partial_overlap():
    # A [0,60], B [20,40]. A: 20 + 20/2 + 20 = 50 min; B: 20/2 = 10 min; Σ = 60.
    out = averaged_seconds_by_record([_iv("A", start=0, end=60), _iv("B", start=20, end=40)], NOW)
    assert _approx(out["A"], 50 * 60)
    assert _approx(out["B"], 10 * 60)
    assert _approx(sum(out.values()), 60 * 60)


def test_only_batch_divides_non_batch_keeps_full_time():
    # Non-batch N [0,60] overlaps batch B [0,60]. N stays full; B stays full (alone among batchable).
    out = averaged_seconds_by_record(
        [_iv("N", start=0, end=60, batch=False), _iv("B", start=0, end=60, batch=True)], NOW
    )
    assert _approx(out["N"], 3600)   # non-batch not diluted
    assert _approx(out["B"], 3600)   # only batchable in its lane -> k=1


def test_two_batch_plus_one_nonbatch_overlap():
    # 2 batchable split among themselves; the non-batch is untouched.
    out = averaged_seconds_by_record(
        [_iv("b1", end=60), _iv("b2", end=60), _iv("n", end=60, batch=False)], NOW
    )
    assert _approx(out["b1"], 1800)
    assert _approx(out["b2"], 1800)
    assert _approx(out["n"], 3600)


def test_marked_wrong_excluded_and_does_not_reduce_others():
    # Wrong interval overlaps a batch step; it earns nothing and doesn't divide B.
    out = averaged_seconds_by_record(
        [_iv("wrong", end=60, wrong=True), _iv("B", end=60)], NOW
    )
    assert "wrong" not in out
    assert _approx(out["B"], 3600)   # B alone -> full


def test_states_are_independent():
    # A working [0,60] and P paused [0,60] don't share a divisor.
    out = averaged_seconds_by_record(
        [_iv("w", state="working", end=60), _iv("p", state="paused", end=60)], NOW
    )
    assert _approx(out["w"], 3600)
    assert _approx(out["p"], 3600)


def test_open_record_reduces_closed_record_share():
    # Closed A [0,60], open B [30, now]. During [30,60] k=2 -> A: 30 + 30/2 = 45 min.
    out = averaged_seconds_by_record(
        [_iv("A", start=0, end=60), _iv("B", start=30, end=None)], NOW
    )
    assert _approx(out["A"], 45 * 60)


def test_determinism_under_shuffle():
    import random
    ivs = [_iv(f"e{i}", start=0, end=70) for i in range(6)] + [_iv("late", start=10, end=70)]
    baseline = averaged_seconds_by_record(list(ivs), NOW)
    shuffled = list(ivs)
    random.Random(7).shuffle(shuffled)
    assert averaged_seconds_by_record(shuffled, NOW) == baseline


def test_zero_and_negative_duration_ignored():
    out = averaged_seconds_by_record([_iv("z", start=30, end=30)], NOW)
    assert out == {}


def test_wasted_batch_is_swept_independently_from_trusted_intervals():
    ivs = [
        _iv("wrong_a", end=60, wrong=True),
        _iv("wrong_b", end=60, wrong=True),
    ]
    out = wasted_seconds_by_record(ivs, NOW)
    assert _approx(out["wrong_a"], 1800)
    assert _approx(out["wrong_b"], 1800)
    assert _approx(sum(out.values()), 3600)


def test_wasted_lone_interval_keeps_full_duration():
    out = wasted_seconds_by_record([_iv("wrong", end=60, wrong=True)], NOW)
    assert _approx(out["wrong"], 3600)
