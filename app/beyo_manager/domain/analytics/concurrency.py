"""Concurrency-averaged time for batch working (pure domain logic).

When a worker runs several batchable steps at once, each moment of real time is
shared among the steps concurrently open in that state — so a batch of N steps
open for a real duration D each earns D/N, and the steps sum back to the real
wall-clock time. Non-batch steps always earn their full time (they never divide
and never count toward anyone's divisor).

This is the single source of truth for batch averaging: the analytics worker, the
worker-stats endpoints, and the backfill all compute time through this function,
so the aggregates are a deterministic, idempotent projection of the raw records.

It also owns the *forward* twin of that rule — `accrual_rate_by_record` — which
answers "how fast is this record accruing right now" rather than "how much has it
accrued". Both live here so the rate can never disagree with the seconds it predicts.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction


@dataclass(frozen=True)
class TimeInterval:
    """One worker's single state interval, as needed by the sweep."""

    record_id: str
    step_id: str
    state: str                    # "working" | "paused" | "ended_shift"
    entered_at: datetime
    exited_at: datetime | None    # None = still open (uses ``now``)
    marked_wrong: bool            # record/step flag; selected by the caller's sweep
    is_batchable: bool            # TaskStep.allows_batch_working


def _sweep(
    intervals: Iterable[TimeInterval], now: datetime
) -> dict[str, float]:
    """Run the concurrency sweep for the supplied interval population."""
    result: dict[str, float] = defaultdict(float)

    by_state: dict[str, list[TimeInterval]] = defaultdict(list)
    for interval in intervals:
        by_state[interval.state].append(interval)

    for state_intervals in by_state.values():
        # (record_id, start, end) for batchable intervals feeding the sweep.
        batchable: list[tuple[str, datetime, datetime]] = []
        for interval in state_intervals:
            end = interval.exited_at or now
            duration = (end - interval.entered_at).total_seconds()
            if duration <= 0:
                continue
            if interval.is_batchable:
                batchable.append((interval.record_id, interval.entered_at, end))
            else:
                # Non-batch: full time, never divided.
                result[interval.record_id] += duration

        if not batchable:
            continue

        # Sweep-line: between consecutive boundary points the open set is constant.
        points = sorted({p for (_, start, end) in batchable for p in (start, end)})
        for left, right in zip(points, points[1:]):
            segment = (right - left).total_seconds()
            if segment <= 0:
                continue
            open_ids = [rid for (rid, start, end) in batchable if start <= left and end >= right]
            k = len(open_ids)
            if k == 0:
                continue
            share = segment / k
            for rid in open_ids:
                result[rid] += share

    return dict(result)


def averaged_seconds_by_record(
    intervals: Iterable[TimeInterval], now: datetime
) -> dict[str, float]:
    """Per-record concurrency-averaged seconds for **one worker**.

    Per state: batchable intervals split each instant by the number of
    concurrently-open **batchable** intervals; non-batch intervals earn their full
    duration and are excluded from the divisor. ``marked_wrong`` intervals are
    dropped (earn nothing, reduce nothing). Open intervals use ``now`` as their end
    and still count toward concurrency (so a closed record's share is reduced by an
    overlapping open one). Deterministic: identical input → identical output.

    Returns ``{record_id: seconds}`` (float) for every accruing record.
    """
    return _sweep((interval for interval in intervals if not interval.marked_wrong), now)


def accrual_rate_by_record(
    intervals: Iterable[TimeInterval], now: datetime
) -> dict[str, tuple[Fraction, int]]:
    """Forward accrual rate per **open** interval: seconds credited per wall-clock second.

    Returns ``{record_id: (rate, concurrency)}`` for accruing records only; a record absent
    from the mapping is not accruing. ``concurrency`` is the divisor the rate came from, so
    ``rate == Fraction(1, concurrency)`` always holds.

    Same rule as ``averaged_seconds_by_record``, evaluated at ``now`` instead of integrated
    over an interval: group by state, then a batchable interval takes ``1/k`` where ``k`` is
    the number of concurrently-open batchable intervals in that state, while a non-batch
    interval takes the full ``1`` and stays out of everyone's divisor.

    THREE DELIBERATE DIVERGENCES FROM ``_sweep`` — each one is load-bearing:

    1. **Only open intervals count.** A closed record earns nothing going forward, so it must
       not sit in the divisor. This is what makes "pause one of three, the other two go to
       1/2" fall out, and it is why the rate CANNOT be read off ``_sweep``'s last segment: a
       record whose share was halved by a peer that has since closed is now accruing at the
       full ``1``, not at ``1/2``.
    2. **No ``duration <= 0`` skip.** A record opened this very instant has accrued nothing
       but does have a forward rate, and reporting ``None`` for it would stall a just-started
       timer for one poll.
    3. **``marked_wrong`` intervals are dropped**, exactly as ``averaged_seconds_by_record``
       drops them — they neither accrue nor dilute.

    Grouping by state first is also what keeps a PAUSED or ``ended_shift`` record from
    diluting a WORKING one: they are simply different populations.
    """
    eligible_by_state: dict[str, list[TimeInterval]] = defaultdict(list)
    for interval in intervals:
        if interval.exited_at is not None or interval.marked_wrong:
            continue
        if interval.entered_at > now:
            continue
        eligible_by_state[interval.state].append(interval)

    rates: dict[str, tuple[Fraction, int]] = {}
    for state_intervals in eligible_by_state.values():
        divisor = sum(1 for interval in state_intervals if interval.is_batchable)
        for interval in state_intervals:
            if interval.is_batchable:
                # divisor >= 1 here: this interval is itself batchable and was counted.
                rates[interval.record_id] = (Fraction(1, divisor), divisor)
            else:
                rates[interval.record_id] = (Fraction(1), 1)
    return rates


def wasted_seconds_by_record(
    intervals: Iterable[TimeInterval], now: datetime
) -> dict[str, float]:
    """Per-record concurrency-averaged seconds for flagged intervals only.

    The flagged population is swept independently from trusted intervals. This makes
    a flagged batch step's full averaged step time wasted instead of allowing trusted
    work to dilute its wasted value.
    """
    return _sweep((interval for interval in intervals if interval.marked_wrong), now)
