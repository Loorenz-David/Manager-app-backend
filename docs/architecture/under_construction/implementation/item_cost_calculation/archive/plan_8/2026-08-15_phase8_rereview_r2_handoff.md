---
plan: phase 8 — status & results
role: review
round: 2
verdict: CHANGES_REQUESTED
date: 2026-08-15
actor: Claude Opus 5 (plan-reviewer)
---

# Phase 8 re-review r2 handoff

## Review history (what earlier rounds settled)

- **r1 (2026-08-14): CHANGES_REQUESTED**, 7 blocking / 6 should-fix / 7 notes.
  Verdict was "production correct, proof vacuous": every mechanism re-derived
  clean, but only **2 of 18** named mutations turned the shipped suite red. I
  built 19 probe rows; 16 of 18 mutations then bit.
- **fix r1 (2026-08-15, checkpoint `0c85707`)**: adopted the probe file
  byte-identically, rebuilt C7 on real producers, built the from-scratch
  families, made exactly the five production corrections (G4–G8), and ran the
  full 19-row ledger with zero deferrals.

This round is delta-scoped: verified perimeter, then full adversarial depth on
the changed seam, bounded regression on dependents, settled areas untouched
except where something looked wrong in passing.

## Verdict: CHANGES_REQUESTED — 2 blocking / 3 should-fix / 6 notes

**Twelve of the thirteen r1 findings are closed, and closed by the arbiter that
was absent-or-green in r1.** The fix is high quality: every one of the 19
declared mutations bites, the perimeter is exact, the numbers reproduce, and
the five production corrections are right.

Two blockers remain, both found by mutations **I added this round** (the
passing-glance clause), both the same shape r1 blocked on — a named contract
whose arbiter cannot fail:

- the `ok`/`infeasible` half of C7 is still a serializer echo, and the producer
  A1 names by hand survives being replaced with a constant;
- §8A.1's "pause and ended-shift seconds are never read" clause has no
  discriminating fixture anywhere, so billing paused time as consumption is
  invisible.

Neither is a shipped defect. Both are one-fixture fixes.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. Both blockers are test-side; no semantic decision is
open.

## Verified perimeter

`git diff 0c85707..HEAD -- app/` empty. Exactly the four declared production
files changed; **fifteen phase-8 production files verified byte-identical to
their r1 entry hashes** (`shasum -c` against my own r1 record: 15 OK, 4
expected FAILED). Nothing moved outside the fence.

| file | sha256 | vs declared |
|---|---|---|
| `routers/api_v1/item_economics.py` | `799d205d432435ffb6a88eead011803a698e157df44a0ab43c3e8a31739dc15a` | matches coordinator |
| `commands/item_economics/delete_item_valuation.py` | `a9a987d7b230dd6605079ca2b868e34380bf3825c1f78d8f17165227ad9d9d7c` | matches |
| `queries/item_economics/get_item_lifetime_economics.py` | `1f26eecaaeeb6df153316640d99e1d067aed69844e418d13c93efbd0e7cf315e` | matches |
| `queries/item_economics/get_task_budget_status.py` | `5f89e29b695ea13f13666ecb5ff9e315fdf61e2e745f61ca8cba48a90a68bde8` | matches |
| adopted probe (in tree) | `b5ac470c704e5f62be3d8752d7eb2b6f4e908469c5e944f764ee1a9d454abe3c` | **identical to my preserved r1 source** |

The six restoration hashes in the fix ledger match r1b's finals byte-for-byte
(I recomputed all fifteen unchanged files, not just those six).

## Numbers (re-derived, not taken on trust)

- Full non-E2E suite, foreground, by me: **2138 passed / 23 failed / 1
  deselected**, 130.93s — matches the declaration exactly.
- Failure set **byte-compared** (sorted `diff`) against the phase-1 list:
  **byte-identical, zero drift**.
- **+27 reconciled exactly** against `--collect-only`: probe file 19 (new) +
  `test_phase8_status_results.py` 8→14 (+6) + router 96→98 (+2) +
  serializers 15→15 (12 C7 rows → 10 producer rows + 2, net 0).
