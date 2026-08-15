---
plan: phase 8 — status & results
role: review
round: 3
verdict: APPROVED
date: 2026-08-15
actor: Claude Opus 5 (plan-reviewer)
---

# Phase 8 re-review r3 handoff

## Review history (what earlier rounds settled)

- **r1 (2026-08-14): CHANGES_REQUESTED**, 7 blocking / 6 should-fix / 7 notes.
  "Production correct, proof vacuous" — every mechanism re-derived clean, but
  only 2 of 18 named mutations turned the shipped suite red.
- **fix r1 (`0c85707`)**: adopted the 19-row probe verbatim, rebuilt C7 on real
  producers, built the from-scratch families, five production corrections.
- **r2 (2026-08-15): CHANGES_REQUESTED**, 2 blocking / 3 should-fix / 6 notes.
  12 of 13 r1 findings closed; all 19 declared mutations bite. The two blockers
  were mutations *I* added (MX1, MX2) that survived; all five findings test-side.
- **fix r2 (checkpoint `6988364`)**: the H1–H7 list, test-side only, zero
  production edits.

This round is a THIN delta review per the r3 prompt. The 15 ledger rows proven
biting in r2 against production files that are byte-identical today (M4–M16,
M18, G7/G8) were **not** re-run — declared out of scope. Settled r1/r2 mechanism
re-derivations stand.

## Verdict: APPROVED — 0 blocking / 0 should-fix / 4 notes

Every correction bites. Both r2 blockers are closed by the exact mutations that
survived last round, re-applied from **my own r2 mutant bytes** — and the fix's
ledger hashes reproduce those bytes, so the record is now re-derivable rather
than merely re-confirmable (r2 N3 / P-I 9th closed). The three should-fixes are
closed, the two ride-along notes are closed, and the H-list is ticked honestly:
every claim I tested held.

Three mutations I added this round **also** bite, which is why this is an
approval rather than a pass-by-checklist: the fix is stronger than its
acceptance condition required. C7 now enumerates all twelve shipped enum members
with both producers real — the first round in which A1 is actually satisfied.

The four notes are carry-forward only. The most interesting (N1) is a defect in
**my own r2 specification**, not in the fix: H3's repair, executed exactly as I
wrote it, leaves M1/M2/M3's bite contingent on physical row order. It bites
62/62 today; the structural repair is named below and routed forward.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. No semantic decision is open; all four notes are
technical carry-forwards.

## Verified perimeter

`git diff 6988364..HEAD -- app/` **empty** — the working tree's `app/` is
byte-identical to the checkpoint. All seven hashes declared in the fix handoff
recomputed identical at session entry, and the five production files I mutated
recomputed identical at close.

| file | sha256 | vs declared |
|---|---|---|
| `services/tasks/analytics/process_item_cost_result.py` | `d57ca890d0ad9b14eb09bdda339e07cfe94e3a20475621ca640e61a11e2e5172` | matches |
| `services/queries/item_economics/get_task_budget_status.py` | `5f89e29b695ea13f13666ecb5ff9e315fdf61e2e745f61ca8cba48a90a68bde8` | matches |
| `services/queries/item_economics/get_task_budget_status_worker.py` | `011cf2ae76dde81fe837a1f7b5f8a869230621001c64af06feb7718951970f00` | matches |
| adopted probe (test) | `7df683f793d996a0869f9360b153ff56578c85b7df3d6d6881aae95ad026fbfb` | matches |
| `test_phase8_status_results.py` | `adef4c5b2de9bf40dc95488a233509bcfce7a9ea0694afcaf79eed13202ec53c` | matches |
| `test_phase8_serializers.py` | `683ba963b475ad3bbbc2ab0961af7b490c510dabca65f699c008b861c7fe3dc5` | matches |
| `test_item_economics_router.py` | `cba1fed45366100bdecd6734f6ad5db7a92ed3acb458f91dad24fce99e4529c3` | matches |
| `routers/api_v1/item_economics.py` (my probe only) | `799d205d432435ffb6a88eead011803a698e157df44a0ab43c3e8a31739dc15a` | restored |
| `domain/item_economics/calculator.py` (my probe only) | `03389d0a2743ae7968a0e5aecc88cc5b2675bea6762c2b9bbec2d87662af8eb0` | restored |

H7 holds: the checkpoint is four test files plus two docs, and no production
file, migration, or graph record moved.

## Closure table — r2's 2 blocking / 3 should-fix

