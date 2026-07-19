"""Wall-clock (linear) timeline for one worker (pure domain logic).

The daily-stats totals sum every state interval independently, so two items paused
over the same ten minutes contribute twenty minutes of pause. That answers "how long
did items sit paused", but not "over the worker's real day, how much time passed
between working, and why". This module answers the second question.

At every instant the worker is collapsed to a **single** effective state:

* **working** — any item is being worked (wins over everything, even while other items
  sit paused);
* **paused** — no item is being worked and at least one *active* pause is open, credited
  to that pause's reason;
* **ended_shift** — no work and no active pause, but an ended-shift interval is open;
* **idle** — none of the above: time inside the worker's active span that isn't
  attributed to anything (researching the next item, un-booked gaps, a forgotten pause
  after the worker already resumed).

The buckets are disjoint and partition the real elapsed span.

**Stale-pause capping.** A paused ``StepStateRecord`` stays open until it is explicitly
resumed, so a pause the worker walked away from would otherwise keep absorbing every
later idle gap under its old reason. Each pause is therefore *capped at the worker's
next resume* — the first moment they start working anything after the pause began.
Beyond that cap the pause is stale: it stops counting as pause and the non-working time
it used to cover falls through to **idle**. A genuine re-pause after resuming is a fresh
interval and still counts.

Overlapping *active* pauses with different reasons are attributed to the pause that
**started earliest** (ties broken by ``record_id``).

Two views share one sweep:

* :func:`compute_linear_timeline` — aggregate seconds per bucket (roster totals);
* :func:`compute_linear_segments` — the ordered partition as merged, typed segments
  carrying the underlying records/steps, for drawing an interactive timeline.
"""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

# Key used for paused intervals that carry no reason.
UNSPECIFIED_REASON = "unspecified"


@dataclass(frozen=True)
class LinearInterval:
    """One worker's single state interval, as needed by the linear sweep."""

    record_id: str
    state: str                    # "working" | "paused" | "ended_shift"
    reason: str | None            # StepEventReasonEnum value; only read for paused
    entered_at: datetime
    exited_at: datetime | None    # None = still open (clamped to ``now``)
    step_id: str = ""             # owning TaskStep; only needed for the segments view


@dataclass(frozen=True)
class LinearTimeline:
    working_seconds: int
    paused_seconds: int
    ended_shift_seconds: int
    idle_seconds: int
    pause_by_reason: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class LinearSegmentRecord:
    """One state record contributing to a segment, with its own (true) record times.

    ``entered_at``/``exited_at`` are the record's real span (not clamped to the segment or
    window), so the frontend can place the individual record inside the block. ``state``
    equals the segment's effective state; ``reason`` is this record's own reason (in a
    paused block with several items paused, each keeps its reason — the block only shows
    the owner's).
    """

    record_id: str
    step_id: str
    state: str
    reason: str | None
    entered_at: datetime
    exited_at: datetime | None
    is_open: bool


@dataclass(frozen=True)
class LinearSegment:
    """One contiguous run of a single effective state on the wall-clock timeline."""

    start: datetime
    end: datetime
    state: str                              # "working" | "paused" | "ended_shift" | "idle"
    reason: str | None                      # owner reason for paused runs, else None
    record_ids: tuple[str, ...]             # effective-state records active in the run
    step_ids: tuple[str, ...]               # their owning steps (deduped, sorted)
    records: tuple[LinearSegmentRecord, ...]  # per-record detail, ordered by entered_at
    is_open: bool                           # run reaches ``now`` via a still-open record

    @property
    def seconds(self) -> int:
        return int(round((self.end - self.start).total_seconds()))


@dataclass(frozen=True)
class _Entry:
    """A window-clamped interval plus its pause-active end (``active_end``)."""

    start: datetime
    end: datetime
    active_end: datetime          # min(end, next-resume) for pauses; == end otherwise
    interval: LinearInterval


@dataclass(frozen=True)
class _RawSegment:
    start: datetime
    end: datetime
    state: str
    reason: str | None
    record_ids: frozenset[str]
    step_ids: frozenset[str]
    is_open: bool


def _clamp(
    interval: LinearInterval, window_start: datetime, window_end: datetime, now: datetime
) -> tuple[datetime, datetime] | None:
    """Clamp an interval to ``[window_start, window_end]`` (open intervals end at ``now``)."""
    start = max(interval.entered_at, window_start)
    end = min(interval.exited_at or now, window_end)
    if end <= start:
        return None
    return start, end


def _first_after(sorted_points: list[datetime], moment: datetime) -> datetime | None:
    """First point strictly greater than ``moment`` (the worker's next resume), or None."""
    idx = bisect_right(sorted_points, moment)
    return sorted_points[idx] if idx < len(sorted_points) else None


