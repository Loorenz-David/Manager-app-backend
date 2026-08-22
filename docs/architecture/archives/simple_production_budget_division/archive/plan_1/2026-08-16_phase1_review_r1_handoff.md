---
plan: 1
role: reviewer
round: 1
state: REVIEWED
verdict: CHANGES_REQUESTED
actor: Claude (Opus 5, plan-reviewer doctrine)
date: 2026-08-16
pipeline: simple_production_budget_division
---

# Phase 1 review round 1 — LIGHT-SCOPED first review

## Summary

**Verdict: CHANGES_REQUESTED — five should-fix, zero blocking. No behavioral defect
was found in either rule-6 mechanism.**

Both mechanisms are correct. M1's SQL and M2's function were read line-by-line
against intention §3/§4 as amended (round 5–6) and, for M1, against the generated
SQL itself; every clause of both contracts is present and correctly placed — group
unit, group-level window admission, `percentile_cont` + half-even with no `::numeric`
anywhere, min-sample gate, left-join enumeration, workspace scoping, half-even
`B_seconds` pre-`C`, the `t_i > 0` weight ladder with interpolated even-count median,
exact `Fraction` arithmetic, largest-remainder with the NULL-safe tie key, and the
empty-allocated-set path. The r1c ledger is **honest**: six sampled rows re-applied
at their named sites all turned red with the declared values, including the two
"bites exactly one row" claims for C9d. The two adjudicated equivalence STOPs
(C13b-door2, C20) were re-checked against the code and **hold**. My independent
suite run reproduces 2286 passed / 26 failed / 1 deselected, and the 26 decompose
byte-identically to the 23 v1 baseline IDs + the 3 foreign bootstrap IDs. The
verified perimeter over `0b85701^..fb48d13` is clean.

What fails the round is **test coverage, not behavior**: four criteria are not met as
written, and each gap was confirmed by an actual probe that leaves the phase suite
green while the defect the criterion exists to prevent is live in the code. The
worst of them lets a monetary key into the E2 step payload (HC-3) and lets E2's
entire typicals loader be deleted, both without a single red test.

⚠ OWNER DECISIONS REQUIRED (0)

Nothing here needs an owner answer. K5 (the foreign graph delta inside checkpoint
`0b85701`) stays recorded for the approval gate as already agreed; my findings are
all implementer-actionable test work.

## Write perimeter (this session)

- `docs/architecture/under_construction/implementation/simple_production_budget_division/handoffs/reviewer/2026-08-16_phase1_review_r1_handoff.md`
  — this file, and nothing else.

Per this round's prompt ("your full write perimeter (that one file)") I did **not**
touch the master plan tracker or `plans/plan_1.md`'s Review log; the coordinator owns
folding layer 1 into those. No architecture-graph mutation was made or attempted.

## Verified perimeter (charter re-review protocol)

`git diff --stat 0b85701^ fb48d13` = 19 files, 2776 insertions, 3 deletions.
Classification of every touched file:

| File | Classification |
|---|---|
| `domain/item_economics/budget_division.py` | registered new (master plan §4) |
| `domain/item_economics/division_serializers.py` | registered new (§4) |
| `services/queries/working_sections/get_working_section_typical_times.py` | registered new (§4) |
| `services/queries/item_economics/get_task_budget_allocations.py` | registered new (§4) |
| `tests/unit/domain/item_economics/test_budget_division.py` | registered new (§4) |
| `tests/integration/services/queries/working_sections/test_typical_times_query.py` | registered new (§4, P8) |
| `tests/integration/services/queries/item_economics/test_budget_allocations_query.py` | registered new (§4, P8) |
| `tests/unit/routers/api_v1/test_budget_division_routes.py` | registered new (§4) |
| `routers/api_v1/working_sections.py` | designated E1 mount (§4 Routes); addition only |
| `routers/api_v1/item_economics.py` | designated E2 mount (§4 Routes); addition only |
| `routers/README.md` | HC-1a artifact 2; addition only |
| `tests/unit/routers/test_phase9_item_economics_route_mirror.py` | HC-1a artifact 1; +1 row, count 23→24 |
| `tests/unit/routers/api_v1/test_item_economics_router.py` | HC-1a artifact 4 (round 6); addition only |
| `.archgraph/architecture.yml` | K5, recorded, out of scope |
| 5 × pipeline docs (master plan, plan_1, three implementer handoffs) | pipeline artifacts |

All 3 deleted lines are inside HC-1a artifact 1: the two `== 23` count assertions and
the renamed count-test function (`..._twenty_three_routes` → `..._twenty_four_routes`).
No file outside the registered set or the four HC-1a artifacts changed. **No migration,
no schema diff** — HC-2 clean.