| r2 id | verdict | evidence |
|---|---|---|
| **B1** C7 `ok`/`infeasible` producer unarbitrated | **CLOSED** | MX2 re-applied from my r2 bytes (hash reproduces) reddens `[P-V-infeasible]` with `assert 'ok' == 'infeasible'`; `[P-V-ok]` correctly stays green. The rows drive the real `get_task_budget_status` against a committed evaluation — no `SimpleNamespace`. The null-percent half is closed too (MX3 below). |
| **B2** §8A.1 excluded columns had no fixture | **CLOSED** | MX1 re-applied from my r2 bytes (hash reproduces) reddens `test_c4_…skipped_steps` with `assert 150 == 120`. The fixture carries all three nonzero columns, and each discriminates independently (MX1b/MX1c below). |
| **S1** C1 probe intermittently red | **CLOSED** | Both rows now assert candidate SETS; **zero** order-dependent picks remain in the probe file (grep). Pair ran 10× → 20/20 green. Arbiter power intact: M1/M2 redden their named rows in 62/62 row-executions. See N1 for the residual. |
| **S2** C5 supersession row vacuous | **CLOSED** | Real supersession: `create_production_cost_basis_version` closes the open version (`effective_to = effective_from`) — I read the command, not the claim. Different rate (fixed monthly cost 200000), and two non-vacuity assertions: new rate ≠ snapshot rate, and recomputing at the new rate WOULD change `consumed_cost_minor`. See N2. |
| **S3** C3 diluted across one task | **CLOSED** | Second step on a second `Task` with its own committed evaluation, both WORKING; asserts `{result.actual_worker_seconds} == {1800}` and Σ == 3600 over the two result rows — the per-episode flow-through, not just the rollup arithmetic. |
| **N1** re-entry `scalar()` | **CLOSED** | `select(func.count()).select_from(ItemCostResult).where(task_id == …) == 1`. |
| **N2** G7 scoped to one route | **CLOSED** | `all(route.response_model is None for route in item_economics.router.routes)`, and it **bites on a different route** — I set `response_model=dict` on `/configuration-status` and it reddened. The widening is real, not cosmetic. |
| **N3** no per-row mutant hashes | **CLOSED** | The fix ledger carries the mutant-hash column; MX1/MX2/M1/M2 all reproduce my r2 bytes exactly. P-I 9th satisfied as a hard field. |

## Mutation ledger — 4 re-runs from my own r2 bytes + 3 I added

Scope: the named focused rows. Every row applied, observed, reverted with
`git checkout --`, and hash-verified. Tree clean at close.

| # | site | sha256 before → mutant | observed red | vs r2 |
|---|---|---|---|---|
| MX1 | `process_item_cost_result.py`: `+ TaskStep.total_pause_seconds` | `d57ca890…5172` → `fdae3c4106686398559c4c50574b9653d4b0a5d26f80e430f42dfa9f87b490b7` | `test_c4_consumption_excludes_deleted_steps_but_counts_skipped_steps` — `assert 150 == 120` | **reproduces** (survived in r2) |
| MX2 | `get_task_budget_status.py`: status ternary → constant `OK` | `5f89e29b…bde8` → `57c4591f8d21fbdb5940cc9262012d0d41f33465e47a05c96ffd98ec23d2c140` | `…drives_evaluated_status[P-V-infeasible]` — `assert 'ok' == 'infeasible'` | **reproduces** (survived in r2) |
| M1 | manager committed filter deleted | `5f89e29b…bde8` → `3a659e93e75a134df29540b956f72028686b04bb070325dbf6e856ca9bf95c3a` | `test_probe_c1_projection_isolation_…` (behavioural `evaluation_id` assertion) | **reproduces** |
| M2 | worker committed filter deleted | `011cf2ae…7f00` → `783698f82ff07ae145b31266569ebd3014049ac3eea07c82ca57f3b8b66a29d0` | `test_probe_c1_worker_service_filter_…` | **reproduces** |
| **MX1b** | `+ TaskStep.total_ended_shift_seconds` | `d57ca890…5172` → `9a8fba5f5b34bcc9cedd9b100a6ebe9181eb53d67ddb0cbcc1e7a5b3ca304554` | same C4 row — `assert 160 == 120` | new (mine) |
| **MX1c** | `+ TaskStep.inaccurate_working_seconds` | `d57ca890…5172` → `c5fbe1a31da5d5449c89300f41aeb0a4ca51a6e746cb89a3212609c807ba3563` | same C4 row — `assert 170 == 120` | new (mine) |
| **MX3** | `calculate_percent_consumed`: return `Decimal("0.00")` instead of `None` for allowance ≤ 0 | `03389d0a…8eb0` → `86c0578fb850bd76c9507c93e9a26a92e346505c18da68190502b87b7f800fca` | `…[P-V-infeasible]` — `assert Decimal('0.00') is None` | new (mine) |
| **G7-probe** | `response_model=dict` on `/configuration-status` | `799d205d…c15a` → `b2cd60997ee0413133dcc9a3186045f1dcf08f1aac12fc04bda22429c0aeeca9` | `test_item_economics_routes_declare_no_response_model` | new (mine) |

