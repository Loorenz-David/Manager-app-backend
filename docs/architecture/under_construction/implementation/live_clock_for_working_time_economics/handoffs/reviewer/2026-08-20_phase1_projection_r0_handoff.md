---
plan: 1
role: projection
round: 0
verdict: AMENDMENTS_REQUIRED
date: 2026-08-20
actor: Claude Fable 5 (plan-projection, fresh session)
---

# Projection handoff — plan 1, round 0

## Opening (owner-readable)

I walked the implementer's first hour of plan 1 on paper, against the real code, and
the plan is close to implementable — nothing here needs a product decision from you,
and no question about how the feature should behave is open. What I found is a set of
text-level gaps the coordinator must fold in before the implementer starts: the
"frozen reference payloads" need precise construction rules or a hidden clock in the
typical-times query will silently expire them months from now; the pass/fail baseline
figures in the master plan went stale when the purchase-API commit landed after they
were measured; and a few test recipes as written could stay green under the exact
defect they exist to catch. All fixes are amendments to the plan documents, written
out verbatim below. Next: the coordinator applies them and compiles the implementer
prompt.

## ⚠ OWNER DECISIONS REQUIRED (0)

None — every ledger row routes to the coordinator as a plan amendment, an upstream
intention note, or a written delegation. Nothing needs the owner personally.

## Decision ledger

| # | Decision point | Classification | Routing |
|---|---|---|---|
| L1 | Golden payload composition: which task feeds which file, which E-B face(s), E-A request shape (its task `SELECT` has no `ORDER BY` — a two-task byte-golden is order-luck) | plan gap | amend plan_1 §4 task 1 + C2 (text A1) |
| L2 | `typical_times_statement` wall-clock cutoff makes goldens expire when any qualifying completed step ages out of the window | plan gap | amend plan_1 §4 task 1 (text A2) |
| L3 | Intention §2.3A's clock-read absence claim scoped its grep to `services/queries/item_economics/` and missed `get_working_section_typical_times.py:typical_times_statement` — a `datetime.now(timezone.utc)` read executing inside E-P and E-A requests | intention gap | route upstream (text A3); never patched downstream |
| L4 | C1's baseline reference: master plan §6's 26/2433/1 predates commit `6c15678` (test files added/changed), and §6 contains no enumerated failure-ID set for C1's "byte-identical" comparison | plan gap (master plan §6) | coordinator action (text A4) |
| L5 | C5's "close via the production transition path" is undetermined between `transition_step_state.py:transition_step_state` (stamps its own `datetime.now(timezone.utc)` — cannot close "at t") and `_step_transition_core.py:_apply_step_transition` (accepts `now=`) | plan gap | amend C5 (text A5); upstream citation nit included |
| L6 | C9's default-stamp row ("two constructions ⇒ non-decreasing distinct stamps") asserts a distinctness the mechanism does not guarantee — µs clock resolution vs sub-µs constructions; the row can flake | plan gap | amend C9 (text A6) |
| L7 | C10's written order (expire, then dirty-check) makes both assertions pass under the HC-1A assignment it exists to catch — `Session.expire_all()` discards un-flushed attribute changes | plan gap | amend C10 (text A7) |
| L8 | C3 row 1 omits `allows_batch_working=True`; without it, a same-user counterfactual still reads 1800+1800 and "distinct credited users" is not the reason the number holds (charter rule 2 companion) | plan gap | amend C3 (text A8) |
| L9 | C3 row 3's interval durations and resulting expected integers are unpinned (rows 2 and 4 carry 1500/300 and 1200; row 3 carries only "cross-task halving") | free choice | written delegation (text D1) |
| L10 | Golden capture mechanism (how the three files get written at capture time) | free choice | written delegation (text D2) |
| L11 | Golden fixture persistence discipline (fixed client_ids vs committed residue across runs) | free choice | written delegation (text D3) |
| L12 | C7's anchor mutation (`max(entered_at)`) is swallowed by the 1-day buffer unless the fixture separates the closed record's exit from the later anchor by more than one day — a naive same-day case-4 fixture leaves the mutation green | plan gap | amend C7 (text A9) |

### Verbatim-ready amendment texts

**A1 — plan_1 §4 task 1, replace the sentence beginning "Serialize all three endpoint
payloads" (and adjust C2's first clause to match):**