## Findings

### S1 (should-fix) — E2 carries a second, entirely unproven copy of the M1 aggregation

`get_task_budget_allocations.py:47-97` (`_load_typicals`) reproduces
`get_working_section_typical_times.py:24-46` clause-for-clause (only the `state`
literal spelling, the `ORDER BY` and the `working_section_ids` filter differ). M1 —
a rule-6 mechanism — therefore has two implementations that can drift, and the copy
that the worker cards actually consume is guarded by nothing.

**Probe (confirmed):** replacing `_load_typicals`'s body with `return {}` leaves all
33 phase tests green (`test_budget_division.py`, `test_budget_allocations_query.py`,
`test_typical_times_query.py`, `test_budget_division_routes.py`). No test anywhere
asserts a non-null `typical_worker_seconds` inside an E2 payload, and no E2 fixture
holds two allocated steps in different sections, so M2's proportional weighting is
never exercised with real typicals on the endpoint that ships it.

Authority: intention §3 (M1) + charter rule 6 (silent-failure mechanisms); master
plan §4 registers **one** query service for M1.

Correction: extract the grouped-median subquery into one shared helper both services
call, and add an E2 integration row with two sections whose typicals differ (e.g.
3600 / 1800, ≥5 qualifying groups each) pinning both the payload
`typical_worker_seconds` values and the resulting 2:1 allowance split.

### S2 (should-fix) — C14's constancy fixture never runs the status-resolution path, so the N8 defect it exists to block passes green

`test_budget_allocations_query.py:91-114`. C14 as rewritten by projection P10
(`plan_1.md:188-197`) requires the 1-task and 3-task calls to *"each include an
evaluation-less task so the status path runs in both"*. Neither call does:

- the 1-task call passes only `values[3]` — the **evaluated** task;
- the fixture's only evaluation-less task (`no_item_task`) has no PRIMARY `TaskItem`,
  so it short-circuits to `NOT_EVALUATED` at `get_task_budget_allocations.py:225-227`
  without ever reaching `resolve_economics_selection`.

**Probe (confirmed):** inserting a per-task workspace-wide `ProductionCostGroup`
query immediately before `resolve_economics_selection` (`:229`) — the exact
projection-N8 defect, a per-task `_load_preview_inputs` — leaves all 3 tests green.
The mutation the ledger *did* run (per-task evaluation query) bites; the expensive
one the criterion was rewritten to catch does not.

Correction: add a second evaluation-less task **with** a primary item (+ valuation)
so the resolver path runs, and include one such task in both the 1-task and the
3-task call.

### S3 (should-fix) — C17's E2 step key-set assertion is missing; HC-3's guard has a hole exactly where the worker cards read

`test_budget_division_routes.py:149-155`. C17 (`plan_1.md:204-207`) names three exact
key-set assertions — an E1 row, an E2 task object, **and an E2 step object**. Only
two exist, and the `"money"/"minor"` scan at `:155` iterates the task dict's keys
only, never `steps[]`.

**Probe (confirmed):** adding `"consumed_cost_minor": 4321` to `serialize_budget_step`
(`division_serializers.py:30-40`) leaves all 25 tests green.

Authority: intention HC-3 (time only, never money — all four roles); master plan §6
set-assertion rule.

Correction: add `set(serialize_budget_step(task["steps"][0]))` equality against the
eight-key set, and extend the money scan across step keys.

### S4 (should-fix) — C15's E1 row does not pin which service the route resolves to, so the P7 shadowing regression passes green

`test_budget_division_routes.py:36-49`. With `run_service` monkeypatched, `GET
/api/v1/working-sections/typical-times` returns 200 with exactly one recorded call
whether it lands on E1 or on `get_working_section_route` with
`working_section_id="typical-times"` — the test cannot tell them apart.

**Probe (confirmed):** moving the E1 declaration below
`@router.get("/{working_section_id}")` (`working_sections.py:149`) leaves all 11
route tests green. Projection P7 called this ordering load-bearing; today only a
hand-check defends it. (Declaration order *is* currently correct: E1 at `:131`,
param route at `:149`.)

Correction: assert `calls[0][0] is working_sections.get_working_section_typical_times`
on the E1 row — the precedent already protecting E2 is
`test_item_economics_router.py:133`.

### S5 (should-fix, lowest) — C13's "byte-agreeing with `get_task_budget_status`" clause is unasserted

`test_budget_allocations_query.py:72-87` asserts `actual_worker_seconds == 1200` but
never invokes `get_task_budget_status` on the same fixture, so the byte-agreement C13
names is not proven by any test.