**Score: 4 of 4 re-runs bite (both r2 survivors now dead); 4 of 4 mutations I
added bite.** MX1b/MX1c matter beyond the letter of H2: because the fixture uses
*distinct* nonzero values (30 / 40 / 50), the row does not merely detect "a wrong
column was summed" — it identifies **which** one. MX3 closes the half of B1 that
H1 did not name.

## Independently re-derived numbers

- Full non-E2E suite, foreground, by me: **2138 passed / 23 failed / 1
  deselected**, 123.18s — matches the declaration exactly.
- Failure set **sorted-diffed byte-for-byte** against the phase-1 23-item list
  (plan 1, S2 correction): **byte-identical, zero drift**.
- Collection **net 0**, reconciled per file: serializers 15→13 (the two echo
  ids), `test_phase8_status_results.py` 14→16 (the two producer ids), probe 19
  and router 98 unchanged. 2161 selected / 2162 collected.
- **C7 completeness re-checked against the shipped enum:** 12 members, 12
  parametrize ids — ten `resolve_item_economics_status` ids
  (`P-V-major-category`, `P-V-no-cost-group`, `P-V-ambiguous-cost-group`,
  `P-V-no-basis-version`, `P-V-no-cost-model-version`, `P-V-item-unvalued`,
  `P-V-expected-price`, `P-V-purchase-cost`, `P-V-currency`,
  `P-V-not-evaluated`) plus `P-V-infeasible` / `P-V-ok` on the committed branch.
- H3 subset: 10 runs × 2 rows = **20/20 green**, no flake.
- `ruff check` on the four-file perimeter: clean except the declared pre-existing
  `F401` (`ItemMajorCategoryEnum`) in the adopted probe — correctly untouched,
  since H3 authorized only two rows in that file.
- DB left at head **`c1d2e3f4a5b6`**; zero item-economics residue by state query
  (`item_cost_evaluations` 0, `item_cost_results` 0,
  `execution_tasks[process_item_cost_result]` 0). The 1 `item_valuations` and 1
  `production_cost_basis_versions` row present are **pre-existing non-orphaned
  dev data** (created 2026-08-14 21:24, before the checkpoint); `orphaned` counts
  are 0. `user_section_daily_work_stats` 889 (r2: 881), zero orphaned — the known
  phase-4 N11 class.
- Graph: **read-only, zero delta** — 172 nodes / 254 edges, rev
  `c74eb91304146d284be10e7eb88dbb26ddfa709daca9849bab0d489c7a966166`, stale 1,
  21 pending. Zero delta is correct by construction: no production file moved.

## Notes (carry-forward, none blocking)

### N1 — C1's mutation bite is now order-CONTINGENT (my own H3 spec's limitation)

Before the repair, the row reddened in *both* heap orders: the fixture guard
fired when the committed row came back first, the behavioural assertion when the
projection did. H3 (which I wrote) removed the guard and replaced it with a
candidate-SET assertion that is, by design, order-blind. That leaves
`status.evaluation_id == committed["client_id"]` as the only assertion that can
fail — and under M1/M2/M3 the mutated service does an unordered `scalar()` over
a candidate set that still contains the committed row. If the heap returns the
committed row, the service is accidentally right and the mutation **survives**.

Empirically it bites: 25 focused runs + 6 wide-scope (35-test) runs = **62/62
row-executions red, zero misses**. But r2 recorded the alternate order occurring
on a clean tree (3 reds in ~25 wide runs), so the miss is not hypothetical.

**This is not a defect in the fix** — H3's stated acceptance condition ("M1/M2/M3
must still bite") is verified, and the implementer executed the specification
faithfully. It is a limitation of the specification. The order-free repair is a
**structural** arbiter (plan-reviewer doctrine 3): assert that each of the three
services' compiled evaluation `SELECT` carries the three literal filter clauses,
which no heap order can affect. Routed forward, not back.

### N2 — the C5 row's "after close" premise is not exercised

`_prepared` leaves the task `WORKING` and the row never closes it, so
`task_closed_at` (None) and `task_state_snapshot` (WORKING) are trivially equal
on both sides of the ten-column comparison — 2 of 10 columns contribute nothing
in this fixture, and C5's named scenario ("supersession **after close**") is not
the one run.

No defect hides here, which is why this is a note: the invariant actually proven
— the recompute uses the evaluation's snapshot rate, not live configuration — is
closure-independent, and C6b separately arbitrates both columns for terminal
states (`test_phase8_reviewer_r1_probe.py:232-233` asserts `task_closed_at is
not None` for terminals, `:266-267` asserts `is None` for READY). *Correction:*
resolve the task before the second handler run, or rename the row to match what
it tests.