> Serialize, with `json.dumps(payload, sort_keys=True, separators=(",", ":"))`, the
> following payload set — three golden files, one per endpoint, each a JSON object
> with the two task keys `idle_no_result` (fixture a) and `frozen_no_drift`
> (fixture b):
>
> - `golden_production_time.json` — per task, the return of
>   `get_task_production_time(ctx)`.
> - `golden_budget_status.json` — per task, an object
>   `{"manager": serialize_task_budget_status(get_task_budget_status(ctx), include_monetary=True),
>   "worker": serialize_task_budget_status(get_task_budget_status_worker(ctx), include_monetary=False)}`
>   — both faces captured, because phase 2 changes both and phase 3 (D9) rewires the
>   worker face's `result.percent_consumed`; each face's golden is the byte-freeze at
>   its own serialization site.
> - `golden_budget_allocations.json` — per task, the return of
>   `get_task_budget_allocations(ctx)` called with `task_ids` of exactly that one
>   task. Never one batched two-task call:
>   `get_task_budget_allocations.py:get_task_budget_allocations` selects its tasks
>   with no `ORDER BY`, so a multi-task response's row order is database-dependent
>   and a byte golden over it is fixture luck.
>
> Fixture (c) applies to both tasks: every step of (a) and (b) holds an open
> `PENDING` record.

**A2 — plan_1 §4 task 1, append:**

> Typicals stability: `get_working_section_typical_times.py:typical_times_statement`
> computes `cutoff = datetime.now(timezone.utc) − TYPICAL_WINDOW_DAYS` at statement
> build, and both `sample_count` and `typical_worker_seconds` are filtered by
> `latest_closed_at >= cutoff` — a wall-clock read on the E-P and E-A request paths.
> The golden fixture must make the typicals block time-invariant by construction: no
> fixture step is `COMPLETED` and every fixture step's `closed_at` is `NULL`, so
> `sample_count == 0` and `typical_worker_seconds` is `None` on every section at any
> future run date. The golden test's docstring records this constraint and why.

**A3 — upstream, for the intention (home-artifact rule; coordinator folds):**

> §2.3A's search scope (`app/beyo_manager/services/queries/item_economics/`) missed a
> clock read on two of the three surfaces' request paths:
> `get_working_section_typical_times.py:typical_times_statement` (in
> `services/queries/working_sections/`, called by both E-P and E-A) derives its
> qualifying cutoff from `datetime.now(timezone.utc)`. The absence claim's own rule
> (master plan §5: scope AND term set) bites — the term set was right, the scope
> excluded a callee module. Consequences: (1) HC-3A's scope bullet ("what one clock
> read covers") should either bring this cutoff under the injected `now` in phase 2
> or record it as a known residual read; (2) T1/T1′'s byte-identity claim for E-P and
> E-A rests on that resolution; (3) master plan §6's carried fact
> ("`typical_times_statement`'s grouping subquery has no date predicate") is true of
> the subquery but incomplete about the statement — the outer qualifying filter is
> time-dependent. Also cosmetic: §3.3A C.1 and §6A cite
> `_step_transition_core.py:apply_step_transition`; the defined symbol is
> `_apply_step_transition`.

**A4 — coordinator action on master plan §6 (then C1 stands as worded):**

> Re-measure the full-suite baseline on a clean tree at the commit the implementer
> will start from (HEAD ≥ `2711b58`): commit `6c15678` landed after the §6
> measurement at `a0aaacc` and changed `app/beyo_manager/services/queries/items/lookup/`
> plus two test files under `app/tests/integration/services/queries/items/` (one of
> them new, +88 lines), so 26/2433/1 cannot be assumed. Record in §6 the re-measured
> counts AND the enumerated failure-ID set (or a committed file path that enumerates
> it) — C1 compares IDs against "§6's set", which §6 currently does not contain.

**A5 — plan_1 C5, replace "close via the production transition path" with:**

> close by calling `_step_transition_core.py:_apply_step_transition` with `now=t`
> (passing ctx, step, task, the open record as `closing_record`,
> `new_state=TaskStepStateEnum.PAUSED`, `credited_user_id` of the fixture worker,
> `pause_reason_id=None`, `transition_reason=None`) — the shared core both shipped
> commands route through, and the only production entry that accepts the pinned
> clock. `transition_step_state.py:transition_step_state` stamps its own
> `datetime.now(timezone.utc)` internally and cannot close "at t" against fixed
> fixture timestamps.

