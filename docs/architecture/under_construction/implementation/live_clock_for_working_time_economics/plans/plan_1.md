# Plan 1 — the pre-change goldens, the clock boundary, and the live loader

```
state: NOT_STARTED
phase: 1
date: 2026-08-20
depends_on: mechanism-inventory gate PASSED (round 4a) — holds
```

## 1. Goal

Ship the two foundations every surface change stands on, while **no payload changes
byte-one**: (a) the T5 golden files, captured and committed while all three endpoints
are still settled-only; (b) the request-clock boundary (`ServiceContext.now`, decision
N-1); (c) the shared live loader `load_live_worked_seconds` (decision N-3) with its
full contract proven at loader level.

**NOT in this phase:** no endpoint, service, or serializer changes — E-P/E-B/E-A
payloads are byte-identical to `348a09f` throughout (that is criterion C1). No
`_build_evaluated_status` change (phase 2). No D9 work (phase 3). No handoff (phase 4).

## 2. Read first

1. `master_plan.md` §4 (decisions N-1…N-4), §5, §6.
2. Intention §1A (HC-1A, HC-3A), §3.1 + §3.1A (the M1 contract — your task list for the
   loader), §3.2 + §3.2A (the four cases with preconditions; the window derivation),
   §3.3 + §3.3A (the parity bound: ≤ 1 s **per step**), §9A (T1′–T5, T10).
3. Source: `averaged_time.py:compute_record_contributions` (the wrapper you call),
   `concurrency.py:averaged_seconds_by_record` (read, never modify — HC-2),
   `process_step_transition.py:_recompute_step_time_totals` (the settlement side of T2),
   `step_state_record.py:StepStateRecord` (`uix_step_state_records_active`),
   `context.py:ServiceContext`, `budget_division.py:DivisionStep`.

## 3. Files expected to change

- `app/beyo_manager/services/context.py` — the `now` field (N-1). **Nothing else in
  this file.**
- `app/beyo_manager/services/queries/item_economics/live_worked_seconds.py` — **new**,
  the loader (N-3).
- `app/tests/integration/services/queries/item_economics/test_live_worked_seconds.py` —
  **new**, C3–C10.
- `app/tests/integration/services/queries/item_economics/goldens/` — **new**, three
  golden JSON files + `app/tests/integration/services/queries/item_economics/test_live_clock_goldens.py` (C2).
- No other file. `concurrency.py`, `averaged_time.py`, `budget_division.py` and every
  service file are **read-only** this phase.

## 4. Ordered tasks

1. **T5 golden capture — FIRST, before any code change** (intention §9 T5, finding 5's
   sequencing). Build the deterministic golden fixture set (fixed client_ids, fixed
   timestamps, committed evaluation): (a) an idle task with settled work and **no**
   result row; (b) a task with a persisted `ItemCostResult` and **zero post-freeze
   drift** (settled figures unchanged since `computed_at`, current evaluation ==
   `result.evaluation_id`) — this fixture must NOT straddle the D9-divergence state,
   and the golden test's docstring says why (phase 3 changes the frozen-percent
   *source*; in the no-drift state old and new sources are value-identical, so these
   goldens survive D9 — a drift fixture would not); (c) steps whose open records are
   `PENDING` (§9A T5: proves the state filter, not record absence). Serialize,
   with `json.dumps(payload, sort_keys=True, separators=(",", ":"))`, the
   following payload set — three golden files, one per endpoint, each a JSON object
   with the two task keys `idle_no_result` (fixture a) and `frozen_no_drift`
   (fixture b):

   - `golden_production_time.json` — per task, the return of
     `get_task_production_time(ctx)`.
   - `golden_budget_status.json` — per task, an object
     `{"manager": serialize_task_budget_status(get_task_budget_status(ctx), include_monetary=True),
     "worker": serialize_task_budget_status(get_task_budget_status_worker(ctx), include_monetary=False)}`
     — both faces captured, because phase 2 changes both and phase 3 (D9) rewires the
     worker face's `result.percent_consumed`; each face's golden is the byte-freeze at
     its own serialization site.
   - `golden_budget_allocations.json` — per task, the return of
     `get_task_budget_allocations(ctx)` called with `task_ids` of exactly that one
     task. Never one batched two-task call:
     `get_task_budget_allocations.py:get_task_budget_allocations` selects its tasks
     with no `ORDER BY`, so a multi-task response's row order is database-dependent
     and a byte golden over it is fixture luck.

   Fixture (c) applies to both tasks: every step of (a) and (b) holds an open
   `PENDING` record.

   Typicals stability: `get_working_section_typical_times.py:typical_times_statement`
   computes `cutoff = datetime.now(timezone.utc) − TYPICAL_WINDOW_DAYS` at statement
   build, and both `sample_count` and `typical_worker_seconds` are filtered by
   `latest_closed_at >= cutoff` — a wall-clock read on the E-P and E-A request paths.
   The golden fixture must make the typicals block time-invariant by construction: no
   fixture step is `COMPLETED` and every fixture step's `closed_at` is `NULL`, so
   `sample_count == 0` and `typical_worker_seconds` is `None` on every section at any
   future run date. The golden test's docstring records this constraint and why.

   Write the assert test that replays the fixtures and compares byte-for-byte.
   **Commit the goldens + test in the phase's first checkpoint commit and record the
   hash in the Review log** — a golden added after any surface change is a gate
   failure, not a test.