Verified correct by reading (this is a coverage gap, not a behavior defect): both
surfaces sum the same column over the same filter —
`get_task_budget_status.py:138-147` (`SUM(total_working_seconds)` WHERE
`workspace_id`, `task_id`, `is_deleted IS false`, no state predicate) vs
`get_task_budget_allocations.py:154-162` + `:259` (identical loader filter, Python
sum, no state predicate) — and both null the field for evaluation-less tasks
(`_empty_status:81-97` vs `:260-267`).

Correction: one extra assertion calling `get_task_budget_status` on the C13 fixture
and comparing `actual_worker_seconds`.

## Notes

- **N-a (README, P11 hand-check).** The two new detail sections
  (`routers/README.md:3996-4016`) omit the `#### Request Body` and `#### Responses`
  blocks that every other detail section in this hand-maintained file carries, so
  the E1/E2 payload keys — the reason these surfaces exist — are documented nowhere.
  The E2 section is also filed between two working-sections entries instead of in
  path order among the item-economics entries. Quick Index rows for both routes are
  present, correctly placed and accurate (route, tag, operationId).
- **N-b.** The E2 row was inserted at
  `test_phase9_item_economics_route_mirror.py:61` directly beneath the comment *"The
  one route the whole workspace may call; the handler picks the money-free worker
  service for WORKER and SELLER identities"* — that comment now describes
  budget-allocations, and its claim is false for it. Move the row below the comment's
  route, or re-word.
- **N-c.** `get_task_budget_allocations.py:223`, `:278`, `:281-282` computes `binding`
  per task, stores it as `_binding`, then pops it before serializing — dead
  computation. Remove it or serve it.
- **N-d.** C3's "zero-worked allocated steps `on_track`" clause is unasserted —
  `test_budget_division.py:46-52` pins the clamped allowance to 0 but not the
  `share_state`. Behavior verified correct by reading (`budget_division.py:178`).
- **N-e.** C5b pins only `z`'s allowance (`test_budget_division.py:86-87`), where C5
  requires "pinned integers for every step". C5a does pin both.
- **N-f.** `budget_division.py:107` rebuilds `{state.value for state in
  EXCLUDED_STEP_STATES}` once per step inside the comprehension; hoist it above the
  loop. Cosmetic at current step counts.
- **N-g.** `item_economics.py:36` inserts the new service import out of the file's
  alphabetical import order.
- **N-h (carry to the frontend handoff, not an implementer fix).** For a task whose
  status is not `ok`/`infeasible`, E2 returns `actual_worker_seconds: null` while
  `steps[].worked_seconds` stay populated. This is *correct* — it mirrors
  budget-status's `_empty_status`, which plan T3 required — but it is broader than
  intention §5's enumerated null list (four fields) and contradicts §6's
  "`actual_worker_seconds` equals the sum of its own `steps[].worked_seconds` by
  construction". Recommend §5/§6 absorb the fifth null; the frontend must sum
  `steps[]` to show consumed time on unevaluated tasks.

## Verified correct (settled ground — do not re-derive next round)

- **Perimeter** as tabulated above; HC-1a additive on all four artifacts; HC-2 clean.
- **M1 SQL** against intention §3 as amended, confirmed on the generated SQL captured
  during probing: grouping unit `(working_section_id, task_id)`; all four
  contributing-step predicates (`workspace`, `state='completed'`, `is_deleted IS
  false`, `recorded_time_marked_wrong IS false`); **group-level** window admission as
  `FILTER (WHERE max(closed_at) >= cutoff)` on both the count and the percentile,
  with **no per-step `closed_at` predicate anywhere**; `percentile_cont(0.5) WITHIN
  GROUP (ORDER BY sum(total_working_seconds))` on the bigint→double path;
  `CAST(round(<double>) AS INTEGER)` — **no `::numeric` on the rounding path**;
  `sample_count >= 5` gate (NULL below); `LEFT OUTER JOIN` from `working_sections`
  so zero-sample sections survive with `null`/`0`; workspace scoping on both the
  subquery and the outer select; the `working_section_ids` filter applied in the
  outer WHERE, where it cannot alter any surviving section's aggregate; NULL
  `MAX(closed_at)` fails the window (intention N5) by construction.