**A6 — plan_1 C9, replace the default-construction row with:**

> default-stamp row: monkeypatch `beyo_manager.services.context.datetime` (the module
> global the `default_factory` lambda resolves at call time) with a stub whose
> `now(tz)` returns `T0` then `T0 + 1s` on successive calls; two default
> constructions carry `now == T0` and `now == T0 + 1s` respectively — proving the
> stamp is evaluated per construction, at construction time, never shared as a class
> default. (Two unstubbed back-to-back constructions can legally collide at
> microsecond resolution; "distinct stamps" is not a property the mechanism
> guarantees, and the unstubbed form flakes.)

**A7 — plan_1 C10, replace the assertion sentence with:**

> after `load_live_worked_seconds` over a step with an open record, assert in this
> order: (1) `session.dirty` contains no `TaskStep` — before any expire, because
> `Session.expire_all()` discards un-flushed attribute changes and an expire-first
> ordering passes under the very assignment this row exists to catch; then
> (2) `session.expire_all()`; then (3) re-read `total_working_seconds` from the DB
> and assert it is unchanged.

**A8 — plan_1 C3 row 1, append after "its only reason for 3600":**

> ; both steps `allows_batch_working=True` — with the flag off, a same-user
> counterfactual still reads 1800+1800 (non-batch intervals never divide,
> `concurrency.py:averaged_seconds_by_record`) and the distinct-users predicate stops
> being the reason the number holds; with the flag on, the counterfactual reads
> 900+900. Contract 1800/1800, counterfactual 900/900.

**A9 — plan_1 C7, append:**

> Fixture constraint the mutation depends on: the closed record's `exited_at` must
> precede `max(entered_at) − 1 day` (i.e., the two open records' `entered_at` sit
> more than a day plus the overlap apart), or the 1-day buffer swallows the
> `max(entered_at)` anchor and the mutation cannot redden. Operationally such an old
> open record cannot exist (§3.2 window note); the fixture inserts rows directly and
> the database permits it — correctness must not hang on the scheduler.

### Written delegations (free choices, granted on purpose)

**D1 — C3 row 3:** the interval durations and the resulting expected integers are
the implementer's choice, recorded in the test beside the row. The shape is not: one
worker, two open batchable records on steps of two different tasks, loader called
over task 1's steps only, expected value = the halved share per §3.2A case 3.

**D2 — golden capture mechanism:** the implementer chooses between (i) a regeneration
branch inside `test_live_clock_goldens.py` gated on an env flag the committed test
never sets, or (ii) a throwaway capture script that is never committed. Constraints
either way: the goldens plus assert test land in the phase's first checkpoint commit
(C2), and no dead scaffolding ships (charter rule 4).

**D3 — golden fixture persistence:** golden fixtures are flush-only on the
rollback-scoped `db_session` fixture (`tests/conftest.py:db_session`) — never
committed — so their fixed client_ids cannot collide with committed residue across
runs. C5's committing fixtures keep the `try/finally` teardown the plan already
requires.

## Reality-check and decidability findings

- **R1 — paths.** Every plan §3 path verified: `services/context.py` exists;
  `services/queries/item_economics/` exists and `live_worked_seconds.py` is
  correctly marked new; the test directory exists and both test files plus
  `goldens/` are correctly marked new. "No other file" is implementable.
