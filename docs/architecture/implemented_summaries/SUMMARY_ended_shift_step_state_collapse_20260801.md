# SUMMARY_ended_shift_step_state_collapse_20260801

## Metadata

- Summary ID: `SUMMARY_ended_shift_step_state_collapse_20260801`
- Status: `summarized`
- Owner agent: `claude-opus-5` (operator: David)
- Created at (UTC): `2026-08-01T00:00:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_ended_shift_step_state_collapse_20260801.md`
- Intention: `backend/docs/architecture/under_construction/intention/INTENTION_ended_shift_step_state_collapse_20260731.md`

## What was implemented

`TaskStepStateEnum.ENDED_SHIFT` is gone. A step that stops because a shift ended is now simply
`PAUSED`, and *why* it stopped travels in `transition_reason` (system) or `pause_reason_id` (the
worker's choice) — the same category error the `system_transition_reasons` set removed one layer
down, applied one layer up.

- **A single derived bucket** in a new `domain/analytics/time_buckets.py`, applied at three sites:
  one SQL `CASE` in `averaged_time.py` and two Python calls. The plan named two.
- **`compute_record_contributions`'s six consumers** keep working untouched, verified per consumer.
- **Reclassifying migration** `2645b4327b17` — 208 rows, per E2's three-row table.
- **Frontend** — `pause-reason-transition.ts` deletion was already in that tree from the existing
  handoff; verified, not authored, and nothing was committed in that repository.

### E1 — the ruling that shaped the metric

Clock-out keeps closing `WORKING` steps only. A `PAUSED` record measures **how long the item stood
still for a stated reason** — an item metric, not shift accounting — so force-closing it would
destroy the measurement. `total_ended_shift_seconds` therefore narrows to the **unattributed**
bucket: the item stopped because the shift ended and nobody said why.

That reframing is what dissolved a concern raised during planning — that a worker-picked ended-shift
pause would move into `total_pause_seconds` and corrupt the ratio. It does move, and that is correct
classification: the worker stated a reason.

## Review history

Round 1 `NEEDS_CHANGES` (R1 blocking, R2/R3 documentation). Round 2 **APPROVED** with R4 low.
R4 closed afterwards.

### R1 — the finding worth carrying forward

`heal_open_shifts_today.py`'s `_TIME_STATES = (WORKING, PAUSED)` **was never edited**, and that is
exactly why two independent sweeps missed it. Before the collapse, a clock-out force-closed record
was `ended_shift` and fell outside the tuple; afterwards it is `paused`, entered at exactly
`clock_out_at` — which is also exactly where `scope_start` lands.

The query implementing *"a worker who already clocked out today is skipped"* began finding the
clock-out record itself. With `--execute` it would write a `STARTED_SHIFT` marker at the clock-out
instant and reopen the tail: **a clocked-out worker left with an open shift running to now.**

**This is a third distinct sweep failure mode in this codebase.** An attribute grep misses a site
that calls through a local; an output-key grep catches that but not this; and neither can reach a
filter that *stood still while the data moved into it*. The question that finds it is not "what
reads this value" but **"what filter previously excluded it, and now doesn't?"**

Fixed with a documented `_worker_activity()` predicate excluding `transition_reason = 'shift_ended'`
at both call sites, using `IS DISTINCT FROM` rather than `!=` — `transition_reason` is NULL on every
worker-driven record, and `NULL != 'shift_ended'` is NULL, which would have discarded precisely the
rows the query exists to find.

### R4 — a test that passed for a reason unrelated to its claim, twice

The carryover assertion was vacuous: the day-two fixture left the worker idle, so it asserted over
an empty set. The operator's first repair made the set non-empty but **still could not detect the
regression** — a paused carryover can only ever attach to an `IN_PAUSE` block
(`_STEP_STATE_FOR_SHIFT`), and day two had none, so the guard was never consulted either way.

Closed by giving day two a genuine `IN_PAUSE` block, with the carryover left open. Mutation verified
in both directions against the real guard — the `current_shift_start` clause at
`get_worker_linear_timeline_breakdown.py:484`, **not** the window-overlap clause the operator
initially named.

## Reversibility — the plan was contradicted, correctly

The plan called the migration irreversible. The implementer kept `ended_shift_collapse_journal` and
ran a full `downgrade` → `upgrade` round trip. That is the right call under
`architecture/30_migrations.md`: unlike the transition-reason journal, whose rows all shared one
constant, this one holds genuinely **per-row** information across three row shapes with different
previous states.

E2's reporting change is still not undone by it — the journal only means the rows can be put back.
**Nothing drops the journal**, so it lives in production indefinitely; that is a later decision, not
a defect.

## Validation

23 failed / 1453 passed, failure node set byte-identical to baseline at the same run index. `ruff`
clean on touched files; the 5 findings in `transition_step_state.py` are pre-existing (T8).
Criterion 9 verified against the journal rather than a count: 0 worker-picked rows typed as a system
transition, 0 that lost their `pause_reason_id`. E2 row 3 — zero instances locally — proven by
constructed rehearsal, and it is the shape the server holds most of.

## For the deployer

The server is at `d8e4f1a2c6b7`. This is **eight** migrations spanning three feature sets, none
deployed. `alembic upgrade head` runs the lot — no flags, no explicit targets.

Two windows, both stated in the plan's deployment section: `deploy.yml` runs migrations **before**
`systemctl restart`, so seven pre-restart query sites raise on the removed enum member until the
restart completes; and `_recreate_enum` rewrites both `step_state_records` and `task_steps` under
`ACCESS EXCLUSIVE`, rebuilding **21** indexes. That table rewrite, not the 208 reclassified rows,
sets the window length.