2. **`ServiceContext.now` (N-1).** `now: datetime = field(default_factory=lambda:
   datetime.now(timezone.utc))` — tz-aware UTC, stamped once at construction (the
   service boundary), overridable by passing `now=`. Extend the class docstring's
   Rules block: `now` is request data like `incoming_data`, read by services instead
   of any clock; the "never add boolean flags or config values" rule stands and this
   is neither.
3. **The loader (N-3).** `live_worked_seconds.py`:
   `async def load_live_worked_seconds(session, workspace_id: str, steps:
   Sequence[TaskStep], now: datetime) -> dict[str, int]`, implementing intention §3.1
   as contracted by §3.1A, exactly:
   - one batched open-record probe over the given steps' ids (`exited_at IS NULL`,
     `state == WORKING`, `is_deleted IS FALSE`) — one SQL statement (§3.4A A);
   - distinct users via `COALESCE(credited_user_id, created_by_id)`, skipping
     both-NULL records (§3.1A D);
   - per user: `W_start = min(entered_at) over that user's probed records − 1 day`
     (§3.2A: the anchor is load-bearing, the buffer is slack), one
     `compute_record_contributions(session, workspace_id, u, W_start, now, now)` call;
   - filter returned rows to `is_open AND state == "working" AND record_id ∈ probe
     set`; per step: `settled + int(round(share))` (§3.1A A — round the **share**,
     never the sum; Python `round`, half-even);
   - every input step keyed in the output; steps with no open working record map to
     their settled column as `int`; output values are `int` (§3.1A B);
   - **no assignment to any ORM attribute, ever** (HC-1A).
4. Tests C3–C10 below, with the mutation ledger per master plan §5 (both sides
   computed, whole suite, ID sets diffed, sites named, probes reverted hash-verified).

## 5. Acceptance criteria

Every criterion is an automated test in this phase's files unless marked otherwise.

- **C1 — nothing changed.** Full suite: baseline 26 failed / +new passed / 1
  deselected, failure IDs byte-identical to `master_plan.md` §6's set; golden test
  green on the unchanged endpoints. (The golden test IS the payload-freeze proof.)
- **C2 — goldens.** Three golden files exist **per task 1's composition** (two task
  keys each; E-B both faces at their own serialization sites; E-A one single-task
  call per task, never batched); the assert test replays the fixtures and compares
  full payloads byte-for-byte; the capture commit precedes every other change of this
  pipeline's phases (Review log records the checkpoint hash). Fixture (c)'s
  open-`PENDING` records present; task 1's typicals-invariance constraint holds (no
  `COMPLETED` fixture step, every `closed_at` NULL) and the golden test's docstring
  records it.
- **C3 — the four §3.2 rows** (T3), expected values from §3.2A: row 1 two workers/two
  users ⇒ 1800+1800 (fixture reason: **distinct** credited users, its only reason for
  3600; both steps `allows_batch_working=True` — with the flag off, a same-user
  counterfactual still reads 1800+1800 (non-batch intervals never divide,
  `concurrency.py:averaged_seconds_by_record`) and the distinct-users predicate stops
  being the reason the number holds; with the flag on, the counterfactual reads
  900+900. Contract 1800/1800, counterfactual 900/900); rows 2–4 with
  `allows_batch_working=True` on every participating step (§3.2A precondition):
  1500/300; cross-task halving with row 3's durations and expected integers delegated
  (D1, §6); 1200. One row each; each fixture's predicate the only reason its number
  holds.