- **R2 — citations.** All resolve at source:
  `averaged_time.py:compute_record_contributions` (signature matches the plan's call
  `(session, workspace_id, u, W_start, now, now)`),
  `concurrency.py:averaged_seconds_by_record`,
  `process_step_transition.py:_recompute_step_time_totals` (directly callable;
  `_rate` returns `None` without a `UserWorkProfile`, cost 0 — as §9A claims),
  `step_state_record.py:StepStateRecord` (`uix_step_state_records_active` declared
  `postgresql_where=text("exited_at IS NULL")`, no `is_deleted` exclusion — §3.1A E
  accurate), `context.py:ServiceContext` (the "Never add boolean flags or config
  values" rule verbatim), `budget_division.py:DivisionStep`. **One mismatch:** the
  intention cites `_step_transition_core.py:apply_step_transition`; the symbol is
  `_apply_step_transition` (folded into A3/L5).
- **R3 — baseline staleness.** `git log`: `a0aaacc` (§6 measurement) precedes
  `6c15678`, which changed lookup code and test files. See L4/A4.
- **R4 — ServiceContext call sites.** All 401 `ServiceContext(` constructions in
  `app/` are keyword-based; none positional. Task 2's field addition is
  call-site-safe anywhere after the non-defaulted fields, and C9 needs no
  call-site rows. Confirms the plan's scoping.
- **R5 — §9A environment claims.** Verified at source:
  `tests/conftest.py:initialize_database` (suite runs on configured Postgres, so the
  partial-index guarantee is inherited), `tests/conftest.py:count_queries`, and the
  `json.dumps(sort_keys=True)` + sha256 pattern at
  `test_production_time_query.py:test_c14_c16_flat_time_only_degradation_and_tenant_boundary`.
- **R6 — golden JSON-safety.** All payload leaves are JSON-native:
  `serializers.py:_decimal` emits `str`, `serializers.py:_serialize_result` and
  `division_serializers.py:_serialize_production_time_final` isoformat
  `computed_at`, `division_serializers.py:serialize_production_time_section`
  isoformats `state_entered_at`. Fixture (b) must pin `computed_at` (the plan's
  "fixed timestamps" covers it). E-P section order is total
  (`budget_division.py:_section_sort_key`), E-P steps ordered by `client_id`;
  the one non-deterministic ordering found is E-A's task list (L1/A1).
- **R7 — the naive-`now` loud failure (C9's TypeError row) is reachable as
  claimed.** The loader's probe carries no `now` predicate; the wrapper's SQL
  accepts a naive bind; the failure lands in `concurrency.py:_sweep` at
  `(end - interval.entered_at)` when the open record's end falls back to the naive
  `now` — matching §1A HC-3A. Decidable as `pytest.raises(TypeError)`.
- **R8 — window semantics.** The plan's "min(entered_at) over that user's **probed**
  records" is consistent with §3.2A's derivation restricted to the probe set: a
  closed record overlapping only an unprobed open record's early segments shares no
  segment with any probed record and cannot alter its share. Recorded because
  §3.1's phrasing ("u's open working records") could be read wider; no contradiction,
  no ledger row.
- **R9 — mutation-ledger spot checks.** C5's both-sides table (§9A T2) re-derived
  and confirmed, including that the still-open case-2 second record keeps dividing
  inside `_recompute_step_time_totals` so settled = 1500 exactly. C4's rows are all
  decidable against the loader flow (flagged-open record is probed, earns `0.0`
  through the wrapper's `.get`; future-entered record is probed but never fetched by
  the wrapper's `entered_at < window_end`; both-NULL attribution never enters the
  distinct-user set). C8's stub seam works in both directions (module-global
  `datetime` under `from __future__ import annotations`; stub uncalled under
  contract, intercepted under the inserted read). C7's mutation bites only under
  A9's separation constraint.
- **R10 — archgraph.** Orientation only: initialized, 187 nodes / 278 edges,
  0 pending, 0 stale, 0 diagnostics — matches master plan §6. Nothing touched.

## Criteria decidability summary

| Criterion | Verdict |
|---|---|
| C1 | decidable after A4 (baseline re-measure + enumerated ID set) |
| C2 | decidable after A1/A2/D2 |
| C3 | decidable after A8 (row 1) and D1 (row 3); rows 2/4 writable now with §3.2A's integers |
| C4 | decidable as written |
| C5 | decidable after A5; both mutation sides confirmed at §9A's values |
| C6 | decidable as written (probe excludes the deleted step; the user-scoped sweep still fetches its record) |
| C7 | decidable after A9 |
| C8 | decidable as written |
| C9 | decidable after A6 (default-stamp row); other rows writable now |
| C10 | decidable after A7 — as written the row cannot fail under its own mutation |

## Write perimeter

From `git status` at session end: exactly one file created, nothing else touched —

- `docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/handoffs/reviewer/2026-08-20_phase1_projection_r0_handoff.md`

No code, no plan edits, no intention edits, no tracker row, no archgraph mutations
(status/read-only orientation only). The derivation skeleton is discarded per
doctrine; no appendix is attached so the implementer cannot receive it as guidance.
