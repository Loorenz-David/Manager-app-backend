"""Concurrency-averaged time for batch working (pure domain logic).

When a worker runs several batchable steps at once, each moment of real time is
shared among the steps concurrently open in that state — so a batch of N steps
open for a real duration D each earns D/N, and the steps sum back to the real
wall-clock time. Non-batch steps always earn their full time (they never divide
and never count toward anyone's divisor).

This is the single source of truth for batch averaging: the analytics worker, the
worker-stats endpoints, and the backfill all compute time through this function,
so the aggregates are a deterministic, idempotent projection of the raw records.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime


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


def wasted_seconds_by_record(
    intervals: Iterable[TimeInterval], now: datetime
) -> dict[str, float]:
    """Per-record concurrency-averaged seconds for flagged intervals only.

    The flagged population is swept independently from trusted intervals. This makes
    a flagged batch step's full averaged step time wasted instead of allowing trusted
    work to dilute its wasted value.
    """
    return _sweep((interval for interval in intervals if interval.marked_wrong), now)
