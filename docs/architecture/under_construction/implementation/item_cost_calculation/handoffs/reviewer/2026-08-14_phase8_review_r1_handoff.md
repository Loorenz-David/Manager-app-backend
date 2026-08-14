---
plan: phase 8 — status & results
role: review
round: 1
verdict: CHANGES_REQUESTED
date: 2026-08-14
actor: Claude Opus 5 (plan-reviewer)
---

# Phase 8 review r1 handoff

## Summary

**The production surface is correct. The proof is not.**

I re-derived every mechanism against the code and ran the full deferred
mutation ledger (17 named rows + 1 I added at the route seam). Of those
**18 mutations, 2 turn the shipped suite red.** Sixteen — including every
one of the four §8B.1 emission points, all three C1 committed-current
filters, the §8A.2 two-cost boundary, the A15 DELETE re-resolution, the C7
producer swap, and serving a WORKER the full manager money payload — leave
the suite at its exact baseline.

I then built the declared-unbuilt families as probes: **19 probe rows, all
green on the shipped tree**, and 16 of the 18 mutations now bite exactly one
probe row each. That is the important finding: **nothing I could reach is
behaviourally wrong.** The emissions fire, the guards hold, the money
boundary redacts, the upsert converges, the migration is faithful. What is
missing is the evidence that any of it will still be true after the next
edit.

Two acceptance criteria (C2 bucket policy, C3 batch dilution) have zero rows
from anyone, including me.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. Every finding is a technical fix inside the phase
fence; no semantic decision is open, and no card is raised.

## Verified environment and numbers

- Full non-E2E suite, foreground, by me: **2111 passed / 23 failed / 1
  deselected**, 112.28s. Reproduced a second time at session close:
  identical.
- Failure set **byte-compared** (sorted `diff`) against the phase-1 S2
  list of 23 — **byte-identical, zero drift**.
- Collection reconciles **+35** over the phase-7 baseline (2099 selected →
  2134): 27 from the four new test files (migration 1, phase-8 integration
  8, phase-8 serializers 15, handler/wiring unit 3) + 8 from the router
  test's new parametrized rows. Exact.
- All **19 declared final hashes recomputed byte-identical** at session
  entry and again at session close.
- Configured DB left at head **`c1d2e3f4a5b6`**; enum label present by
  state query.
- **Disposable round-trip run** (r1b skipped it): fresh
  `beyo_manager_p8_rev_r1` → `alembic upgrade head` in 1.70s → label present
  by `pg_enum` state query → `downgrade be9dfe42a035` succeeds → label
  correctly **remains** (PG cannot drop enum values), matching the
  migration's own docstring and the `f2c3d4e5f6a7` precedent → re-upgraded
  → database dropped.
- `alembic check`'s three drifts (`email_sync_states_connection_id_key`,
  two `step_state_records` indexes) **predate the phase structurally**: the
  phase touched no model file at all (`git diff --name-only b71d252..HEAD --
  app/beyo_manager/models/ app/migrations/` returns only the new migration).
  Routed to the only-if-cheap ledger.
- Architecture Graph: **read-only, zero delta**. Entry and exit both
  172 nodes / 254 edges, revision `c74eb91304146d…`, 21 pending, 1 stale,
  no diagnostics. The three A16 discrepancy filings are present under the
  maintenance ledger's `open/`.

## Findings ledger

7 blocking / 6 should-fix / 6 notes.

