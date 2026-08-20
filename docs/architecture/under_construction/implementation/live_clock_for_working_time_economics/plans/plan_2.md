# Plan 2 — the three surfaces go live (one loader run, one `now`, per request)

```
state: NOT_STARTED
phase: 2
date: 2026-08-20
depends_on: plan 1 APPROVED 2026-08-20 (`d21fe9e`) — holds
```

**What phase 1 shipped, that this phase consumes** (facts, verified at approval):

- `live_worked_seconds.py:load_live_worked_seconds(session, workspace_id, steps, now)
  -> dict[str, int]` — keyed by step `client_id`, every input step present, values
  `settled + int(round(open_share))`. Raises `TypeError("load_live_worked_seconds
  requires an aware UTC now")` on a naive `now`: it **fails closed at its own
  boundary**, and that guard is load-bearing (intention §1A HC-3A round 4d).
- `context.py:ServiceContext.now` — aware UTC, stamped once per construction,
  overridable by `now=`. Every service in this phase reads `ctx.now`; no service
  reads a clock.
- Three golden files + `test_live_clock_goldens.py` under
  `app/tests/integration/services/queries/item_economics/` — captured **before** any
  live code existed. They are this phase's payload-freeze proof (C1).

## 1. Goal

Wire `load_live_worked_seconds` into E-P, E-B (both faces) and E-A so every
worked-seconds-derived field on the three payloads derives from one loader run and one
`ctx.now` per request (HC-5, §4.1A D), and delete the E-B SQL aggregate in favour of
the per-step fold (decision N-2). All four §4.1 surface rows ship together (D5).

**NOT in this phase:** no change to `budget_division.py`, `concurrency.py`,
`averaged_time.py`, the router, any serializer's key set, or the two frozen-percent
feed sites — `final.percent_consumed` and the worker face's `result.percent_consumed`
keep today's request-level wiring until phase 3 (D9). No handoff (phase 4).

## 2. Read first

1. `master_plan.md` §4 (N-1…N-4), §5 — **including the nine rules earned in phase 1**,
   which bind here — and §6 (the four-caller table fact; the baseline **26 / 2459 / 1**
   with its enumerated ID set; the third-flake and `TZ` environment facts).
1b. `plans/plan_1.md` §5 (C9 and C11/C12 as amended — the shapes this phase's criteria
   are modelled on), §6's structural-facts note, and §7's Review log: six rounds of
   findings, every blocking one in a plan or review artifact rather than in code.
2. Intention §1A (HC-1A, HC-3A scope — E-A's `today_utc()`), §4.1 + §4.1A (the field
   table, the fold, the composition contract and per-caller declaration table), §4.2,
   §4.3 + §4.3A (the three allowance paths — path 3 is the expensive mistake), §2.6
   (the price-scenario coupling), §5.2 (the frontend's four criteria, adopted as
   contract), §9A (T1′ row b, T5–T9, T11, T12).
3. Source: the three services + `get_task_budget_status_worker.py`,
   `division_serializers.py`, `serializers.py:serialize_task_budget_status`,
   `get_task_price_scenario.py` (read — its call is in your blast radius),
   `budget_division.py:DivisionStep`, `_step_transition_core.py:_apply_step_transition`
   (T11's close path).

## 3. Files expected to change

- `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py` — the
  fold (N-2): `_build_evaluated_status` loads the task's **non-deleted steps** (no
  state filter — §4.1A A population check), obtains the live map, and computes
  `actual_seconds = Σ live map`; the `func.sum` aggregate is **deleted**. Signature
  per §4.1A D: `get_task_budget_status(ctx, *, live_seconds: Mapping[str, int] | None
  = None)` — `None` means "compute the map yourself from `ctx.now`", never "skip";
  same optional threading through `_build_evaluated_status`.
- `app/beyo_manager/services/queries/item_economics/get_task_production_time.py` —
  resolves the live map **once** over its loaded steps, passes it into
  `get_task_budget_status(ctx, live_seconds=…)`, and hands the allocator
  `DivisionStep` rows carrying the live figures (HC-1A: built, never assigned onto
  ORM steps).
- `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py` —
  one loader call **per batch** keyed over all visible tasks' steps (the per-user
  sweep is shared across tasks — §3.4A B); `DivisionStep` substitution per task;
  headline `actual_seconds` from the map; `today_utc()` → `ctx.now.date()` resolved
  **once before the loop** (HC-3A scope).
- `app/beyo_manager/services/queries/item_economics/get_task_budget_status_worker.py` —
  only if the `_build_evaluated_status` threading requires a call-site change; expected
  unchanged (it inherits the fold).
- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`
  — **additive only** (round 4b, projection r0 / intention HC-3A):
  `typical_times_statement` gains a `now: datetime | None = None` parameter; `None`
  preserves the existing `datetime.now(timezone.utc)` cutoff read (the compatibility
  shim for callers outside this pipeline — the working-sections surface and the
  price-scenario typical block, both settled-basis and out of scope, whose behaviour
  and suites must be untouched); E-P and E-A pass `ctx.now`. No other change to this
  file — its aggregates and grouping are path 3 of §4.3A and stay settled.
- New/extended test files under
  `app/tests/integration/services/queries/item_economics/` for C1–C11 below; the
  price-scenario suite (`test_price_scenario*.py`) **only if** C10 finds it red —
  fixed-`ctx.now` fixture additions and nothing else in it.

## 4. Ordered tasks

1. The fold in `_build_evaluated_status` (N-2), with the loader threading (§4.1A D
   caller table: E-B route resolves its own; worker face inherits; E-P passes its map;
   price scenario resolves its own **by not changing** — `ctx.now` exists for it).
2. E-P: one map, both consumers (status + division rows).
3. E-A: batch probe, per-user sweeps shared across tasks, headline from the map,
   `today_utc()` replacement.
4. The typicals cutoff under `ctx.now` (intention HC-3A round 4b): the additive
   parameter and the two call sites (E-P's `typical_times_statement(...)` call and
   E-A's `_load_typicals`).
5. Tests C1–C11, mutation ledger per master plan §5.

## 5. Acceptance criteria

- **C1 — T5 goldens stay green, untouched.** The three golden files from plan 1 are
  byte-identical assertions against the live code — **the golden files and their test
  are read-only in this phase's diff** (any edit to them is an automatic review
  finding). This is §5.2 criterion 4.
- **C2 — the motivating card** (§5.2 criterion 1, §1): a section 25 minutes into a
  3 m 6 s allowance with an open working record reports `share_state: "over_share"`
  with `worked_seconds` and `left_seconds` consistent in the same payload (exact
  expected integers in the test, derived from the fixture).
- **C3 — T6 coherence** (§5.2 criterion 3, HC-5): one open record;
  `budget.actual_worker_seconds == Σ sections[].worked_seconds`; per row
  `left_seconds == allowance_seconds − worked_seconds`; `share_state` consistent with
  the figures beside it. Plus the population row: a task carrying one `SKIPPED` step —
  headline still equals the fold over **all** non-deleted steps (§4.1A A).
- **C4 — T1′ row b (call sites, one per endpoint):** with `ctx.now` frozen and the
  loader's clock-stub in place, serving each endpoint twice yields byte-identical
  payloads and **loader invocations == 1 per request** (E-P's composition included —
  this is the §4.1A D double-computation guard). **Named mutation, per endpoint at the
  call site:** E-P passing `live_seconds=None` instead of its map ⇒ invocation count 2
  ⇒ red; E-A restoring `today_utc()` inside the loop ⇒ its determinism row red.
- **C5 — T9 (HC-1A), three rows:** serve each endpoint against a task with an open
  working record; re-read `task_steps.total_working_seconds` in a fresh session ⇒
  unchanged. **Named mutation (loader call site in each service):** assign the live
  figure onto `step.total_working_seconds` before division ⇒ column re-read `600` not
  `0` ⇒ red (§9A T9's both sides).
- **C6 — T12 allowances:** one payload with an open working record: every
  `allowance_seconds` (sections and steps) byte-identical to the settled payload's;
  honest-form rows per §9A T12 — no excluded step in the fixture has an open working
  record (assert), `charged_seconds` computed from settled values (assert on the
  division input). `typical` blocks byte-identical (path 3, §4.3A).
- **C7 — T7 worker face:** the worker/seller serializer carries no monetary key while
  its time fields are live — the existing key-walk family extended by one
  live-state row; the live time fields equal the manager face's for the same fixture
  (D5 — no split-brain).
- **C8 — T8 cost shape:** one active worker across N batched tasks ⇒ exactly one
  open-record probe statement and one `compute_record_contributions` call
  (`count_queries` / call counting, never wall-clock); two workers ⇒ two calls. The
  50-task ceiling **measurement** is a Review-log obligation, not a criterion
  (charter rule 1; §9A T8) — record it there with the fixture shape.
- **C9 — T11 settlement window observed** (D8): open record → read E-P → close through
  the production transition **without** running the analytics worker → read E-P again
  ⇒ `worked_seconds` equals the pre-work settled value (the drop exists); then run
  `_recompute_step_time_totals` ⇒ value returns within ≤ 1 s per step (§3.3A).
- **C10 — the price-scenario blast radius** (§2.6): the full existing price-scenario
  suite green at this phase's head; if any test is time-dependent under the live
  `_build_evaluated_status`, the fix is a frozen `ctx.now` in its fixtures — never a
  change to the shipped service file. Review log records which of the two outcomes
  happened.
- **C11 — the typicals cutoff reads no clock on E-P/E-A** (intention HC-3A round 4b):
  with `beyo_manager.services.queries.working_sections.get_working_section_typical_times`'s
  module clock stubbed, serving E-P and E-A performs **zero** clock reads in that
  module (stub call-count == 0). **Named mutation, one per call site:** drop the
  `now` argument at E-P's call ⇒ the statement falls back to the defaulted clock read
  ⇒ stub intercepted ⇒ that row red; same for E-A's `_load_typicals` call. Both sides:
  contract stub-count 0/0, mutation ≥ 1 at the mutated site. Plus one
  behaviour-preservation row: `typical_times_statement()` called with no argument
  (the outside-pipeline form) produces the same rows as before this phase for the
  same fixture — the shim is inert.

## 6. Notes

- **Path 3 warning verbatim** (§4.3A): `typicals_by_section` must never be fed live
  figures — a live typical moves every allowance on the payload. The loader's output
  goes to step rows and headline only.
- `_build_evaluated_status`'s step load and E-P's existing step load are **two loads
  in one E-P request** — acceptable (they serve different needs; the *live map* is
  computed once, which is what HC-5 contracts). If the implementer consolidates, the
  consolidation must not change E-B-standalone's behaviour; either outcome is recorded
  in the Review log.
- Inherited hazards: the two flaky tests (master plan §6); repeat + ID-diff before any
  conclusion. Parallel sessions share a baseline — none run in parallel with this one.

## 7. Review log

(empty — append-only)