- **M2** against intention §4: half-even `B_seconds` computed **before** `C`;
  non-deleted universe, then the `EXCLUDED_STEP_STATES` partition; `C` charged;
  `D = max(0, B − C)`; weight ladder with the `t_i > 0` gate, the per-allocated-step
  median fallback including the interpolated even-count mean, and the all-fail
  unit-weight branch (so `Σw > 0` whenever the allocated set is non-empty); **exact
  `Fraction` throughout — no float on the path**; floors + largest-remainder with the
  tie key `(-remainder, seq is None, seq or 0, client_id)`, giving `Σ allowance = D`
  by construction; `share_state` mapping including `no_budget` precedence per §5;
  empty-allocated-set branch; deterministic row ordering.
- **Two-doors + budget-status agreement**: C13 test file re-run green; fixture read;
  the deleted+skipped step (1200s) is absent from both the rows and
  `actual_worker_seconds` (1200, not 2400); the non-deleted excluded step is charged
  (`D = 6000 − 1200 = 4800`, pinned). Column/filter agreement with budget-status
  verified structurally (see S5).
- **Both adjudicated equivalence STOPs upheld.** C13b-door2: `excluded` is built from
  `live_steps` (`budget_division.py:104-108`), which already dropped deleted rows, so
  the named door-2 site is unreachable by construction and the protective red lives
  at C13a. C20: with `allocated == []` every downstream loop (`:149-171`) is
  vacuously empty and the returned dict is identical with or without the guard. Both
  adjudications are sound; neither needs re-opening.
- **ORM identity**: no `__eq__`/`__hash__` override on the model base, so
  `step not in excluded` (`:109`) is identity-based for ORM rows and `client_id`-
  disambiguated for `DivisionStep` — no mis-partition risk.
- **Route mechanics**: E1 declared at `:131`, above the param route at `:149`, and
  tab-indented consistently (N12) — verified with `cat -t`. E2 declared above the
  parameterized `/tasks/{task_client_id}/…` block with the ordering comment. Both
  `require_roles([ADMIN, MANAGER, WORKER, SELLER])`. Cap raised as
  `BUDGET_ALLOCATIONS_TOO_MANY_TASK_IDS` → 422 through the real command (r1c's W9 fix
  verified). Repeatable-param style per P12, not filed as a convention break. The
  new route satisfies `test_item_economics_routes_declare_no_response_model`.
- **Serializers** vs intention §5: exact key sets on all three shapes, decimal
  minutes as strings via `_decimal`, seconds as ints, `section_name_snapshot` passed
  through as stored (`string | null`, N2), **no monetary key present anywhere** in
  `division_serializers.py`.

## Ledger sample (six rows — prompt required five minimum)

Every mutation applied at its **named site**, run, observed red, reverted.

| # | Row | Mutation (site) | Observed red | Reverted |
|---|---|---|---|---|
| 1 | **C9c** | `get_working_section_typical_times.py:31-36` — add `TaskStep.closed_at >= cutoff` to the subquery WHERE (per-step admission) | `test_typical_query_admits_old_first_pass_when_recent_rework_closes_group` FAILED `assert 2000 == 4200`; 1 failed / 7 passed | ✅ |
| 2 | **C9d-rounding** | `:44` — `cast(func.round(cast(percentile, Numeric)), Integer)` | `…_half_even_rounding[half-even-rounding]` FAILED `assert 1001 == 1000`; `[continuous-interpolation]` stayed green — confirms the plan's "each mutation bites exactly one row with a distinct wrong value" | ✅ |
| 3 | **C9b** | `:37` — `group_by(working_section_id, task_id, client_id)` | `test_typical_query_aggregates_same_task_section_steps_before_sampling` FAILED `assert 6 == 5` (also collaterally reddens C9c) | ✅ |
| 4 | **C5b** | `budget_division.py:75` — naive `(sequence_order, client_id)` key | `test_tie_order_is_nulls_last_then_client_id` FAILED `TypeError: '<' not supported between instances of 'int' and 'NoneType'` (counts as red per C5b) | ✅ |
| 5 | **C19** | `:61` — `int(minutes * Decimal(60))` (truncate) | `test_half_even_budget_seconds_quantization` FAILED `assert 11700 == 11701` | ✅ |
| 6 | **C1** (my choice) | `:169-171` — independent `round(float(share))`, largest-remainder removed | `test_largest_remainder_preserves_distributable_sum` FAILED `assert 60 == 61` | ✅ |

Conclusion: the r1c ledger is honest on every row sampled. Nothing in the sample
contradicted its recorded result.

## Suite (P-L — re-measured, not trusted)

Command, from `backend/app/`: `PYTHONPATH=. pytest -q -m 'not e2e'`

**My result: 2286 passed, 26 failed, 1 deselected, 2 warnings in 256.99s** — matches
the r1c handoff exactly.