| id | sev | criterion / authority | what is wrong |
|---|---|---|---|
| **B1** | blocking | C6b + C10 (A4), §8B.1 rows 1–3, charter 11 | **All four §8B.1 emission points can be deleted with a green suite.** M5 (READY-entry emit, `_task_state_transitions.py:114-118`), M6 (reopen emit, `:55-59`), M7/M8/M9 (the three terminal emits, `resolve_task.py:99-103`, `fail_task.py:99-103`, `cancel_task.py:99-103`) each leave the focused scope at its exact baseline (400 passed / 2 established). No test observes that a result task is ever enqueued. |
| **B2** | blocking | C6, §8A.5, A17-L23/L24 | **The straggler re-emit and its round-6 READY half have no arbiter.** M10 (delete the whole branch) and M11 (narrow the guard to terminal only) both survive. The exact-count discipline L24 demands is asserted nowhere. |
| **B3** | blocking | C1 + A7, §8A.6, HC-2, charter 2 companion | **All three committed-current filter deletions survive.** `test_c1_projection_is_invisible_to_status_and_result_handler` is order-dependent: the committed row is inserted before the projection, so an unfiltered read returns it anyway — two sufficient causes. The worker service (A7's third site) has no C1 row at all. |
| **B4** | blocking | A1 (GOVERNING), charter 2 + 3, P-V 3rd ext | **C7 is a serializer echo.** All twelve rows build a `SimpleNamespace` with `status` already set and assert the serializer copies it. Every row's expression is identical, no row names a producer, the hazard row is absent, and M12 (swap `resolve_item_economics_status` for `selection.status` — the exact leak A1 exists to prevent) survives. |
| **B5** | blocking | C9, §8A.2, §11A.1/§11A.3, HC-1 | **The two-cost boundary has no arbiter at either site.** M13 (add `total_cost_minor` to the status payload at its definition site — §8A.2's own named mutation) survives. M18 (serve WORKER/SELLER the full manager payload: `production_budget_minor`, `consumed_cost_minor`, `variance_cost_minor`, `evaluation_id`) also survives — the route test asserts only which *service* was selected, never what the endpoint returns. A11's quantified disjointness test was not built. |
| **B6** | blocking | A15, intention round 17 R17-2 | **The DELETE re-resolution has no arbiter.** M4 (revert `delete_item_valuation.py` to the hardcoded `ITEM_UNVALUED`) survives. Neither the configured row nor R17-2's literal same-warning equality is asserted anywhere. |
| **B7** | blocking | C2, C3, A12 | **Two acceptance criteria carry zero rows.** C2 (four-bucket policy, incl. A12's `PAUSED` + `SHIFT_ENDED` construction and the `inaccurate_working_seconds` bucket) and C3 (batch dilution: two batchable steps, full overlap, Σ = wall clock) were declared unbuilt by r1b and I did not build them either — both need the analytics time pipeline stood up, which is a build task, not a probe. Recorded honestly rather than waived. |
| **S1** | should-fix | A17-L21, charter 11 | The route inlines `claims.get("role_name") in {WORKER, SELLER}` instead of the mandated `include_monetary_step_fields(role_name)` reuse. `include_monetary_step_fields` is a **positive allow-list** (ADMIN/MANAGER); the shipped code is a **negative deny-list**. They agree only over the four canonical names — for any other `role_name` the shipped predicate grants full money. `require_roles` blocks non-canonical names today, so there is no live leak, but the shape fails open where A17 decided it must fail closed. |
| **S2** | should-fix | A6, charter 4 | `item_economics.py:405-409`'s route tables are **dead code and tautological**. `_MANAGER_ONLY_ROUTES` is derived from `router.routes`, so `_ROUTES` equals the router surface by construction and can never disagree with it; and grep finds **zero references** to any of the three names. M16 ("move budget-status into the manager-only table") is therefore unbiteable by construction. The real completeness arbiter is the *test* module's hand-written `_ROUTES` list, which does its job — so delete the production block, or make the role-gate tests parametrize over it as A6 specified. |
| **S3** | should-fix | charter 4 | `serialize_item_lifetime_economics` (`serializers.py`) has **zero callers** anywhere — `get_item_lifetime_economics` builds the identical dict inline. |
| **S4** | should-fix | A7, charter 5 | The evaluated read model is **duplicated verbatim**: `get_task_budget_status.py:127-166` is a byte-for-byte copy of `_build_evaluated_status` (`:169-216`), which only the worker service calls. A7 mandated separate *filters*, not two copies of the money computation — a correction applied to one path silently misses the other. |
| **S5** | should-fix | A17, P-H | The `route.response_model is None` structural row over `item_economics.router.routes` was **not built** (grep: no `response_model` assertion in the router test). It is green today; its job is regression, so its absence is the whole loss. |
| **S6** | should-fix | A15 (unsanctioned side effect) | `delete_item_valuation` now **raises `NotFound` when the item is soft-deleted**: the re-resolution loads the Item with `is_deleted.is_(False)` and raises inside `maybe_begin`, which rolls the soft-delete back. Before this phase the delete succeeded and returned `ITEM_UNVALUED`. A15 asked for re-resolution, not a new refusal. Suggest resolving to `ITEM_UNVALUED` when the item is gone. No test covers it. |
| **N1** | note | baseline #5 | `test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task` is in the **established failing set**, so A3's reopen-signature change landed on a path with no green integration coverage. My probe covers the phase-8 half; the baseline failure itself stays where it is. |
| **N2** | note | A9 | `serialize_item_cost_result_worker` has only a test caller; production reaches the same key set through `_serialize_result` inside `serialize_task_budget_status`. Same keys today — recorded so the arbiter's placement is known. |
| **N3** | note | P8-5 | The migration is faithful to the `f2c3d4e5f6a7` precedent (`ADD VALUE IF NOT EXISTS`, no-op downgrade) and its docstring states the PG limitation **honestly** — better than the precedent, which is silent. Verified by round-trip. |
| **N4** | note | §10 | The three `alembic check` drifts are pre-existing; route to the only-if-cheap ledger, not this phase. |
| **N5** | note | A13 / C5 | A13's "observe `computed_at` strictly advance" replaced C5's whole-row-variant-must-fail clause, and the advance **does** bite (M17). Correct as amended. |
| **N6** | note | §8A.6 / P-B | The status query returns `result: null` whenever there is no current committed evaluation, even if a result row exists. Consistent with the null-numerics rule and unreachable today (INV-E2). Recorded so a later reader does not file it as a bug. |
| **N7** | note | A15 | A15 passes a literal `None` for the post-delete valuation rather than re-reading it. True today (one current valuation per item by the supersede chain); it would become false if that ever changed. |

## Mutation ledger — the 17 deferred rows, plus one

Scope for every row: the phase's focused arbiter set (11 paths — item-economics
integration + unit, migrations, tasks + task_steps commands, analytics, the
router test, the state-transition unit). **Baseline: 400 passed / 2 failed**
(both established: baseline #5 and #6). "Bites" = a NEW red beyond that set.
Every row reverted with `git checkout --` and the file's sha256 recomputed
byte-identical to the entry hash.

| # | mutation (file · site) | sha256 before → mutated | shipped suite | my probe |
|---|---|---|---|---|
| 1 | C1 manager filter deleted · `get_task_budget_status.py` | `9abf05b5…0941` → `64e5cb10…7876` | **survives** | bites `test_probe_c1_projection_isolation_with_a_discriminating_fixture` |
| 2 | C1 worker filter deleted · `get_task_budget_status_worker.py` | `011cf2ae…7f00` → `783698f8…a29d` | **survives** | bites `test_probe_c1_worker_service_filter_is_independent_and_projection_blind` |
| 3 | C1 handler filter deleted · `process_item_cost_result.py` | `d57ca890…5172` → `14bb672d…d095` | **survives** | bites `test_probe_c1_projection_isolation_…` |
| 4 | A15 re-resolution removed · `delete_item_valuation.py` | `0bb4d312…b007` → `2c15c2c2…09a8` | **survives** | bites `test_probe_a15_delete_valuation_reresolves_the_status` |
| 5 | READY-entry emit deleted (definition site) · `_task_state_transitions.py` | `728e7770…073c` → `8c41cb44…c1b5` | **survives** | bites `test_probe_c6b_ready_entry_writes_ready_snapshot_with_null_closed_at` |
| 6 | reopen emit deleted (helper definition site) · `_task_state_transitions.py` | `728e7770…073c` → `9d0664bc…cc0e` | **survives** | bites `test_probe_c6b_reopen_through_add_task_steps_flips_snapshot_to_working` (through `add_task_steps`, as specified) |
| 7 | resolve terminal emit deleted · `resolve_task.py` | `f5d9e23f…4cb4` → `cffa4f03…1331` | **survives** | bites `…[C10-terminal-resolve]` |
| 8 | fail terminal emit deleted · `fail_task.py` | `bceb0768…cede` → `4d72d3ae…b590` | **survives** | bites `…[C10-terminal-fail]` |
| 9 | cancel terminal emit deleted · `cancel_task.py` | `97de30b2…a438` → `b4bf6a52…cdba` | **survives** | bites `…[C10-terminal-cancel]` |
| 10 | straggler re-emit deleted · `process_step_transition.py` | `fe1091c6…7e80` → `71f50c47…567d` | **survives** | bites `…[C6-straggler-RESOLVED]` **and** `[C6-straggler-READY-half]` |
| 11 | straggler READY half narrowed to terminal-only | `fe1091c6…7e80` → `b4bc929b…1a35` | **survives** | bites `…[C6-straggler-READY-half]` only |
| 12 | C7 selection-OK producer swap · `get_task_budget_status.py` | `9abf05b5…0941` → `8c16f71a…5d7b` | **survives** | bites `test_probe_c7_hazard_selection_ok_without_committed_evaluation_reads_not_evaluated` |
| 13 | C9 `total_cost_minor` added (definition site) · `serializers.py` | `12d6e36a…3f88` → `f97fd225…d4f2` | **survives** | bites `test_probe_c9_step_and_economics_money_key_sets_are_disjoint` |
| 14 | C11 live task field substituted for the snapshot · `get_item_lifetime_economics.py` | `c10d6bc6…2e06` → `e228e0ce…4b4e` | **survives** | bites `test_probe_c11_lifetime_uses_evaluation_snapshot_not_the_live_task_field` |
| 15 | A6 WORKER removed from the budget-status allow-list · `item_economics.py` | `50efab29…aefe` → `b6127127…6101` | **BITES** `test_budget_status_route_is_available_to_all_roles[get-budget-status-worker]` | also bites the route probe |
| 16 | A6 budget-status moved out of `_ALL_ROLE_ROUTES` · `item_economics.py` | `50efab29…aefe` → `19660fef…9dce` | **survives — unbiteable by construction** (S2: the table is dead code) | n/a |
| 17 | A13 `computed_at` frozen (dropped from the SET list) · `process_item_cost_result.py` | `d57ca890…5172` → `1929a4c0…b512` | **BITES** `test_c5_replay_updates_only_computed_at_and_converges` | — |
| **18** | *(added by me)* route serves WORKER the manager payload · `item_economics.py` | `50efab29…aefe` → `e1f345bf…bd898` | **survives** | bites `test_probe_c9_budget_status_endpoint_returns_no_money_for_worker_roles[route-worker\|route-seller]` |

**Score: 2 of 18 bite the shipped suite. 16 of 18 bite a probe I built.**

### P8-7 — the R2-N2 hardening does fail

Renaming the `evaluation_id` key at its production site
(`commit_item_cost_evaluation.py:391`, `extra={"evaluation_id": …}` →
`"evaluationId"`) turns
`test_phase7_create_task_auto_commits_and_dispatches_after_task_transaction`
red. Reverted; sha256 back to `6419cec2…73a4`. The hardening is real.

## Row-coverage map — C1–C11 as amended (A1–A18)

| criterion row | arbiter today | verdict |
|---|---|---|
| C1 manager / handler filters | `test_c1_projection_is_invisible_to_status_and_result_handler` | non-discriminating → **B3** |
| C1 worker filter (A7 3rd site) | — | **B3** |
| C2 four buckets (A12) | — | **B7** |
| C3 batch dilution | — | **B7** |
| C4 deleted excluded / SKIPPED counts | `test_c4_consumption_excludes_deleted_steps_but_counts_skipped_steps` | ✔ (no-steps→0 COALESCE row still missing) |
| C5 replay identity + `computed_at` advance (A13) | `test_c5_replay_updates_only_computed_at_and_converges` | ✔ (M17 bites) |
| C5 no evaluation → nothing written | `test_c5_without_current_evaluation_writes_nothing` | ✔ |
| C5 ON CONFLICT update path | same replay row (`client_id` preserved) | ✔ |
| C5 config supersession after close → byte-identical | — | gap |
| C6 straggler RESOLVED / READY / WORKING, exact counts | — | **B2** |
| C6b READY entry (`ready`, `closed_at` NULL) | — | **B1** |
| C6b reopen → `working` | — | **B1** |
| C6b re-entry converges (8B.3) | — | gap |
| C6b three terminal rows, zero-notification fixtures (A4) | — | **B1** |
| C6b PENDING / ASSIGNED / STALLED (A8) | `test_c6b_non_admitted_states_write_nothing[PENDING\|ASSIGNED\|STALLED]` | ✔ |
| C6b §8B.2 totality | `test_result_task_type_and_admitted_states_cover_ready_and_terminal_states` (asserts the complement) | ✔ structural |
| C7 twelve members (A1) | `test_c7_serializes_each_shipped_status_exactly[P-V-…×12]` | vacuous → **B4** |
| C7 hazard row / priority row | — | **B4** |
| C8 bound / mismatched / detached | — | gap |
| C9 worker result key set (A9) | `test_worker_result_serializer_has_no_monetary_fields` (exact set equality) | ✔ |
| C9 quantified disjointness (A11) | — | **B5** |
| C9 route money boundary | — | **B5** |
| C10 handler map + queue routing | `test_c10_result_handler_is_registered_on_the_analytics_route` | ✔ |
| C10 three terminal enqueues | — | **B1** |
| C11 snapshot axis (A2.5 named mutation) | `test_c11_lifetime_read_uses_snapshot_episode_and_result_only_totals` | M14 survives → **B7**/S-list |
| C11 role gate + route in the arbiter table | router test `_ROUTES` equality | ✔ |
| C11 pagination / ordering | — | gap (verified correct by reading: `limit+1`, `committed_at DESC, client_id DESC`) |
| A6 P-G both directions | M15 ✔ / M16 unbiteable | half → **S2** |
| A10 loader equality + non-vacuity | — | gap |
| A17 `route.response_model is None` | — | **S5** |
| R2-N2 hardening | `test_phase7_create_task_auto_commits…` | ✔ (bites) |
| migration state | `test_process_item_cost_result_enum_member_is_present` | ✔ |

## What I verified CORRECT (re-derived, not taken on trust)

- **§8B.2 admission is total.** `_ADMITTED_STATES` = {WORKING, READY, RESOLVED,
  FAILED, CANCELLED}; the complement is exactly {PENDING, ASSIGNED, STALLED}
  and the unit test asserts the set difference, so a new `TaskStateEnum`
  member cannot silently join either side.
- **The upsert matches A5 exactly.** SET list = the eleven enumerated columns
  and nothing else; `client_id`, `task_id`, `created_at`, `workspace_id` are
  excluded. `client_id` and `created_at` still populate on INSERT via their
  Column-level `default=` callables (SQLAlchemy Core applies them), and the
  regenerated `client_id` is correctly discarded on the UPDATE path —
  `test_c5_…` asserts `second.client_id == first.client_id`. Constraint name
  `uq_item_cost_results_task_id` matches the model's `UniqueConstraint`.
- **§8A.1's expression is identical in both consumers** (handler and status
  query): `COALESCE(SUM(total_working_seconds), 0)`, `is_deleted` the only
  filter, step state deliberately unfiltered, rollup columns only, no
  `inaccurate_*` / pause / ended-shift read.
- **The two-producer composition holds.** `resolve_item_economics_status`
  terminates at `NOT_EVALUATED` (`ITEM_READINESS_PRECEDENCE`'s last row is
  unconditional `True`) and structurally cannot emit `ok`/`infeasible`; those
  two come only from the committed-evaluation branch. A1's hazard is closed
  in the code — my probe passes on the shipped tree.
- **A4's placement is right.** In all three terminal commands the
  `create_instant_task(… PROCESS_ITEM_COST_RESULT …)` sits at the same indent
  as `target_user_ids = …`, after the `if target_user_ids:` block, inside
  `maybe_begin`. My zero-notification-target probe proves it fires when no
  notification does.
- **R17-1 is honoured.** Both status services load the result row whenever one
  exists (not gated on terminal), and both serializer variants carry
  `task_state_snapshot` + `computed_at` — the boundary label.
- **P-E as amended holds.** `add_task_steps.py`'s diff is the `await` and the
  new keyword arguments only; `process_step_transition.py`'s only addition is
  task 4's guarded re-emit, gated on `payload.credited_user_id` and
  `closing_state in TIME_BEARING_STATES`, placed after
  `_recompute_step_time_totals` and before the commit, exactly per A17-L23.
- **`infeasible` yields a null percent by construction** —
  `calculate_percent_consumed` returns `None` for `allowed <= 0`, so C7's
  null-numerics clause cannot be violated by the evaluated branch.
- **The straggler guard is behaviourally correct**: READY → 1 emit,
  RESOLVED → 1, WORKING → 0 (probe, exact counts).
- **`item_binding` produces all three values correctly**, and the status keeps
  `evaluation.item_id` across a PRIMARY swap (probe).
- **`_load_preview_inputs` and `_load_live_inputs` agree field-for-field**
  today (probe, with the non-vacuity assertions A10 requires).
- 4B N4 applied: `status is EconomicsStatusEnum.OK` replaces the string
  compare.

## Preserved probe artifacts (adoption-fidelity)

Path: `docs/architecture/under_construction/implementation/item_cost_calculation/probes/reviewer_r1_phase8/`

| file | sha256 | rows |
|---|---|---|
| `test_reviewer_r1_phase8_probe.py` | `b5ac470c704e5f62be3d8752d7eb2b6f4e908469c5e944f764ee1a9d454abe3c` | **19, all green on the shipped tree** |

Row inventory: C10 terminal ×3 (zero-notification fixtures), C6b READY entry,
C6b reopen through `add_task_steps`, C8 binding ×1 (three assertions), C7
hazard, C7 priority, C1 discriminating ×1, C1 worker service ×1, C6 straggler
×3, A10 loader equality, C9 quantified disjointness, A15 re-resolution ×1
(both R17-2 rows), C11 snapshot, C9 route money boundary ×2.

The file was developed inside
`app/tests/integration/services/commands/item_economics/` and **removed from
the app tree** at session close; it runs unmodified when copied back to that
path. Its fixtures build on phase 7's `_fixture` / `_ctx` /
`_cleanup_committed_fixture`, and its `_cleanup` owns full teardown
(charter 11½) including the analytics stats tables, the READY-entry
side-effect instances, and the emitted execution tasks/payloads.

**Adoption note for the fix cycle:** adopt these rows *verbatim* — each one is
the arbiter for a named mutation, and every weakening listed in the ledger
above is exactly the shape that let the shipped rows pass. C2, C3, C6b
re-entry, C5 config-supersession, and the no-steps COALESCE row still need
building from scratch.

## Write perimeter (this session)

**Documents**
- `handoffs/reviewer/2026-08-14_phase8_review_r1_handoff.md` (this file, new)
- `plans/phase_8_status_results.md` (Review log append only)
- `master_plan.md` (tracker row 8 only)
- `probes/reviewer_r1_phase8/test_reviewer_r1_phase8_probe.py` (new artifact)

**Code:** none. All 19 phase production files carry their entry hashes at
session close; `git status` shows only the new probes directory.

**Mutation-probe declaration.** Files touched by an applied-and-reverted
mutation, each verified byte-identical afterwards:
`get_task_budget_status.py`, `get_task_budget_status_worker.py`,
`process_item_cost_result.py`, `delete_item_valuation.py`,
`_task_state_transitions.py`, `resolve_task.py`, `fail_task.py`,
`cancel_task.py`, `process_step_transition.py`,
`domain/item_economics/serializers.py`, `get_item_lifetime_economics.py`,
`routers/api_v1/item_economics.py`, `commit_item_cost_evaluation.py`.

**Database side effects.** The probes commit rows. Early probe iterations
whose teardown aborted on FK-ordering left residue; I removed it explicitly
and re-verified. Final state, by state query: `item_cost_evaluations` 0,
`item_cost_results` 0, `execution_tasks` where
`task_type='process_item_cost_result'` 0, `working_sections LIKE 'wsec_probe%'`
0, `task_steps LIKE 'tsp_probe%'` 0, `items LIKE 'itm_other_%'` 0, orphan
`execution_payloads` 0. Disposable database `beyo_manager_p8_rev_r1` created
and dropped. Configured DB at head `c1d2e3f4a5b6`.

**Architecture Graph.** Read-only, zero delta. 172 nodes / 254 edges,
revision `c74eb91304146d…`, 21 pending held for the coordinator's
post-approval pass, 1 stale node, no diagnostics. No promotion, rejection or
edit enacted.

## Lessons for the plans (coordinator folds upstream)

1. **A per-row deferral is compliant in form and worthless in substance when
   the whole ledger is deferred.** §9's deferral rule was written so a single
   awkward mutation could be pushed to review — not seventeen. The rule needs
   a cap: *a cycle may defer at most N rows, and never the rows guarding the
   phase's own named mechanism.* r1 deferred the ledger wholesale, r1b
   re-deferred it row by row, and the result is a phase whose central
   mechanism reached review with a 2-of-18 mutation score.

2. **"Named mutation" needs to name the arbiter too.** Every criterion here
   named a mutation and a site; none named *which test id must go red*.
   Where the plan did name a test (A13, A6) the mutation bit. Where it named
   only a site, the implementer wrote a test with the right name and no
   power. Criterion template: mutation site → **expected red node id**.

3. **A criterion that enumerates a vocabulary must enumerate its
   producers, and the plan must say the expression has to differ per row.**
   A1 said this in prose ("each row's EXPRESSION differing", "WHICH producer
   it exercises") and the shipped C7 still parametrized twelve identical
   serializer echoes. The enforceable form is structural: *no two rows of an
   enumerated criterion may share a call graph.*

4. **Money-boundary criteria must name the endpoint, not the serializer.**
   C9/A9 were satisfied at the serializer and left the route unguarded —
   M18 walks straight through. Phase 1 learned this at eight endpoints; the
   lesson did not travel because the criterion was phrased about a payload
   rather than about a response.

5. **A structural arbiter derived from the thing it audits is not an
   arbiter.** A6's `_MANAGER_ONLY_ROUTES` is computed from `router.routes`.
   The planner should state that completeness tables are **hand-written
   literals** — that is the whole mechanism.

6. **Record where a criterion's only integration path is already red.** A3's
   reopen change landed on `test_adding_a_batch_of_steps_reopens_ready_task`,
   a baseline failure. The plan should flag "this touch point's existing
   coverage is in the failing set" so the implementer knows a new row is
   mandatory, not optional.

## Human-authorization backlog

- The 21 pending graph reviews (r1's inferred delta) plus the migration
  mapping remain for the coordinator's post-approval pass. Not touched.
- The three A16 discrepancy filings under
  `archGraph_mapping_mantainance/open/` remain open for the maintenance
  channel.

Neither needs an owner decision now; both are recorded so they cannot
evaporate.