- **C4 — exclusions** (T4): open `PAUSED` ⇒ 0 live term; record flag alone ⇒ 0; step
  flag alone ⇒ 0 **and** the same-worker sibling step's live figure **rises** (§6A
  E3 — both assertions in the step-flag row); `is_deleted` record ⇒ 0 (docstring: no
  shipped writer, defense-in-depth, §3.1A D); zero-cases `entered_at >= now` ⇒ 0 and
  both-attribution-NULL ⇒ skipped (§3.1A D).
- **C5 — T2 parity, both rows** (§9A): batch row (case-2 shape) and single-open-record
  row; compute live at `t`, close by calling
  `_step_transition_core.py:_apply_step_transition` with `now=t` (passing ctx, step,
  task, the open record as `closing_record`, `new_state=TaskStepStateEnum.PAUSED`,
  `credited_user_id` of the fixture worker, `pause_reason_id=None`,
  `transition_reason=None`) — the shared core both shipped commands route through,
  and the only production entry that accepts the pinned clock
  (`transition_step_state.py:transition_step_state` stamps its own
  `datetime.now(timezone.utc)` internally and cannot close "at t" against fixed
  fixture timestamps) — then run
  `_recompute_step_time_totals` directly, assert `|live − column| ≤ 1` **per step**
  (§3.3A B — never a per-user tolerance). Fixtures commit ⇒ own `try/finally`
  teardown (charter 11½). Single-row precondition: that worker holds **no other open
  interval anywhere** (§9A). **Named mutation (call site, this loader, not
  `concurrency.py`):** sweep call → `now − entered_at`: batch row `1500→1800` red,
  single row `1800→1800` green — recorded per row, whole-suite.
- **C6 — T10 / deleted-step divisor:** a deleted step's open batch record still halves
  the live sibling (§3.1A F); the deleted step itself absent from the loader output
  (input steps are non-deleted by contract).
- **C7 — the window anchor:** one worker, two open batch records with different
  `entered_at`, plus a closed record overlapping only the earlier one's first segments
  (case-4 shape): correct shares require `W_start` anchored at `min(entered_at)`.
  **Named mutation (definition site, the window computation):** anchor at
  `max(entered_at)` — this row's expected values shift and it reddens; compute both
  sides in the ledger. Fixture constraint the mutation depends on: the closed
  record's `exited_at` must precede `max(entered_at) − 1 day` (i.e., the two open
  records' `entered_at` sit more than a day plus the overlap apart), or the 1-day
  buffer swallows the `max(entered_at)` anchor and the mutation cannot redden.
  Operationally such an old open record cannot exist (§3.2 window note); the fixture
  inserts rows directly and the database permits it — correctness must not hang on
  the scheduler.
- **C8 — determinism / T1′ row a (definition site):** loader called twice with the
  same `now` over unchanged state returns equal dicts; with the module's clock stubbed
  to advance +5 s per call, output is unchanged (stub call-count == 0 — the loader
  reads no clock). **Named mutation:** insert a `datetime.now(timezone.utc)` read into
  the loader ⇒ stub row reddens (`600` vs `605` per §9A T1′).
- **C9 — `ServiceContext.now`:** aware-UTC type row; explicit `now=` honored;
  default-stamp row: monkeypatch `beyo_manager.services.context.datetime` (the module
  global the `default_factory` lambda resolves at call time) with a stub whose
  `now(tz)` returns `T0` then `T0 + 1s` on successive calls; two default
  constructions carry `now == T0` and `now == T0 + 1s` respectively — proving the
  stamp is evaluated per construction, at construction time, never shared as a class
  default. (Two unstubbed back-to-back constructions can legally collide at
  microsecond resolution; "distinct stamps" is not a property the mechanism
  guarantees, and the unstubbed form flakes.) A naive `now` handed to the loader
  **fails closed at the loader's own boundary** with `TypeError` (§1A HC-3A as
  amended round 4c — the sweep cannot raise on this driver; the un-guarded
  behaviour is a silently vanished live term). The test is named for the boundary,
  its docstring records why the sweep site cannot fire (the 0-rows naive-bind
  observation), and the **named mutation** is: delete the boundary guard
  (definition site) ⇒ exactly this row reds, whole-suite.