def _sweep(
    intervals: Iterable[LinearInterval],
    window_start: datetime,
    window_end: datetime,
    now: datetime,
    extra_points: Iterable[datetime] = (),
) -> list[_RawSegment]:
    """Partition the window into raw segments, one per gap between boundary points.

    ``extra_points`` are additional hard boundaries (e.g. day midnights) forced into the
    sweep so no raw segment straddles them. Empty windows yield ``[]``.
    """
    clamped: list[tuple[datetime, datetime, LinearInterval]] = []
    working_starts: list[datetime] = []
    open_ids: set[str] = set()
    for interval in intervals:
        span = _clamp(interval, window_start, window_end, now)
        if span is None:
            continue
        clamped.append((span[0], span[1], interval))
        if interval.state == "working":
            working_starts.append(span[0])
        if interval.exited_at is None:
            open_ids.add(interval.record_id)

    if not clamped:
        return []

    working_starts.sort()

    entries: list[_Entry] = []
    for start, end, interval in clamped:
        if interval.state == "paused":
            resume = _first_after(working_starts, start)
            active_end = min(end, resume) if resume is not None else end
        else:
            active_end = end
        entries.append(_Entry(start, end, active_end, interval))

    points = {p for e in entries for p in (e.start, e.end)}
    points.update(p for p in extra_points if window_start <= p <= window_end)
    ordered = sorted(points)

    raw: list[_RawSegment] = []
    for left, right in zip(ordered, ordered[1:]):
        if (right - left).total_seconds() <= 0:
            continue

        working = [e for e in entries if e.interval.state == "working" and e.start <= left and e.end >= right]
        if working:
            state, reason, chosen = "working", None, working
        else:
            active_pauses = [
                e for e in entries
                if e.interval.state == "paused" and e.start <= left and e.active_end >= right
            ]
            if active_pauses:
                owner = min(active_pauses, key=lambda e: (e.interval.entered_at, e.interval.record_id))
                state, reason, chosen = "paused", owner.interval.reason or UNSPECIFIED_REASON, active_pauses
            else:
                ended = [e for e in entries if e.interval.state == "ended_shift" and e.start <= left and e.end >= right]
                if ended:
                    state, reason, chosen = "ended_shift", None, ended
                else:
                    state, reason, chosen = "idle", None, []

        record_ids = frozenset(e.interval.record_id for e in chosen)
        step_ids = frozenset(e.interval.step_id for e in chosen if e.interval.step_id)
        is_open = right == now and any(e.interval.record_id in open_ids for e in chosen)
        raw.append(_RawSegment(left, right, state, reason, record_ids, step_ids, is_open))

    return raw


def compute_linear_timeline(
    intervals: Iterable[LinearInterval],
    window_start: datetime,
    window_end: datetime,
    now: datetime,
) -> LinearTimeline:
    """Aggregate wall-clock seconds per bucket for one worker (roster totals view)."""
    seconds = {"working": 0.0, "paused": 0.0, "ended_shift": 0.0, "idle": 0.0}
    pause_by_reason: dict[str, float] = defaultdict(float)
    for seg in _sweep(intervals, window_start, window_end, now):
        secs = (seg.end - seg.start).total_seconds()
        seconds[seg.state] += secs
        if seg.state == "paused":
            pause_by_reason[seg.reason or UNSPECIFIED_REASON] += secs

    # Round reason buckets and derive the pause total from them so the breakdown always
    # reconciles exactly with ``paused_seconds`` (no fractional rounding drift).
    reason_seconds = {reason: int(round(secs)) for reason, secs in sorted(pause_by_reason.items())}
    return LinearTimeline(
        working_seconds=int(round(seconds["working"])),
        paused_seconds=sum(reason_seconds.values()),
        ended_shift_seconds=int(round(seconds["ended_shift"])),
        idle_seconds=int(round(seconds["idle"])),
        pause_by_reason=reason_seconds,
    )


def compute_linear_segments(
    intervals: Iterable[LinearInterval],
    window_start: datetime,
    window_end: datetime,
    now: datetime,
    hard_breaks: Iterable[datetime] = (),
) -> list[LinearSegment]:
    """Ordered partition of the window as merged, typed segments (interactive-timeline view).

    Consecutive raw segments with the same ``(state, reason)`` are merged into one run,
    unioning their records/steps — except across a ``hard_breaks`` boundary (e.g. day
    midnights), which always starts a new segment so callers can group cleanly by day.
    """
    intervals = list(intervals)
    by_id = {iv.record_id: iv for iv in intervals}
    breaks = frozenset(hard_breaks)
    raw = _sweep(intervals, window_start, window_end, now, extra_points=breaks)

    # Merge consecutive raw segments (accumulating record ids) into runs.
    runs: list[dict] = []
    for seg in raw:
        prev = runs[-1] if runs else None
        if (
            prev is not None
            and prev["state"] == seg.state
            and prev["reason"] == seg.reason
            and seg.start not in breaks
        ):
            prev["end"] = seg.end
            prev["record_ids"] |= seg.record_ids
            prev["is_open"] = seg.is_open
        else:
            runs.append(
                {
                    "start": seg.start,
                    "end": seg.end,
                    "state": seg.state,
                    "reason": seg.reason,
                    "record_ids": set(seg.record_ids),
                    "is_open": seg.is_open,
                }
            )

    segments: list[LinearSegment] = []
    for run in runs:
        records = _segment_records(run["record_ids"], by_id)
        segments.append(
            LinearSegment(
                start=run["start"],
                end=run["end"],
                state=run["state"],
                reason=run["reason"],
                record_ids=tuple(sorted(run["record_ids"])),
                step_ids=tuple(sorted({r.step_id for r in records if r.step_id})),
                records=records,
                is_open=run["is_open"],
            )
        )
    return segments


def _segment_records(
    record_ids: set[str], by_id: dict[str, LinearInterval]
) -> tuple[LinearSegmentRecord, ...]:
    """Per-record detail for a segment, ordered by (entered_at, record_id)."""
    ivs = sorted(
        (by_id[rid] for rid in record_ids if rid in by_id),
        key=lambda iv: (iv.entered_at, iv.record_id),
    )
    return tuple(
        LinearSegmentRecord(
            record_id=iv.record_id,
            step_id=iv.step_id,
            state=iv.state,
            reason=iv.reason,
            entered_at=iv.entered_at,
            exited_at=iv.exited_at,
            is_open=iv.exited_at is None,
        )
        for iv in ivs
    )