- Focused scope (the 11-path arbiter set): **427 passed / 2 failed**, both
  established baseline members (#5, #6).
- `ruff check` on the fix perimeter: clean. Repo-wide 123 pre-existing findings
  confirmed out of scope.
- DB left at head `c1d2e3f4a5b6`; zero item-economics residue by state query
  (`item_cost_evaluations` 0, `item_cost_results` 0,
  `execution_tasks[process_item_cost_result]` 0, probe sections/steps/records 0).
- Graph: **read-only, zero delta** — 172 nodes / 254 edges, rev
  `c74eb913…`, 21 pending. I checked the zero-delta claim rather than
  accepting it: G5 deleted a production block that was **dead code and never a
  node**, and G6 moved a call **inside** existing nodes. No boundary added or
  removed; zero delta is correct.

## r1 finding closure

| r1 id | verdict | evidence |
|---|---|---|
| **B1** five §8B.1 emission points | **CLOSED** | M5/M6/M7/M8/M9 each redden exactly their named probe row and nothing else; all five mutant hashes reproduce r1's byte-for-byte (files unchanged) |
| **B2** straggler + READY half | **CLOSED** | M10 reddens both straggler rows; M11 reddens **only** `[C6-straggler-READY-half]` — the round-6 half is separately arbitrated |
| **B3** three C1 filters | **CLOSED behaviourally** | M1/M2/M3 all bite their named rows. The arbiter row is intermittently red on a clean tree — new **S1**, a defect in my own r1 probe |
| **B4** C7 vacuous | **PARTIALLY CLOSED** | ten readiness members now drive `resolve_item_economics_status` with per-row differing fixtures; M12 bites. The two members A1 names — `ok`/`infeasible` — are still hand-built echoes → new **B1** |
| **B5** C9 both sites | **CLOSED** | M13 reddens the disjointness row **and** both route-money rows; M18 reddens both route rows |
| **B6** A15 re-resolution | **CLOSED** | M4 reddens `test_probe_a15_delete_valuation_reresolves_the_status` |
| **B7** C2/C3 zero rows | **PARTIALLY CLOSED** | both criteria now have real rows built from scratch. C2-as-worded is satisfied; §8A.1's sibling clause is not → new **B2**. C3 uses one task → **S3** |
| **S1** A17 predicate | **CLOSED** | `include_monetary_step_fields` at `:134`; fail-closed row drives `_run_budget_status` with a fabricated role and asserts the worker service; M15 still bites |
| **S2** dead route tables | **CLOSED** | production block deleted (zero grep hits). M16 now reddens `test_router_route_pairs_match_the_authoritative_route_table` — the hand-written-literal arbiter does its job |
| **S3** dead serializer | **CLOSED** | `get_item_lifetime_economics` calls `serialize_item_lifetime_economics` |
| **S4** duplicated read model | **CLOSED** | one `_build_evaluated_status`; both services call it; the per-service literal filters correctly stay separate (A7 preserved — M1 and M2 still bite independently) |
| **S5** `response_model` row | **CLOSED** | row exists and **bites** (I probed it: `response_model=dict` reddens it). Scoped to the one route → **N2** |
| **S6** soft-deleted item | **CLOSED** | `ITEM_UNVALUED` branch; the G8 mutation (restore the raise) reddens its row |

## New findings

### B1 (blocking) — C7's `ok`/`infeasible` producer has no arbiter

`test_c7_committed_evaluation_branch_drives_evaluated_status` builds a
`SimpleNamespace` with `status` already set to `OK`/`INFEASIBLE` and asserts
the serializer echoes it — **exactly the r1 B4 shape, preserved for the two
members A1 singles out.** A1 (GOVERNING): "*those two come ONLY from the
committed-evaluation branch (evaluation present → `infeasible` iff
`allowed_worker_minutes <= 0` else `ok`)*"; G2 required every row to drive its
real producer.

**Mutation MX2** (mine): in `get_task_budget_status.py`, replace
`status = EconomicsStatusEnum.INFEASIBLE if allowed <= 0 else EconomicsStatusEnum.OK`
with `status = EconomicsStatusEnum.OK`.
sha256 `5f89e29b…bde8` → `57c4591f8d21fbdb5940cc9262012d0d41f33465e47a05c96ffd98ec23d2c140`.
**Focused scope stays at baseline — nothing reddens.** The "`infeasible` ⇒
`percent_consumed` null" clause rides on the same hand-built object and is
equally unarbitrated on the production path.

*Correction:* one integration row driving `get_task_budget_status` against a
committed evaluation with `allowed_worker_minutes <= 0`, asserting
`status is INFEASIBLE` and `percent_consumed is None`, plus its `> 0`
counterpart asserting `OK`. The probe's `_committed_fixture` already gives the
scaffolding.

### B2 (blocking) — §8A.1's "pause / ended-shift / inaccurate are never read" has no discriminating fixture

Intention §8A.1: "*`inaccurate_*` is never read … `total_pause_seconds` and
`total_ended_shift_seconds` are never read (R-5)*". Every phase-8 consumption
fixture carries **zero** pause, ended-shift and inaccurate seconds, so no row
can tell the correct read from a wrong one.

**Mutation MX1** (mine): in `process_item_cost_result.py`, sum
`TaskStep.total_working_seconds + TaskStep.total_pause_seconds`.
sha256 `d57ca890…5172` → `fdae3c4106686398559c4c50574b9653d4b0a5d26f80e430f42dfa9f87b490b7`.
**Focused scope stays at baseline — nothing reddens.** Paused time would be
billed against the production budget, silently overstating consumed cost and
understating remaining minutes on every episode with a pause.

To be fair to the fix cycle: **C2 as literally worded is satisfied** — the new
`test_c2_rollup_separates_working_paused_ended_shift_and_marked_wrong` proves
each real ORM record lands in its own rollup column (A12's `PAUSED` +
`SHIFT_ENDED` construction and the marked-wrong →
`inaccurate_working_seconds` split are both asserted). What is missing is the
step from those columns into the phase-8 read.

*Correction:* extend one consumption row's step with nonzero
`total_pause_seconds` / `total_ended_shift_seconds` / `inaccurate_working_seconds`
and assert `result.actual_worker_seconds` equals the working seconds alone.
One fixture edit closes it and makes MX1 bite.

### S1 (should-fix) — the adopted C1 probe row is intermittently red on a clean tree

**This is a defect in my own r1 probe; the fix cycle adopted it verbatim
exactly as G1 instructed and is not at fault.**

`test_probe_c1_projection_isolation_with_a_discriminating_fixture` asserts
`unfiltered[0].client_id == projection[...]` over a `SELECT … WHERE task_id = …`
with **no `ORDER BY`**. PostgreSQL is free to return heap tuples in any order.
Observed failing on an unmutated tree:

```
E  AssertionError: fixture must place the PROJECTION first so an UNFILTERED read picks it
E  assert 'ice_01M01XGHNXAGKXKXMHNMENPX5R' == 'ice_01M01XGHPQPB4WN9TTYCEF7ETY'
```

(the committed row came back first even though the projection was inserted
first — note the lower ULID on the committed row is the *later* insert.)
Frequency: 3 reds in ~25 wide-scope runs, **at least two on a clean tree**
(runs `flake_5`, and one earlier run under an unrelated test-file mutation
that does not reproduce).

The failure mode is a **false positive, not a missed mutation** — under M1/M3
the row reddens in *both* heap orders, so the arbiter's power is intact, and
the guard firing is it correctly reporting that the fixture has stopped
discriminating. But an intermittently-red row corrupts the byte-identical
baseline discipline every later phase gates on (same class as phase-2 N14).

*Correction:* make the discrimination order-independent — assert over the
candidate **set** (the unfiltered predicate admits both rows; the literal
committed-current predicate admits exactly one, the committed row) rather than
over `scalar()`'s arbitrary pick, keeping a behavioural assertion on
`status.evaluation_id`. The same applies to the sibling
`test_probe_c1_worker_service_filter_is_independent_and_projection_blind`,
which carries the identical guard.

### S2 (should-fix) — the C5 config-supersession row cannot fail

`test_c5_config_supersession_after_close_preserves_snapshot_recompute`
soft-deletes a `CostModelVersion` and asserts the result row is unchanged. The
handler's entire call graph reads `Task`, `ItemCostEvaluation` and `TaskStep`
— **no configuration table at all** (verified by grep over
`process_item_cost_result.py`: zero hits for `CostModel`, `ProductionCost`,
`Basis`, `_load_preview`, `configuration`). The row therefore cannot fail
whatever the handler does with config, and it has no non-vacuity arbiter
(P-J 3rd ext).

Separately, "supersession" in §8.4 means a **new version superseding an old
one** — the scenario is "someone commits new configuration after the episode
closed; the stored result must not drift". A soft delete is the phase-4/5
delete path, not supersession, so the row does not exercise §8.4 either.

*Correction:* commit a superseding basis/model version with a **different
rate** after the close, re-run the handler, assert the §8A.4 column set is
byte-identical, and add the non-vacuity assertion that the new live
configuration really would have produced a different number.

### S3 (should-fix) — C3 dilutes across one task, not two

C3: "*one worker, two batchable steps on **two tasks**, full overlap → each
episode consumes exactly half the wall clock; Σ = wall clock*". Both steps in
`test_c3_batch_rollup_dilutes_two_overlapping_steps_to_wall_clock` carry
`task_id=task.client_id` — one task. The dilution arithmetic is proven
(`[1800, 1800]`, Σ = 3600 = wall clock); the **flow-through into two separate
episodes** — which is what the criterion is named for and what the phase-8
consumption read consumes — is not. With both steps on one task that episode
consumes the full 3600, so the "each episode consumes half" claim is untested.

*Correction:* put the second step on a second task with its own committed
evaluation and assert each episode's `actual_worker_seconds` is 1800.

### Notes

- **N1** — C6b re-entry's single-row claim uses
  `scalar(select(ItemCostResult.task_id).where(...))`, which returns the first
  row and cannot detect a second. True anyway via
  `uq_item_cost_results_task_id`; use a count if the claim is meant to bind.
- **N2** — G7's structural row asserts `response_model is None` for the
  budget-status route only; A17 worded it "over `item_economics.router.routes`".
  It bites (verified), so this is scope, not power.
- **N3** — the fix handoff cites **no per-row mutant hashes** (restoration
  hashes only), against P-I 9th. My independent re-run confirms every row
  behaviourally, and for the fifteen unchanged files my r2 mutant hashes
  **reproduce r1's byte-for-byte**; for the four changed files they necessarily
  differ because the pre-image changed. Record-quality note, not a defect —
  but the next cycle should carry them.
- **N4** — r1's N2 (arbiter placement) is materially resolved: the route-money
  rows guard the production path end-to-end (M13 and M18 both redden them).
  `serialize_item_cost_result_worker` still has only a test caller; harmless.
- **N5** — the probe runs in place: **19 collected, 19 green**, all parametrize
  ids preserved (`C10-terminal-{resolve,fail,cancel}`,
  `C6-straggler-{RESOLVED,READY-half,WORKING-none}`, `route-{worker,seller}`) —
  byte-identity guarantees the P-V mapping reads exactly as authored.
- **N6** — `user_section_daily_work_stats` holds 881 rows, **zero orphaned**
  (every row's workspace still exists): the known wider-suite residue class
  (§10 / phase-4 N11, maintenance prompt already filed). The new C2/C3 rows
  clean their own workspaces through the adopted `_cleanup`.

## Mutation ledger — all 19 declared rows re-run, plus 2 of mine

Scope: the same 11-path focused arbiter set as r1. **Baseline 427 passed / 2
failed** (established #5, #6). "Bites" = a new red beyond that set. Every row
reverted with `git checkout --`; tree verified clean and all five perimeter
hashes recomputed identical at close.

| # | site | sha256 before → mutated | observed red | vs r1 mutant hash |
|---|---|---|---|---|
| M1 | manager committed filter | `5f89e29b…bde8` → `3a659e93e75a134df29540b956f72028686b04bb070325dbf6e856ca9bf95c3a` | `…probe::test_probe_c1_projection_isolation_with_a_discriminating_fixture` | differs (file changed by G6) |
| M2 | worker committed filter | `011cf2ae…7f00` → `783698f82ff07ae145b31266569ebd3014049ac3eea07c82ca57f3b8b66a29d0` | `…test_probe_c1_worker_service_filter_is_independent_and_projection_blind` | **reproduces** |
| M3 | handler committed filter | `d57ca890…5172` → `14bb672db9e6c5b2fb3e0deb87b70e80df71452e5e5b97ced3fb0f3628ded095` | `…test_probe_c1_projection_isolation_…` | **reproduces** |
| M4 | A15 re-resolution | `a9a987d7…9d7c` → `124fecf61727819f96f43fd2750506b30b9e4ea46a74b001771b523f11deb62a` | `…test_probe_a15_delete_valuation_reresolves_the_status` | differs (G8 changed the file) |
| M5 | READY-entry emit | `728e7770…073c` → `8c41cb441ff79dab86d84e0ea94f5c494b0588010f40eb592ee355f98072c1c5` | `…test_probe_c6b_ready_entry_writes_ready_snapshot_with_null_closed_at` | **reproduces** |
| M6 | reopen emit | `728e7770…073c` → `9d0664bc47a163cc3d354ed01c1654b7454e2b7b2962b20b70070e5bbb5cc0c6` | `…test_probe_c6b_reopen_through_add_task_steps_flips_snapshot_to_working` | **reproduces** |
| M7 | resolve emit | `f5d9e23f…4cb4` → `cffa4f035cd7eb3825cd3e21ce963b534081548d8cfadb23b1b8199de49d1331` | `…[C10-terminal-resolve]` | **reproduces** |
| M8 | fail emit | `bceb0768…cede` → `4d72d3ae5eee889fea649e839f72c44a501f1d7259157b9f6603e5854dc2b590` | `…[C10-terminal-fail]` | **reproduces** |
| M9 | cancel emit | `97de30b2…a438` → `b4bf6a52ca5858e9f0cac1c4f882810dd1b7c64871658a6bba24ecbcd288cdda` | `…[C10-terminal-cancel]` | **reproduces** |
| M10 | straggler branch | `fe1091c6…7e80` → `71f50c47e0d070d776b4d0b43d043e4d5a23534abee23a2e8cf6cad1e3c567fd` | `[C6-straggler-RESOLVED]` **and** `[C6-straggler-READY-half]` | **reproduces** |
| M11 | straggler READY half | `fe1091c6…7e80` → `b4bc929b0d1508e17283e091fd6d6d0e596e728cd307e5421e02740e1ef1a35f` | `[C6-straggler-READY-half]` only | **reproduces** |
| M12 | C7 selection-status swap | `5f89e29b…bde8` → `bb0e01845aae8c7aabfc060e742824707aae2e44f2894b9806b37585cfd7aede` | `…test_probe_c7_hazard_selection_ok_without_committed_evaluation_reads_not_evaluated` (+ C1 row, S1 flake) | differs (file changed) |
| M13 | `total_cost_minor` injection | `12d6e36a…3f88` → `f97fd2253b8fee71cad314d279f96465ae7b0abfec90b4883192ca0763bcd4c2` | disjointness row **+ both route-money rows** | **reproduces** |
| M14 | lifetime snapshot substitution | `c497e208…3fd9`¹ → `47e645dab4bb623df0be85d87c5c40c525ea5bd56e47935bc07a43cbe2efba19` | `…test_probe_c11_lifetime_uses_evaluation_snapshot_not_the_live_task_field` | differs (file changed) |
| M15 | WORKER route authorization | `799d205d…c15a` → `f9bfed7067897d0392807cb2873f8ea109fb700ca15ccc2e105f3eaf7a324e89` | `test_budget_status_route_is_available_to_all_roles[get-budget-status-worker]` **+** `[route-worker]` | differs (file changed) |
| M16 | test route-table budget row | `c61c95c3…79c5` → `e2585353276beede4f5dd90ac5f7fa299c4c6141ab23f50bdbfe72edfab49073` | `test_router_route_pairs_match_the_authoritative_route_table` | new (r1: unbiteable) |
| M17 | `computed_at` update removal | `d57ca890…5172` → `1929a4c07c8c7bf9c01167a4a4a8da3dd151cb184619701e9cab3a6215b4f512` | `test_c5_replay_updates_only_computed_at_and_converges` | **reproduces** |
| M18 | worker manager-payload | `799d205d…c15a` → `6c32a7f4525cba70f9ca590e350ca39b81bd4877188a4be42d495274dd9a1d79` | `[route-worker]` **and** `[route-seller]` | differs (file changed) |
| G8 | restore the `NotFound` raise | `a9a987d7…9d7c` → `8695a69dd4eee30f1e176a1b2f5734fd522ca7df7bd7af58feb8055c27d9b1e5` | `test_g8_delete_valuation_on_soft_deleted_item_returns_item_unvalued` | new |
| **MX1** | pause seconds summed into §8A.1 | `d57ca890…5172` → `fdae3c41…b490b7` | **NONE — survives** | new (B2) |
| **MX2** | `ok`/`infeasible` producer constant | `5f89e29b…bde8` → `57c4591f…d2c140` | **NONE — survives** | new (B1) |
| G7 | `response_model=dict` | `799d205d…c15a` → `3ca43a9a3cf0f230aa5e97368e0fb13a3142ea25567c8b74894afb46b5d07994` | `test_budget_status_route_declares_no_response_model` | new |

¹ M14 is applied after a prerequisite helper edit (`m14b`), so its pre-image is
the intermediate file; the restored file hashes back to `1f26eeca…c315e`.

**Score: 19 of 19 declared rows bite. 2 of 2 mutations I added survive.**

## Row-coverage map (delta only — settled rows carried from r1)

| criterion row | arbiter | verdict |
|---|---|---|
| C1 manager / handler / worker filters | probe rows ×2 | ✔ (S1: intermittently red) |
| C2 four buckets (A12 constructions) | `test_c2_rollup_separates_…` | ✔ as worded |
| §8A.1 pause/ended-shift/inaccurate never read | — | **B2** |
| C3 batch dilution | `test_c3_batch_rollup_dilutes_…` | partial → **S3** |
| C4 no-steps → 0 COALESCE | `test_c4_no_steps_coalesces_consumption_to_zero` | ✔ |
| C5 replay identity + `computed_at` | `test_c5_replay_…` (M17) | ✔ |
| C5 config supersession | `test_c5_config_supersession_…` | **S2** (vacuous) |
| C6b re-entry (§8B.3) | `test_c6b_reentry_recomputes_…` | ✔ (N1) |
| C7 ten readiness members | `test_c7_readiness_producer_drives_each_status_exactly[…]` (M12) | ✔ |
| C7 `ok` / `infeasible` | `test_c7_committed_evaluation_branch_…` | **B1** (echo) |
| G4 fail-closed audience | `test_budget_status_audience_predicate_fails_closed_for_unknown_role` | ✔ |
| G5 hand-written route table | `test_router_route_pairs_match_…` (M16) | ✔ |
| G7 `response_model is None` | `test_budget_status_route_declares_no_response_model` | ✔ (N2) |
| G8 soft-deleted item | `test_g8_delete_valuation_on_soft_deleted_item_…` | ✔ |
| all r1-probe rows | 19 in place, green | ✔ |

## Write perimeter (this session)

**Documents**
- `handoffs/reviewer/2026-08-15_phase8_rereview_r2_handoff.md` (this file, new)
- `plans/phase_8_status_results.md` (Review log append only)
- `master_plan.md` (tracker row 8 only)

**Code:** none. All four changed production files, the eleven other phase-8
production files, and the adopted probe carry their entry hashes at session
close; `git status` shows no `app/` change.

**Mutation-probe declaration.** Applied-and-reverted, each verified
byte-identical afterwards: `get_task_budget_status.py`,
`get_task_budget_status_worker.py`, `process_item_cost_result.py`,
`delete_item_valuation.py`, `_task_state_transitions.py`, `resolve_task.py`,
`fail_task.py`, `cancel_task.py`, `process_step_transition.py`,
`domain/item_economics/serializers.py`, `get_item_lifetime_economics.py`,
`routers/api_v1/item_economics.py`, and — for M16, by design — the test file
`tests/unit/routers/api_v1/test_item_economics_router.py`.

**Database side effects.** The suite and probes commit rows and clean up after
themselves this cycle: final state by state query is zero item-economics
residue (evaluations 0, results 0, result execution-tasks 0, probe
sections/steps/state-records 0). No disposable database created this round (no
migration changed). Configured DB left at head `c1d2e3f4a5b6`.

**Architecture Graph.** Read-only, zero delta, claim independently checked.
172 nodes / 254 edges, revision `c74eb913…`, 21 pending held.

## Carry-forward dispositions

Not an approval, so these stay held rather than dispatched — recorded so they
cannot evaporate across the next round:

| item | destination |
|---|---|
| 21 pending graph items + migration mapping | coordinator's post-approval graph pass |
| three A16 discrepancy filings (`archGraph_mapping_mantainance/open/`) | maintenance channel |
| the two status queries' node-type question | post-approval graph pass |
| three `alembic check` drifts | only-if-cheap ledger (routed, unchanged) |
| baseline failure #5 (`test_adding_a_batch_of_steps_reopens_ready_task`) | pre-existing; the adopted reopen probe row is the phase's green (r1 N1) |
| `user_section_daily_work_stats` residue class | existing maintenance prompt (phase-4 N11) |

**Anchor spans:** the four changed production files were checked against the
21 held graph items — none of the held items anchors in
`item_economics.py`, `delete_item_valuation.py`,
`get_item_lifetime_economics.py` or `get_task_budget_status.py` in a way this
fix moved; the phase-8 nodes are the newly inferred ones whose spans were
recorded at r1's checkpoint and whose files are unchanged. No anchor service
owed this round.

## Lessons for the plans

1. **"Rebuild the criterion on real producers" needs a per-row completeness
   check.** G2 was followed for ten of twelve members and the two that were
   left as echoes are precisely the two A1 called out by name. When a fix
   instruction says "every row", the fix prompt should carry the row list and
   the fixer should tick it — otherwise the rows that are hardest to build are
   exactly the ones that stay decorative.
2. **A criterion about a *pipeline* needs a row at each end.** C2 proved the
   rollup columns separate and stopped there; the clause that matters for money
   (§8A.1 reads only the working column) sits one step downstream and had no
   fixture anywhere. Enumerate criteria along the data path, not by mechanism
   name.
3. **Non-vacuity applies to "nothing changed" rows too.** The C5 supersession
   row deletes a row nothing in the call graph reads. A criterion asserting
   *stability* must prove the perturbation would otherwise have been visible —
   the same P-J discipline already applied to positive rows.
4. **A fixture that depends on physical row order is not a fixture.** My own
   C1 probe guard rests on unordered heap order; it fails safe but it flakes,
   and a flaky row is corrosive in a project that gates on byte-identical
   failure sets. Discriminating fixtures should be asserted over candidate
   **sets**, never over an unordered `scalar()`'s pick. (Earned against
   myself.)
5. **Per-row mutant hashes are what make a ledger re-derivable.** The fix
   recorded restoration hashes only; I could confirm every row behaviourally,
   but reproduction had to be re-established from scratch rather than compared.
   P-I 9th should be restated as a hard field in the ledger template.