Failure-list diff, computed mechanically (`comm` against the 23 IDs extracted from
`item_cost_calculation/plans/phase_1_worker_money_redaction.md:198-226`):

- baseline IDs missing from my run: **none** (all 23 present, byte-identical);
- extra IDs in my run: **exactly 3**, all
  `tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py`
  (`…creates_requested_configuration_and_updates_owned_values`,
  `…person_owned_configuration_and_section_membership_are_not_overridden`,
  `…human_successors_permanently_freeze_bootstrap_basis_and_model`) — the owner's
  untracked in-flight bootstrap work, foreign and out of scope.

C18 satisfied: 23 baseline byte-identical + 3 foreign; selected count grew additively.

Focused phase set re-run at HEAD after all probes: **33 passed** across the four new
files; the two v1 mirror files plus the phase route file: **120 passed**.

## Mutation-probe declaration

Files touched by probes, each applied-and-reverted and verified **byte-identical** to
checkpoint `fb48d13` afterwards (`git diff fb48d13 -- app/beyo_manager app/tests`
returns empty; SHA-256 re-checked against the pre-probe baseline):

| File | SHA-256 (before == after) |
|---|---|
| `beyo_manager/services/queries/working_sections/get_working_section_typical_times.py` | `ad6cf617c5840943c22b01edd15337d72de6db4032c0e5e56646556d6e7fe2de` |
| `beyo_manager/domain/item_economics/budget_division.py` | `77a5859a5028a375bb101566a7c1dddace0e0832708ff2ce03f5c9366a86c833` |
| `beyo_manager/domain/item_economics/division_serializers.py` | `bb5413be30f7a353498a171c157d7f4d0e16bd5a8964c5e319c781322832bdc9` |
| `beyo_manager/services/queries/item_economics/get_task_budget_allocations.py` | `e226d61accc5dee4e7bb80d951fef95370a120836508cb5010712dc861f27b0a` |
| `beyo_manager/routers/api_v1/working_sections.py` | `fd23d4f2cfea4d12f64a75c0c64cc19f01c0c5abdcac94f3e6c58c70ef790c97` |

Database/state side effects: **none**. Every probe run used the phase's own
teardown-owning fixtures (transaction rollback for the grouped M1 family, explicit
`DELETE` chains elsewhere); no schema change, no migration, configured DB left at
head. The uncommitted tree dirt that remains is exactly what was present when this
session opened — `.archgraph/architecture.yml`, `bootstrap_app.py`, the untracked
bootstrap-seed files, `to_implement_the_accurate_costs_and_projections/`, and the two
pipeline docs the r1c round edited — none of it mine.

## Lessons for the plans (coordinator folds upstream)

1. **A criterion that specifies a fixture property must be checked as a fixture
   property at review time, not inferred from a green mutation.** C14 named "each
   including an evaluation-less task so the status path runs in both" precisely
   because P10 knew the naive shape passes; the round ran a *different*, weaker
   mutation (per-task evaluation query) and recorded it as C14's red. Rule 11 should
   require the mutation to be applied at the site the criterion's *rationale* names
   (here: the preview-load site), not merely at a site that reddens the test.
2. **Multi-part criteria need one row per part.** C17 (three key-set assertions) and
   C13 (row absence + `actual_worker_seconds` + byte-agreement) each shipped with
   parts silently missing while the ledger recorded the criterion as covered. Split
   such criteria into lettered rows (C17a/b/c) so the criterion→test map cannot mark
   a compound criterion green on partial coverage.
3. **Declaration-order and mount-point risks need service-identity assertions, not
   status-code assertions.** P7 was correctly identified as load-bearing and
   correctly implemented, yet nothing defends it, because the route test monkeypatches
   `run_service` and asserts only `200` + one call. Any future plan that pins route
   ordering should require `calls[0][0] is <the service>` (precedent already in the
   repo at `test_item_economics_router.py:133`).
4. **A registered mechanism implemented twice needs a criterion on both copies, or a
   registry rule forbidding the second copy.** Master plan §4 registered one M1 query
   service; T3's "constant query count" requirement pushed the implementer to inline a
   second copy inside E2, and no criterion followed it there. Either §4 should
   register the shared helper, or the plan should carry a criterion per call site.
5. Charter rule 2's companion ("each row's fixture makes its own predicate the ONLY
   reason the expected outcome holds") has a mirror worth writing down: **each
   criterion's guard must be the only reason its test passes** — S1/S2/S3/S4 are all
   cases where deleting the guarded construction left the test green.

## Human-authorization backlog

None beyond the already-recorded K5 graph note. No architecture-graph adjudication is
requested by this review, and no owner decision is required to act on any finding.