### N3 — record quality: "three echo rows" was two

The fix handoff states "The three SimpleNamespace C7 echo rows were removed."
It was **two** — one parametrized function with ids `P-V-infeasible` and
`P-V-ok`. The collection reconciles at −2 serializer / +2 integration, net 0,
which is only checkable because the per-file counts are. Same class as r2's N3:
ledger arithmetic should match the tree.

### N4 — cosmetic edit artifact in the serializer test

The import block's closing paren was re-indented to a stray `        )` and one
of the two blank lines before `_result()` was dropped, in a file whose only
intended change was deleting rows. It passes `ruff` (the default rule set
excludes E1/E3 continuation and blank-line rules), so nothing gates on it, but
it is inconsistent with every other file in the perimeter.

## Write perimeter (this session)

**Documents**
- `handoffs/reviewer/2026-08-15_phase8_rereview_r3_handoff.md` (this file, new)
- `plans/phase_8_status_results.md` (Review log append only)
- `master_plan.md` (tracker row 8 only)

**Code:** none. `git status` clean; `git diff 6988364..HEAD -- app/` empty at
close.

**Mutation-probe declaration.** Applied-and-reverted, each verified
byte-identical afterwards by sha256: `process_item_cost_result.py` (MX1, MX1b,
MX1c), `get_task_budget_status.py` (MX2, M1), `get_task_budget_status_worker.py`
(M2), `domain/item_economics/calculator.py` (MX3), `routers/api_v1/item_economics.py`
(the G7 widening probe). Final hashes for all five are in the perimeter table.

**Database side effects.** Probes and the full suite commit and clean up after
themselves; final state by state query is zero item-economics residue. No
disposable database created (no migration changed). Configured DB left at head
`c1d2e3f4a5b6`.

**Architecture Graph.** Read-only (`archgraph_status` only), zero delta, zero
review mutations. 172/254, rev `c74eb913…`, 21 pending held.

## Carry-forward dispositions (approval — all routed)

| item | destination |
|---|---|
| 21 pending graph items + migration mapping | coordinator's post-approval graph pass |
| the two status queries' node-type question | coordinator's post-approval graph pass |
| three A16 discrepancy filings (`archGraph_mapping_mantainance/open/`) | maintenance channel (already filed) |
| three `alembic check` drifts | only-if-cheap ledger (routed at r1, unchanged) |
| `user_section_daily_work_stats` residue class | existing maintenance prompt (phase-4 N11) |
| baseline failure #5 (`test_adding_a_batch_of_steps_reopens_ready_task`) | pre-existing; the adopted reopen probe row is the phase's green (r1 N1) |
| **N1** structural filter arbiter (order-free C1 mutation) | **phase 9** — first phase touching the status queries; carries the compiled-statement assertion |
| **N2** C5 row's closed-task premise | **phase 9** drift batch (with 4B N3, already routed there) |
| **N3** ledger-arithmetic discipline | folded to §9 as a lesson, no code destination |
| **N4** serializer test formatting | **phase 9** drift batch |

**Anchor spans:** this cycle touched no production file, so no held graph item
moved and no anchor service is owed — as the r3 prompt anticipated. Confirmed:
`git diff 6988364..HEAD -- app/` empty and all phase-8 production hashes equal
their r2 records.

## Lessons for the plans

1. **A filter-deletion mutation whose correct row REMAINS in the candidate set
   cannot be arbitrated order-independently by a behavioural assertion alone.**
   Whatever the fixture does, the mutated query may still pick the right row by
   accident. Criteria of this shape (C1's three filter sites are the archetype)
   want a **structural** arbiter over the compiled statement, with the
   behavioural row as the companion. Earned against my own r2 specification,
   which traded a false-positive flake for a possible false-negative one.
2. **"Prove the excluded columns are excluded" is stronger with DISTINCT nonzero
   values per column.** H2 asked for three nonzero columns; the fix used 30/40/50,
   so a leak of any one produces a unique wrong total (150/160/170) and names the
   culprit. Had all three carried the same value, the row would say only
   "something leaked". Specify distinct values in exclusion criteria.
3. **A stability row's fixture must satisfy the SCENARIO the criterion names,
   not just its mechanism.** C5's row proves snapshot-rate immutability but never
   closes the task, so "after close" is untested and two compared columns are
   vacuous. When a criterion names a boundary condition, the fixture must reach
   it — otherwise the row's name overstates its coverage for every later reader.
4. **A reviewer-specified repair needs its own adversarial pass.** Three of this
   round's four surviving observations (N1 especially) are about the quality of
   the *previous review's* instructions, not the fix. A specification that names
   its own acceptance condition ("M1/M2/M3 must still bite") gets exactly that
   and no more — so the condition must be the property you actually want, stated
   structurally where possible.