- **C11 — the settled term is load-bearing** (added at review r1, finding B1 — the
  identity-element rule, master plan §5). Two rows with `settled != 0`: (a) a step
  with a non-zero settled column **and** an open working record, asserting exactly
  `settled + share`; (b) a step with a non-zero settled column and **no** open
  record, asserting exactly the settled value. **Named mutation (definition site,
  the returned comprehension):** drop the settled term
  (`settled_seconds + live_by_step.get(step_id, 0)` → `live_by_step.get(step_id,
  0)`) ⇒ both rows redden — both sides computed per row, whole-suite, ID sets
  recorded. (Measured before the fix: this mutation's added set was **∅**.)
- **C12 — the output type and the rounding locus discriminate** (added at review
  r1, finding B2). (a) A type row: `assert all(isinstance(v, int) for v in
  result.values())` — `==` cannot express this (`1800.0 == 1800`). (b) A
  half-second locus row: one worker, two batch steps opened together, elapsed an
  **odd** second count at the fixed `now`, so each share is exactly `x.5`;
  asserted as the **half-even** integer (exact literal). **Named mutations:**
  return the raw float (`+= contribution.seconds`, definition site) ⇒ the type row
  reddens (and (b)'s value moves); `int(math.floor(x + 0.5))` in place of
  `int(round(x))` ⇒ the half-second row reddens while the type row stays green —
  recorded per row, whole-suite. (Measured before the fix: dropping `int(round)`
  added **∅**.)
- **C10 — HC-1A at loader level:** after `load_live_worked_seconds` over a step with
  an open record, assert in this order: (1) `session.dirty` contains no `TaskStep` —
  before any expire, because `Session.expire_all()` discards un-flushed attribute
  changes and an expire-first ordering passes under the very assignment this row
  exists to catch; then (2) `session.expire_all()`; then (3) re-read
  `total_working_seconds` from the DB and assert it is unchanged. (Endpoint-level T9
  is phase 2.)

## 6. Notes

### Delegations granted in writing (projection r0, 2026-08-20)

- **D1 — C3 row 3:** the interval durations and the resulting expected integers are
  the implementer's choice, recorded in the test beside the row. The shape is not:
  one worker, two open batchable records on steps of two different tasks, loader
  called over task 1's steps only, expected value = the halved share per §3.2A
  case 3.
- **D2 — golden capture mechanism:** the implementer chooses between (i) a
  regeneration branch inside `test_live_clock_goldens.py` gated on an env flag the
  committed test never sets, or (ii) a throwaway capture script that is never
  committed. Constraints either way: the goldens plus assert test land in the phase's
  first checkpoint commit (C2), and no dead scaffolding ships (charter rule 4).
- **D3 — golden fixture persistence:** golden fixtures are flush-only on the
  rollback-scoped `db_session` fixture (`tests/conftest.py:db_session`) — never
  committed — so their fixed client_ids cannot collide with committed residue across
  runs. C5's committing fixtures keep the `try/finally` teardown the plan already
  requires.

- The wrapper returns `seconds: float` with `.get(record_id, 0.0)` (§3.1A C) — a
  missing key is never an error; do not "harden" it.
- `int(round(·))` is Python's half-even; do not reach for `Decimal` or `math.floor(x
  + 0.5)` (§3.1A A — the difference is exactly the §3.3 bound's width).
- The `state == "working"` filter is against the **bucket key** the wrapper emits,
  not the raw column (§3.1A C); it is kept even though `ended_shift` requires
  `PAUSED` — a type-level assertion, documented as such.
- Inherited tripwires: the two flaky tests in master plan §6 — a count disagreeing
  with baseline is repeated and ID-diffed, never read from one run.

## 7. Review log

- **2026-08-20 — projection r0 consumed (coordinator).** Verdict AMENDMENTS_REQUIRED,
  0 owner cards, 12 ledger rows: 8 plan amendments applied verbatim (A1/A2 golden
  composition + typicals invariance, A5 the `_apply_step_transition` close path, A6
  the stubbed default-stamp row, A7 C10's assertion order, A8 C3 row 1's batch flag,
  A9 C7's separation constraint), 1 routed upstream (L3 — the typicals cutoff clock
  read, folded into intention §2.3A/HC-3A and plan 2), 3 delegations recorded in §6
  (D1–D3). Coordinator verified L3/L5/L4 at source before applying; baseline
  re-measured at `2711b58`: 26 failed / 2436 passed / 1 deselected, ID set enumerated
  in master plan §6. Handoff:
  `handoffs/reviewer/2026-08-20_phase1_projection_r0_handoff.md`.

- **2026-08-20 — phase 1 implementation completed (Codex).** Shipped the
  pre-change T5 goldens and byte-replay assertion at checkpoint `1081a2b`, added
  `ServiceContext.now`, and implemented `load_live_worked_seconds` with the batched
  open-WORKING probe, credited-user grouping, minimum-entry one-day-buffered window,
  shared analytics contribution wrapper, per-share Python rounding, and no ORM
  assignment. Added the loader-level C3–C10 integration rows; D1 chose two overlapping
  30-minute cross-task records for row 3 (900 seconds per step), D2 used a throwaway
  capture script outside the repository, and D3 kept golden fixtures flush-only on the
  rollback-scoped session. The naive-clock contract is enforced at the loader boundary
  with the specified `TypeError`; this preserves the loud contract under the configured
  asyncpg driver's timestamp normalization. Final suite: **26 failed / 2454 passed /
  1 deselected**, with the complete 26-ID failure set unchanged from master §6.
  Named mutation ledger (each whole-suite run; `B` means exactly the 26 IDs enumerated
  in master §6; all rows reverted to loader hash
  `6d11b922fbec3031be49adf1313b6d1685bef95659caf81f2b6cb7e918fa82ca`):

  | mutation / site | observed red set, expressed as `B ∪ Δ` | revert hash |
  |---|---|---|
  | naive `now - entered_at` replacing the wrapper call, loader call site | `B ∪ {test_live_worked_seconds.py::test_c3_row_2_sweep_changes_divisor_mid_interval, test_c3_row_3_cross_task_open_record_is_in_the_divisor, test_c3_row_4_closed_overlap_shapes_the_open_record_share, test_c4_record_marked_wrong_has_no_live_term, test_c4_step_marked_wrong_drops_it_and_releases_sibling_share, test_c5_t2_batch_row_rejoins_settlement_within_one_second, test_c6_deleted_step_still_divides_live_sibling, test_c7_window_anchors_at_minimum_open_entry}` | `6d11b922…fa82ca` |
  | anchor `max(entered_at)` replacing `min(entered_at)`, loader window definition | `B ∪ {test_live_worked_seconds.py::test_c7_window_anchors_at_minimum_open_entry}` | `6d11b922…fa82ca` |
  | inserted `datetime.now(now.tzinfo)` and used it as the sweep timestamp, loader definition | `B ∪ {test_live_worked_seconds.py::test_c3_row_1_distinct_workers_are_not_divided_by_section_records, test_c3_row_2_sweep_changes_divisor_mid_interval, test_c3_row_3_cross_task_open_record_is_in_the_divisor, test_c3_row_4_closed_overlap_shapes_the_open_record_share, test_c4_step_marked_wrong_drops_it_and_releases_sibling_share, test_c4_zero_cases_future_entry_and_missing_attribution_are_skipped, test_c5_t2_batch_row_rejoins_settlement_within_one_second, test_c5_t2_single_open_record_rejoins_settlement_within_one_second, test_c6_deleted_step_still_divides_live_sibling, test_c7_window_anchors_at_minimum_open_entry, test_c8_loader_is_deterministic_and_does_not_read_its_module_clock, test_c10_loader_never_persists_live_seconds_on_task_step}` | `6d11b922…fa82ca` |

  Implementation checkpoint: `a7659bc`. Architecture graph delta is one additive
  batch: inferred `Live worked-seconds loader` projection with `reads_from
  step_state_records` and `calls compute_record_contributions`; no review item was
  promoted, rejected, edited, or removed.

- **2026-08-20 — implementation consumed (coordinator), verified independently.**
  Perimeter: `git diff --name-only 08fc141..HEAD` equals the declared 10 items
  exactly. Goldens-first proven from the checkpoint itself: `1081a2b` contains only
  the three goldens + their test. Clean suite re-run: **26 / 2454 / 1**, failure IDs
  byte-identical to master plan §6's set. **All three named mutations re-applied by
  the coordinator, whole-suite, reverted, hash-verified (`6d11b922…fa82ca`)**:
  mutation 1 (naive elapsed, call site) added exactly the ledger's 8 IDs; mutation 2
  (`max(entered_at)` anchor) exactly its 1. **Mutation 3 required a repeat in a
  second shape**: with the inserted clock read used *only* as the sweep timestamp —
  the ledger row's literal description — the added set is **11** (the
  `zero_cases` test stays green, because the fixture-`now` window fetch still
  excludes the future-entry record); with the clock read used as **both** window-end
  and sweep timestamp, the added set is exactly the ledger's **12**. The
  implementer's observation was true and their mutant was the both-args shape; the
  row's site description under-stated it. Recorded here per rule 11 (a named
  mutation names where it is applied — and, this proves, *how far* it reaches):
  future ledger rows for multi-use arguments state which uses the mutation covers.
  Consumption flags routed to review r1 as probes P1–P7 (headline: the naive-`now`
  boundary guard is a sound but unplanned semantic addition whose justification
  needs reconciling and whose own deletion may leave every test green).

- **2026-08-20 — phase 1 fix cycle completed (Codex, round 2).** Resolved review
  findings B1/B2 and S1/S2, plus notes N1/N3/N7, entirely in
  `test_live_worked_seconds.py`; no production file or Architecture Graph state
  changed. B1 now has two isolated non-zero-settled rows: one asserts
  `settled + share`, and one asserts settled-only with no open record. B2 now has
  an explicit `isinstance(value, int)` row and an odd-second two-way batch row
  whose exact 30.5-second shares assert Python half-even `30`. S1 was renamed to
  `test_c9_naive_now_fails_closed_at_the_loader_boundary` and its docstring records
  the configured driver's 0-row naive-bind observation under HC-3A/plan C9. S2's
  deleted-record row names `reset/phases/delete_step_state_records.py` as the
  only hard-DELETE writer. N1 records the two zero-case mutation halves, N3 pins
  the second C7 value at 1800, and N7 records D1's two overlapping 30-minute
  cross-task choice in the test comment.

  Clean focused verification: **22 passed**; Ruff: **all checks passed**. Final
  whole non-e2e suite: **26 failed / 2458 passed / 1 deselected / 2 warnings**;
  the complete 26-ID failure set is byte-identical to master §6. The test-only
  checkpoint is `a4f5b97`.

  Required mutation ledger (each row was applied at the named definition site,
  measured with the whole non-e2e suite, then reverted and hash-verified). `B`
  means exactly the 26 IDs enumerated in master §6; the restored production-file
  hash for every row is
  `6d11b922fbec3031be49adf1313b6d1685bef95659caf81f2b6cb7e918fa82ca`.

  | mutation / site | observed result |
  |---|---|
  | Drop `settled_seconds +` from the returned comprehension, `live_worked_seconds.py:load_live_worked_seconds` definition site | **28 failed / 2456 passed / 1 deselected** = `B ∪ {tests/integration/services/queries/item_economics/test_live_worked_seconds.py::test_c11_nonzero_settled_term_is_added_to_live_share, tests/integration/services/queries/item_economics/test_live_worked_seconds.py::test_c11_nonzero_settled_term_is_returned_without_open_record}` |
  | Return raw `contribution.seconds` instead of `int(round(...))`, `live_worked_seconds.py:load_live_worked_seconds` definition site | **28 failed / 2456 passed / 1 deselected** = `B ∪ {tests/integration/services/queries/item_economics/test_live_worked_seconds.py::test_c12_loader_output_values_are_ints, tests/integration/services/queries/item_economics/test_live_worked_seconds.py::test_c12_half_even_rounding_is_applied_to_each_half_second_share}` |
  | Replace `int(round(x))` with `int(math.floor(x + 0.5))`, `live_worked_seconds.py:load_live_worked_seconds` definition site | **27 failed / 2457 passed / 1 deselected** = `B ∪ {tests/integration/services/queries/item_economics/test_live_worked_seconds.py::test_c12_half_even_rounding_is_applied_to_each_half_second_share}`; the explicit type row stayed green, as required |
  | Delete the `now` awareness guard, `live_worked_seconds.py:load_live_worked_seconds` definition site | **27 failed / 2457 passed / 1 deselected** = `B ∪ {tests/integration/services/queries/item_economics/test_live_worked_seconds.py::test_c9_naive_now_fails_closed_at_the_loader_boundary}` |

  The mutation probes temporarily touched only
  `app/beyo_manager/services/queries/item_economics/live_worked_seconds.py`; it
  was restored byte-identically after each probe. No tracker update was made;
  that remains coordinator-owned.
