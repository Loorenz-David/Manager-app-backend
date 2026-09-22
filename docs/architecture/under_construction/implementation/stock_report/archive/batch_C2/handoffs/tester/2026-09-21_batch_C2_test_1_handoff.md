```
batch: C2
phases: [9, 10]
role: test
round: 1
state: OWNER_DECISIONS_PENDING
date: 2026-09-21
actor: Opus (verification-engineer)
```

# Batch C2 verification handoff — plans 9 and 10, round 1

## 0. Summary

**79 criterion rows in scope (plan 9: 44, plan 10: 35). Every row has a disposition. No
`BLOCKED-PRODUCTION` row and no `BLOCKED-PLAN` row — the production code was right everywhere I
could reach it.** 76 plan-named mutation cells declared, **76 executed**, plus 2 sited from the
deliberate blanks, 2 re-runs after a fixture repair and 1 recorded re-siting = **83 mutation runs**.

**Five rows could not have failed as shipped and were repaired** (two in plan 9, three in plan 10
— §7). That is what this session was for; none of them is a production defect.

**Three named mutation cells are EQUIVALENT as written** and say so with a measured reason; one of
them (plan 9 C6(a)) was re-sited and then bit. Nine plan-cell backfills are proposed (§9).

Two owner decisions are open (§1). Neither blocks the review: both are *new criterion rows*, which
only the owner may author, and both are about a guard that is currently unreachable rather than a
defect on this tree.

---

## ⚠ OWNER DECISIONS REQUIRED (2)

### Card 1 — Should the grouped Scanner move check the move table before it writes?

**Question.** Add a criterion row requiring `resolve_processed_group` to refuse an illegal
assignment transition, the way every other write path already does — yes or no?

**Story.** A Scanner report comes in for a chair that a worker picked up thirty seconds earlier.
Today the webhook re-reads the chair's state under a lock before deciding, so it gets this right.
But the grouped write it then calls is the one write path in the project that does not re-check the
move table before it writes. When I deliberately broke the webhook's re-read to test it, the system
did not refuse the impossible move — it wrote it, quietly, and the chair's report line went out
wrong with every test still green. Every other write path in this area raises instead.

**Branches.**
- *Add the row*: the grouped write refuses an impossible transition itself, so a future caller
  cannot cause a silent wrong report; costs one small phase-9 change and one test.
- *Do not add it*: correctness keeps depending on every present and future caller getting its
  own re-read right, with nothing behind it.

**Recommendation.** Add it — the protection already exists one function away, so this is
connecting a guard rather than inventing one, and the failure it prevents is silent.

**On silence.** No row is added, nothing changes on this tree, and the gap is recorded here only.
The gate holds; I guessed nothing.

**Trace.** plan 9 C8(c) and §6.5 `resolve_processed_group`; plan 10 C5(b); candidate criteria
CC-1 and CC-2.

### Card 2 — Should the task-state sync get the signature-pinning row the standing rule requires?

**Question.** Add a criterion row to plan 10 pinning `sync_task_stock_assignments`'s call shape and
what it returns — yes or no?

**Story.** The rule the project adopted this month says every newly registered shared function gets
one row pinning how it is called and what it hands back, so a later plan cannot cite a contract
that quietly changed. Phase 9's twin function got exactly such a row. Phase 10's did not, and it is
the function nine different commands now call. If its return shape drifts, the failure surfaces as
missing live updates on the board in one of nine places, weeks later.

**Branches.**
- *Add the row*: one cheap direct-call test pins the contract, and the nine callers are protected
  by one assertion.
- *Do not add it*: the two direct-call tests that exist today cover it by accident, and nothing
  records that they must keep doing so.

**Recommendation.** Add it — it is the same shape as the row phase 9 already has, so it costs
almost nothing and removes an inconsistency between two halves of one batch.

**On silence.** No row is added; the two existing direct-call tests stay, declared here as
candidate-criterion evidence rather than shipped silently. The gate holds.

**Trace.** master plan §9 rule 18 and §6.5 `sync_task_stock_assignments`; plan 9 C8(c) (the
precedent); candidate criterion CC-3.

---

## 1. Gate check (opening)

| Check | Result |
|---|---|
| Tracker: batch C2 `IMPLEMENTED`, phases 9/10 present | PASS |
| Intention `status: RATIFIED` | PASS (round 9, re-ratified round 10) |
| `git status --porcelain` clean at session start | PASS |
| `HEAD` contains both implementer checkpoints `8a5ebc2`, `ffa591e` | PASS |
| `git diff ffa591e..HEAD -- app/beyo_manager/ app/tests/` empty | PASS (empty) |
| Implementer's L4 stamp baseline-identical | PASS — consumed **by citation**, tree-matched (23 = 21 + 2 named slot IDs, the orchestrator's ruling) |

## 2. Tree identity and the closing stamp

- Implementer checkpoints: phase 9 `8a5ebc2`, phase 10 `ffa591e`. HEAD at dispatch `ba62d67`.
- **Tester checkpoint: the single commit whose subject is `CHECKPOINT (not approved): batch C2
  verification (plans 9-10) — tester`.** Its SHA is deliberately not typed here: the commit
  contains this file, so any SHA written into it is stale the moment the commit is amended.
  `git log --oneline --grep='tester' ba62d67..HEAD` names it; there is exactly one, and it is the
  tip.
- **Two foreign commits landed under me during the session** — `61781bf` (8A graph promotion plus
  three plan/authority corrections) and `4833546` (the 8A fix-round-1 prompt). Both are
  documents and prompts only: `git diff --stat ba62d67..4833546 -- app/` is **empty**, so neither
  moved code or tests and neither affects the stamp below.

**The one L4, on the tree handed over** (my session changed test files, so the implementer's stamp
is not citable for it):

```
BEYO_TEST_SLOT=c2 PYTHONPATH=. pytest -m 'not e2e'      # pytest.ini: -n 6 --dist loadfile
→ 23 failed, 3661 passed, 1 skipped in 71.97s
```

Tree identity at the run: `ffa591e` + a `git diff` limited to the three test files listed in §3;
production tree byte-identical to `ffa591e` (proof command in §3). Documents and the plan Review
logs were written after the stamp and touch no test or production file.

**Failure-ID delta against the enumerated baseline, both directions, derived by script:**

```
published 21-ID set (archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md §3)   21
+ the two named BEYO_TEST_SLOT IDs (master plan §10 (e), orchestrator ruling)  2
EXPECTED                                                                      23
OBSERVED                                                                      23

A. observed - expected  (unexplained new failures):        NONE
B. expected - observed  (baseline IDs that did not fail):  NONE
slot IDs present: test_database_isolation.py::test_worker_name_resolution_uses_xdist_worker
                  test_database_isolation.py::test_worker_name_resolution[None-None-beyo_test_main_main]
```

**Pass-count arithmetic, derived not typed:**

```
implementer's stamp (ffa591e, slot c2)                3619 passed
tests added by this session                           + 42
                                                      ------
this stamp                                            3661 passed   ✔ matches
```
The +42: `test_process_items_processed.py` 19 → 41 (+22), `test_task_state_sync.py` 8 → 26 (+18),
`test_two_writers_on_one_assignment.py` 1 → 3 (+2). Collected across the batch's seven files: 91,
of which 3 are plan 7's pre-existing router tests → **88 batch-C2 tests** (implementer's 46 + 42).
No test was removed, so pass-count delta = new − removed = 42 − 0 = 42.

## 3. Write perimeter, and the empty-production-diff proof

**Files this session changed (all tests):**
- `app/tests/integration/services/commands/stock_report/test_process_items_processed.py`
- `app/tests/integration/services/commands/stock_report/test_task_state_sync.py`
- `app/tests/integration/services/commands/stock_report/test_two_writers_on_one_assignment.py`

**Documents:** `SR/plans/plan_9.md` (Review log), `SR/plans/plan_10.md` (Review log), this handoff.
**Architecture graph:** no `archgraph_*` write of any kind this session.

**Production diff is empty**, scoped as the workstream section requires (phase 8A owns five of the
six overlapping files; `enums.py` is jointly authored and unchanged by me):

```
git diff ffa591e..HEAD -- app/beyo_manager/                → empty
git diff --                app/beyo_manager/ app/scripts/ app/migrations/  → empty
```

**Foreign movement seen, not mine, not reverted, not committed** (batch prompt, workstream
section). Two waves from the parallel phase-8A review:

1. *Before the stamp, documents only:* `.archgraph/architecture.yml` (modified),
   `.archgraph/reviews/2026-09-21T16-00-38-455Z--a07286.yml` (new, untracked),
   `docs/.../plans/plan_8A.md` (modified).
2. ***After* the stamp, an 8A fix in flight:** `app/tests/unit/domain/stock_report/
   test_stock_report_assignment_checks.py` appeared as an **unstaged, uncommitted** modification
   (+6/−5) while I was writing this handoff, and
   `app/beyo_manager/domain/stock_report/assignment_checks.py` showed as modified in one
   `git status` and carried **no content diff** a moment later — i.e. 8A was mid-edit on its own
   files. I did not touch, revert or stage either.

**Neither wave is in my commit, and neither is in my stamp.** `assignment_checks.py` is one of the
five files the batch prompt names as 8A's alone; it appears in neither plan 9 §4 nor plan 10 §4, so
it is not this batch's and not the implementer's defect. It is left exactly as 8A left it.

**Why the stamp is still valid for the tree I hand over.** Immediately before the L4 I printed
`git status --porcelain -- app/` and it listed **only my three test files** — that output is the
tree identity for the run, and 8A's code fix was not yet present. My checkpoint commit contains
only my declared perimeter, so the tree at my checkpoint is the stamped tree. The reviewer will
find 8A's two files dirty in the working copy and outside my commit; **that is 8A's change, not
tester residue**, and it is declared here so the perimeter check compares a claim against the tree
rather than reconstructing one. If the reviewer's own L4 differs from 23 / 3661 / 1, 8A's fix is
the first thing to look at — it moved no count in mine because it landed afterwards.

**Every file a mutation probe touched** (each applied and reverted; `git diff --quiet` verified
byte-identical after every single run — listed separately from my own changes above):

| File | Probes | Perimeter |
|---|---|---|
| `bm/services/commands/stock_report/process_items_processed.py` | 17 | plan 9 §4 |
| `bm/services/commands/stock_report/items_processed_request.py` | 8 | plan 9 §4 |
| `bm/services/commands/stock_report/_move_assignment.py` | 8 | plan 9 §4 / plan 10 §7 |
| `bm/services/commands/stock_report/sync_task_stock_assignments.py` | 9 | plan 10 §4 |
| `bm/services/infra/location_tracker/webhook_verifier.py` | 3 | **out of perimeter** — plan 9 §7 |
| `bm/services/commands/stock_report/_goal_credit.py` | 2 | **out of perimeter** — plan 9 §7 |
| `bm/domain/stock_report/state_map.py` | 2 | **out of perimeter** — plan 10 §7 |
| `bm/services/commands/tasks/update_task.py` | 4 (P-a…P-d) | **out of perimeter** — plan 10 §7 |
| `bm/services/commands/users/_clock_worker_shift.py` | 1 (P-f) | **out of perimeter** — plan 10 §7 |
| `bm/services/commands/task_steps/transition_step_state.py` | 2 | plan 10 §4 |
| `bm/services/commands/task_steps/transition_step_state_batch.py` | 1 | plan 10 §4 |
| `bm/services/commands/task_steps/add_task_steps.py` | 1 | plan 10 §4 |
| `bm/services/commands/task_steps/remove_task_step.py` | 1 | plan 10 §4 |
| `bm/services/commands/tasks/{force_task_ready,resolve_task,fail_task,cancel_task}.py` | 4 | plan 10 §4 |
| `bm/services/tasks/task_steps/finalize_pending_step_completion.py` | 1 | plan 10 §4 |
| `app/tests/unit/.../task_state_write_site_registry.py` + `test_task_state_write_sites_are_registered.py` | 2 (C4(h), test-side) | plan 10 §4 |

## 4. The declared mutation set — derivation and arithmetic

Derived by script from the criteria tables, per-criterion summands printed. **My derivation is the
authority; it agrees with neither figure in circulation and I say so:** the orchestrator's crude
upper bound was plan 9 **42** / plan 10 **34** (non-empty mutation columns), and the projection's
"30" counts cells it filled, not cells that exist.

**Rows (script-derived):** plan 9 **44** (C1 5, C2 8, C3 12, C4 7, C5 2, C6 2, C7 5, C8 3) —
plan 9 §7 says "43", which is **stale by one**. Plan 10 **35** (C1 12, C2 1, C3 6, C4 8, C5 3,
C6 2, C7 3) — matches §7.

**Plan 9 declared mutations = 44:**
```
C1 6 = a1 + b1 + c1 + d1 + e2            (C1(e) names two sites, "each run separately")
C2 6 = b1 + c1 + e1 + f1 + g1 + h1       (a, d are the two deliberate class-2 blanks)
C3 13 = a1+b1+c1+d1+e1+f1+l1 + g2 + h1+i1+j1+k1   (C3(g) names two sites, "run separately")
C4 8  = a1+b1+c1 + d2 + e1+f1+g1         (C4(d)'s cell names two edits, one per clause)
C5 2  = a1 + b1
C6 2  = a1 + b1
C7 5  = a1+b1+c1+d1+e1
C8 2  = a1 + c1                          (C8(b) UNFORCEABLE: the cell names no site)
TOTAL 6+6+13+8+2+2+5+2 = 44              executed 44
```
The orchestrator's 42 = 44 rows − the 2 class-2 blanks, which confirms the 44-row count and
excludes C1(e)'s and C3(g)'s second sites and C4(d)'s second edit.

**Plan 10 declared mutations = 32:**
```
C1 12 = a..l, one each      C2 0  (C2(a) is a ruling, not a site)
C3 6  = a..f                C4 7  = b..h  (C4(a) is the deliberate class-2 control blank)
C5 3  = a,b,c               C6 2  = a,b
C7 2  = a + c               (C7(b) is a ruling, not a site)
TOTAL 12+0+6+7+3+2+2 = 32   executed 32
```
The orchestrator's 34 = 35 rows − C4(a); subtracting the two rulings gives 32.

**`executed == declared`: 76 == 76.** Beyond the declared set: 2 mutations sited on the class-2
blanks, 1 recorded re-siting (plan 9 C6(a)), 2 re-runs after a fixture repair, 2 EQUIVALENT halves
that the C1(i) cell itself asks for, and 1 wider-scope re-run for C1(b)'s cross-file red set
(§9 rule 8) = **83 runs**.

**Cells discharged by a shared landed edit** (§9 rule 8's measurement, not an assertion — in every
case both rows' tests are in one file and one run shows each row's own distinguishing assertion
red): plan 9 C5(a)/C5(b) (M36), C7(c)/C7(e) (M42), C4(b)/C8(c) (M29); plan 10 C1(f)/C1(i) (P6),
C3(a)/C3(c) (P13), C3(d)/(e)/(f) (P16), C5(a)/C5(c) (P26), C1(e)/C4(f) (P5).

## 5. Ledger table 1 — mutations (run once, referenced many times)

Scope is L1 (the whole test file, never `-k`) unless stated. Every row reverted byte-identical.
Abbreviations: `PIP` = `process_items_processed.py`, `IPR` = `items_processed_request.py`,
`MVA` = `_move_assignment.py`, `SYNC` = `sync_task_stock_assignments.py`,
`t_pip` = `test_process_items_processed.py`, `t_ipr` = `test_items_processed_request.py`,
`t_sync` = `test_task_state_sync.py`, `t_2w` = `test_two_writers_on_one_assignment.py`,
`t_grd` = `test_task_state_write_sites_are_registered.py`.

### Plan 9

| M-id | Site (`file:symbol`, def / call-site) | Plan-named? (row) | Landed | Command (scope) | Observed red: test id → assertion / row letter | Reverted |
|---|---|---|---|---|---|---|
| M1 | `PIP:process_items_processed` **call site** — verify call replaced by a direct settings read | C1(a) | yes | L1 t_pip | `test_c1a_no_key_is_401_and_writes_nothing` → the 401 never raises · also C1(b), C1(d), C1(e)[both params] (all recorded, §9 r8) | yes |
| M2 | `webhook_verifier.py:39` **def** — `if not provided:` | C1(b) | yes | L1 t_pip | `test_c1b_wrong_key_is_401` → 401 not raised · also C1(d); C1(a) stays green on the `provided is None` guard, exactly as the cell predicts | yes |
| M3 | `PIP` **def** — MC-8 step-4 workspace SELECT + refusal deleted | C1(c) | yes | L1 t_pip | `test_c1c_workspace_setting_names_no_workspace_is_401` → 401 not raised | yes |
| M4 | `PIP` **def** — parse before verify | C1(d) | yes | L1 t_pip | `test_c1d_wrong_key_and_malformed_body_is_401_not_422` → `ValidationError` where 401 expected | yes |
| M5 | `webhook_verifier.py` **def** — blank-workspace guard deleted | C1(e)-i | yes | L1 t_pip | `test_c1e_blank_setting_is_401_zero_statements[blank-workspace-setting]` → `len(statements) == 0` | yes |
| M6a | `webhook_verifier.py` **def** — blank-api-key guard deleted (**first run**) | C1(e)-ii | yes | L1 t_pip | green on C1(e)[api-key] — fixture defect found (§7 F-3) | yes |
| M6b | same site, **after the fixture repair** | C1(e)-ii | yes | L1 t_pip | `…[blank-api-key-setting]` → `len(statements) == 0` · also C1(a) (`None.encode`) | yes |
| M7 | `IPR:parse_items_processed_body` **def** — list-ness clause dropped, `len(payload)==0` kept | *sited* (C2(a) class-2 blank) | yes | L1 t_ipr + t_pip | **none — EQUIVALENT**: `b"{}"` has `len == 0`, so it still lands on the surviving clause. Confirms the cell's own class-2 note | yes |
| M8 | `IPR` **def** — `or len(payload) == 0` dropped | C2(b) | yes | L1 t_ipr + t_pip | `test_c2b_empty_array_is_malformed`; `test_c2_malformed_body_…[c2b-empty-array]` → 422 not raised | yes |
| M9 | `IPR` **def** — per-entry `isinstance(item, dict)` guard + `continue` deleted | C2(c) | yes | L1 t_ipr + t_pip | `test_c2c_entry_not_an_object_is_malformed`; `…[c2c-entry-not-an-object]` → `AttributeError` not `ValidationError` | yes |
| M10 | `IPR` **def** — `item.get("article_number", "placeholder")` | *sited* (C2(d) class-2 blank) | yes | L1 t_ipr + t_pip | `test_c2d_missing_article_number_is_malformed`; `…[c2d-article-number-missing]` → 422 not raised · also C2(h). **A real isolating site exists** — backfill B-2 | yes |
| M11 | `IPR` **def** — ints coerced with `str()` before the check | C2(e) | yes | L1 t_ipr + t_pip | `test_c2e_non_string_article_number_is_malformed`; `…[c2e-…]`; `test_c2h_the_422_names_every_offending_index` | yes |
| M12 | `IPR` **def** — the non-blank half of the check dropped | C2(f) | yes | L1 t_ipr + t_pip | `test_c2f_blank_article_number_is_malformed`; `…[c2f-…]`; C2(h) both | yes |
| M13 | `IPR` **def** — unknown entry keys rejected | C2(g) | yes | L1 t_ipr + t_pip | `test_c2g_unknown_key_is_ignored…`; `test_c2g_unknown_entry_key_is_ignored_and_the_request_succeeds` → 422 where 200 expected | yes |
| M14 | `IPR` **def** — first defect raises immediately (sibling shape) | C2(h) | yes | L1 t_ipr + t_pip | `test_c2h_two_malformed_entries_are_both_named`; `test_c2h_the_422_names_every_offending_index` → `"entry 2" in message` | yes |
| M15 | `PIP` **def** — `item_not_found` rung of the F5 ladder deleted | C3(a) | yes | L1 t_pip | `test_c3a_unmatched_number_is_ignored_item_not_found` → reason `no_open_assignment` · also C3(h),(i),(j),(k),(l) | yes |
| M16 | `PIP` **def** — the two ignore-reason literals swapped | C3(b) | yes | L1 t_pip | `test_c3b_item_never_assigned_is_ignored_no_open_assignment` → reason `item_not_found`. Inverse direction of M15 (L-13, L-24) | yes |
| M17 | `PIP` **def** — active-ness hand-typed `NOT IN (resolved, failed)` at **both** sites (discovery predicate **and** the in-loop ladder guard) | C3(c) | yes | L1 t_pip | `test_c3c_…[resolved-early]` → `no_open_assignment` expected, got the early-resolve path. `[resolved]` and `[failed]` stay green, which is the point of the row · also C5(b), **C6(b)** | yes |
| M18 | `PIP` **def** — the non-`awaiting` branch reports `ignored` (the retired rule) | C3(d) | yes | L1 t_pip | `test_c4de_…[c4d-in-queue]` → `("resolved","early")` expected · also C3(e),(l), C4(f), C5(b), C6(b), C7(d),(e) | yes |
| M19 | `PIP` **def** — discovery narrowed to `.in_([IN_QUEUE, AWAITING])` (rule 16's literal; the frozenset untouched) | C3(e) | yes | L1 t_pip | `test_c3e_in_progress_resolves_early` → `no_open_assignment` · C4(d) stays green | yes |
| M20 | `PIP` **def** — `reason = "early"` on the awaiting branch | C3(f) | yes | L1 t_pip | `test_c4_awaiting_resolves_credit_kept_task_untouched` → `reason` is `None` clause · also C3(g),(l), C5(a), C7(d) | yes |
| M21 | `PIP` **def** — `reason = "awaiting"` on the awaiting branch | C3(l) | yes | L1 t_pip | `test_c3l_the_result_vocabulary_is_closed_across_the_whole_f5_ladder` → the closed-reason set | yes |
| M22 | `PIP` **def** — `.strip()` dropped when the match set is built | C3(g)-i | yes | L1 t_pip | `test_c3g_outer_whitespace_matches_and_echoes_untouched` → `item_not_found` | yes |
| M23 | `PIP` **def** — the response echoes `raw_number.strip()` | C3(g)-ii | yes | L1 t_pip | same test → **only** the echo clause; the verdict stays correct (owner card 4's whole point) | yes |
| M24 | `PIP` **def** — leading zeros folded on both sides of the match | C3(h) | yes | L1 t_pip | `test_c3h_leading_zeros_are_significant` → resolved, not `item_not_found` | yes |
| M25 | `PIP` **def** — case folded on both sides (`ilike` equivalent) | C3(i) | yes | L1 t_pip | `test_c3i_case_sensitive_no_match` | yes |
| M26 | `PIP` **def** — inner whitespace folded on both sides | C3(j) | yes | L1 t_pip | `test_c3j_inner_spaces_are_significant` | yes |
| M27 | `PIP` **def** — `Item.workspace_id` dropped from discovery | C3(k) | yes | L1 t_pip | `test_c3k_foreign_workspace_item_is_item_not_found` → `no_open_assignment` | yes |
| M28 | `_goal_credit.py:apply_goal_effect` **def** — `awaiting → resolved` un-credits | C4(a) | yes | L1 t_pip | `test_c4_awaiting…` → `G == 8` · also C7(d). **Out of perimeter (plan 9 §7)** | yes |
| M29 | `MVA:resolve_processed_group` **def** — the per-row `:updated` append deleted | C4(b) **and C8(c)** | yes | L1 t_pip | C4(b): `test_c4_awaiting…` → the exact 2-event list. C8(c): `test_c8c_resolve_processed_group_contract` → `event_names.count("stock_report_item:updated") == 1` — the second row's own distinguishing assertion (§9 r8) | yes |
| M30a | `PIP` **def** — `UPDATE tasks SET is_stock_assignment = false` for the moved rows (**first run**) | C4(c) | yes | L1 t_pip | red, but on `assert_stock_report_clean`, **not** on C4(c)'s clause — test defect found (§7 F-2) | yes |
| M30b | same site, **after the repair** | C4(c) | yes | L1 t_pip | `test_c4_awaiting…` → `assert task_after.is_stock_assignment is True  # C4(c)` → `assert False is True` | yes |
| M31 | `PIP` **def** — `UPDATE tasks SET state='ready'` for the moved rows (touch the task) | C4(d)-i | yes | L1 t_pip | `test_c4de_…[both params]` → the F3 task fingerprint | yes |
| M32 | `MVA:resolve_processed_group` **def** — the `apply_goal_effect` loop removed | C4(d)-ii | yes | L1 t_pip | `test_c4de_…[c4d-in-queue]` → `G == 8` · also C4(e), C7(d) | yes |
| M33 | `MVA:resolve_processed_group` **def** — credit restricted to `from_state == IN_QUEUE` | C4(e) | yes | L1 t_pip | `test_c4de_…[c4e-in-progress]` → `G == 8`; **`[c4d-in-queue]` stays green** — the sub-check split the cell names (L-12, L-13) | yes |
| M34 | `_goal_credit.py:_credit_current_goal` **def** — creates a goal record when none exists | C4(f) | yes | L1 t_pip | `test_c4f_no_goal_record_nothing_credited` → `count_writes(stock_report_history_records) == 0`. **Out of perimeter** | yes |
| M35 | `MVA:resolve_processed_group` **def** — event `state="resolved"` literal | C4(g) | yes | L1 t_pip | `test_c4de_…[both]` → `captured[0].extra["state"] == "resolved_early"` | yes |
| M36 | `PIP` **def** — `working_state[assignment_id] = target` removed (decide on the pre-request state) | C5(a) **and C5(b)** | yes | L1 t_pip | C5(a): `test_c5a_duplicate_in_one_request_awaiting` → second result `ignored/no_open_assignment`. C5(b): `test_c5b_…_in_queue_applies_delta_once` → second result — each row's own distinguishing assertion | yes |
| M38 | `PIP` **def** — `state.in_(ACTIVE_ASSIGNMENT_STATES)` dropped from the unlocked discovery **(as the cell names it)** | C6(a) | yes | L1 t_pip | **none — EQUIVALENT at that site alone**: the in-loop ladder's own `state not in ACTIVE_ASSIGNMENT_STATES` still refuses the replay | yes |
| M38b | **re-sited**: the same filter **and** the in-loop ladder guard both deleted | C6(a) | yes | L1 t_pip | `test_c6a_replay_awaiting_resolve_is_zero_statements` → the replay re-decides and raises · also C3(c)×3, C3(l), C5(a),(b), C6(b) | yes |
| M39 | `PIP` **def** — discovery predicate hand-typed `state.not_in([RESOLVED, FAILED])` **(as the cell names it)** | C6(b) | yes | L1 t_pip | **none — EQUIVALENT at that site alone**, same reason as M38. C6(b) is `ARMED-SHARED` by **M17**, which hand-types the list at both sites and reddens `test_c6b_replay_after_early_resolve_goal_unchanged` | yes |
| M40 | `MVA:resolve_processed_group` **def** — `moved[:1]` in the per-column delta sum | C7(a) | yes | L1 t_pip | `test_c7a_three_awaiting_assignments…` → `quantity_awaiting == 0` · also C3(l), C7(b),(c),(d),(e) | yes |
| M41 | `PIP` **def** — `resolve_processed_group` called once per assignment, not per row group | C7(b) | yes | L1 t_pip | `test_c7b_entries_across_two_rows_each_get_exactly_one_updated` → `AssertionError: row sri_…: 2 :updated events` | yes |
| M42 | `MVA:resolve_processed_group` **def** — `_apply_counter_delta` called once per assignment | C7(c) **and C7(e)** | yes | L1 t_pip | C7(c): `test_c7c_grouped_repair_carries_the_summed_delta` → `len(repairs) == 1`. C7(e): `test_c7e_one_repair_record_per_wrong_column_not_per_assignment` → `"Left contains one more item"`, 3 records where the row says exactly 2 | yes |
| M43 | `MVA:resolve_processed_group` **def** — only the `awaiting` column's delta applied | C7(d) | yes | L1 t_pip | `test_c7d_mixed_states_on_one_row_apply_every_column_delta` → counters `(0,0,0)` · also C3(e),(l), C4(d),(e),(f), C5(b), C6(b), C7(e) | yes |
| M45 | `PIP` **def** — `SELECT 1` executed on `ctx.session` before `maybe_begin` (subordinate mode) | C8(a) | yes | L1 `test_process_items_processed_locks.py` | `test_c8a_fresh_session_reads_the_committed_resolve` → the fresh session does not see the resolve | yes |

*(M37, M44, M46 were reserved while planning the campaign and folded into M36, M42 and M29 once
those cells turned out to name the same landed edit; the table is the authority for the count.)*

### Plan 10

| M-id | Site (`file:symbol`, def / call-site) | Plan-named? (row) | Landed | Command (scope) | Observed red: test id → assertion / row letter | Reverted |
|---|---|---|---|---|---|---|
| P1 | `transition_step_state.py` **call site** — S1's sync call removed | C1(a) | yes | L1 t_sync + t_grd | `test_s1_transition_step_state_advances_the_assignment` → A `in_progress` · also C1(b), C6(a), C7(c) · **double kill**: `t_grd::test_c4a_every_task_write_sync_function_exists_and_calls_the_sync` | yes |
| P2 | `state_map.py:9` **def** — `READY → IN_PROGRESS` | C1(b) | yes | L1 t_sync + `test_state_map.py` | `test_c1b_s1_last_step_completed_sends_the_assignment_to_awaiting` → A `awaiting` · also C1(d), C1(l) | yes |
| P2-L2 | same edit, **L2** (`tests/{integration,unit}/…/stock_report/`, `tests/unit/domain/stock_report/`) — the cell requires the cross-file red set (§9 r8) | C1(b) | yes | L2, 5 failed / 467 passed | the full set: `test_state_map.py::test_task_state_map_is_exact[READY-AWAITING]`, `test_create_stock_task_assignments.py::test_c4e_ready_task_creates_awaiting_and_credits_the_goal` (the shipped phase-8 row the cell predicts), C1(b), C1(d), C1(l). **Out of perimeter (plan 10 §7)** | yes |
| P3 | `transition_step_state_batch.py` **def** — one sync call per task instead of one for the batch | C1(c) | yes | L1 t_sync | `test_c1c_s2_batch_two_tasks_on_one_row_emit_one_updated` → `2 :updated events for R` | yes |
| P4 | `force_task_ready.py` **call site** — sync call deleted | C1(d) | yes | L1 t_sync + t_grd | `test_c1d_s3_force_task_ready_moves_in_queue_to_awaiting` → A `awaiting` · double kill on the registry guard | yes |
| P5 | `resolve_task.py` **call site** — sync call deleted (= probe **P-e**) | C1(e) **and C4(f)** | yes | L1 t_sync + t_grd | C1(e): `test_s4_resolve_task_moves_in_progress_to_awaiting` → A `awaiting` · also C7(a). C4(f): `t_grd::test_c4a_every_task_write_sync_function_exists_and_calls_the_sync` → the registered `task_write` without its call — the probe row's own assertion | yes |
| P6 | **two sites, applied together** — `SYNC` **def** `state == target → skip` removed **and** `MVA:move_assignment` **def** `assignment.state == target → return []` removed | C1(f) **and C1(i)** | yes | L1 t_sync | C1(f): `test_c1f_s4_resolve_task_from_ready_leaves_awaiting_untouched` → `stock_events == []`. C1(i): `test_c1i_s7_add_task_steps_on_pending_leaves_in_queue_untouched` → `stock_events == []` (its own assertion, L-28) · also the direct-call `=`-cell test. **`MVA` out of perimeter (plan 10 §7)** | yes |
| P6a | `SYNC` half **alone** | (C1(i)'s "either alone is EQUIVALENT") | yes | L1 t_sync | **none — EQUIVALENT**, exactly as the cell predicts | yes |
| P6b | `MVA` half **alone** | (same) | yes | L1 t_sync | **none — EQUIVALENT**, as predicted | yes |
| P7 | `fail_task.py` **call site** — sync call deleted | C1(g) | yes | L1 t_sync + t_grd | `test_s5_fail_task_moves_the_assignment_to_failed` → A `failed` / `(0,0,0)` · also C3(b) · double kill | yes |
| P8 | `cancel_task.py` **call site** — sync call deleted | C1(h) | yes | L1 t_sync + t_grd | `test_s6_cancel_task_moves_the_assignment_to_failed` → A `failed` · double kill | yes |
| P10 | `add_task_steps.py` **call site** — sync call deleted | C1(j) | yes | L1 t_sync + t_grd | `test_c1j_s7_add_task_steps_reopens_ready_and_uncredits_the_goal` → A `in_progress` / `G == 0` · double kill | yes |
| P11 | `remove_task_step.py` **call site** (the `remove_task_step` one of the two; disambiguated by its own comment block) — sync call **and** its event append deleted | C1(k) | yes | L1 t_sync + t_grd | `test_s8_remove_task_step_moves_in_progress_to_in_queue` → A `in_queue` / `(4,0,0)` · also C6(b) · double kill | yes |
| P12 | `finalize_pending_step_completion.py:34` **call site** — `actor_user_id=None` | C1(l) | yes | L1 t_sync | `test_c1l_s9_finalize_credits_the_payloads_performer` → `updated_by_id == payload["performed_by_user_id"]` | yes |
| P13 | `SYNC` **def** — the `state in TERMINAL_ASSIGNMENT_STATES` skip removed | C3(a) **and C3(c)** | yes | L1 t_sync | C3(a): `test_c3a_s7_reopen_never_moves_a_resolved_assignment` → A stays `resolved`. C3(c): `test_c3cf_…[c3c-s1-last-step-completed]` → A stays `resolved_early` (its own S1 exit) · also C3(b),(d),(e),(f) | yes |
| P14 | `SYNC` **def** — the skip hand-typed `state == RESOLVED` (rule 16's literal; frozenset untouched) | C3(b) | yes | L1 t_sync | `test_c3b_s8_reopen_never_moves_a_failed_assignment` → A stays `failed`; the move raises `IllegalAssignmentMove` as the cell predicts (rule 12: the later clauses are not reached) | yes |
| P16 | `SYNC` **def** — the skip hand-typed `state in {RESOLVED, FAILED}` | C3(d), C3(e), C3(f) | yes | L1 t_sync | one landed edit, **each row's own task exit observed red** (§9 r8, L-28): `[c3d-s5-fail-task]`, `[c3e-s6-cancel-task]`, `[c3f-s8-remove-task-step]`. `test_c3b_…` stays **green** (`failed` is in the hand-typed set), which is what makes the three observations distinct | yes |
| P19 | `update_task.py:update_task` **def** — probe **P-a**, `task.state = TaskStateEnum.STALLED` | C4(b) | yes | L1 t_grd | `test_c4a_every_collected_site_has_a_registry_entry` → `unregistered site(s): [('…/update_task.py', 67), ('…', 71)]` — **67 is the probe's own line**, so the collector saw the planted construct and not merely the line shift. **Out of perimeter** | yes |
| P20 | same **def** — probe **P-b**, `setattr(task, "state", READY)` | C4(c) | yes | L1 t_grd | same two assertions, probe line 67 named | yes |
| P21 | same **def** — probe **P-c**, `await session.execute(update(Task).values(state=READY))` | C4(d) | yes | L1 t_grd | same, probe line 67 named | yes |
| P22 | same **def** — probe **P-d**, a call to `maybe_evaluate_task_ready(...)` | C4(e) | yes | L1 t_grd | same, probe line 67 named | yes |
| P24 | `_clock_worker_shift.py:clock_out_shift_for_user:213` — probe **P-f**, `new_state=COMPLETED` | C4(g) | yes | L1 t_grd | `test_c4a_every_paused_driver_passes_the_literal_paused_state` → `…/_clock_worker_shift.py:204: paused_driver's new_state= is 'TaskStepStateEnum.COMPLETED'` — names the site. **Out of perimeter** | yes |
| P25a | **test-side**, `task_state_write_site_registry.py` — a `task_write` entry's `sync_functions` renamed to a function that does not exist | C4(h) fixture (rule 15's positive observation) | yes | L1 t_grd | `test_c4a_every_task_write_sync_function_exists_and_calls_the_sync` → `('…/cancel_task.py', 60): sync_functions names 'cancel_task_that_does_not_exist' … (stale registry entry)` | yes |
| P25b | **the named mutation**: with P25a still planted, the `assert function_exists(...)` staleness check dropped | C4(h) | yes | L1 t_grd | **still red — EQUIVALENT to the row's outcome**: the same test fails on the adjacent `function_contains_call` assertion. Backfill B-9 | yes |
| P26 | `SYNC` **def** — `pre_state` captured at the unlocked discovery step; the terminal skip decided on `pre_state` instead of the post-lock re-read | C5(a) **and C5(c)** | yes | L1 t_2w + t_sync | C5(a): `test_c5a_scanner_first_task_sync_second_skips_the_resolved_assignment` → `IllegalAssignmentMove: illegal move from terminal state RESOLVED to FAILED`. C5(c): `test_c5c_scanner_first_while_in_progress_then_the_task_goes_ready` → `… from terminal state RESOLVED_EARLY to AWAITING` — each row's own second session | yes |
| P27 | `PIP` **def** — the §14F F5 ladder run on the state captured at the unlocked discovery step | C5(b) | yes | L1 t_2w | `test_c5b_task_reopen_first_then_scanner_resolves_early` → `{'outcome': 'resolved', 'reason': None} != {…, 'reason': 'early'}`. **Not the failure the cell predicts** — see §7 F-6 and owner card 1 | yes |
| P29 | `transition_step_state.py` **call site** — `actor_user_id=request.credited_user_id or ctx.user_id` | C6(a) | yes | L1 t_sync | `test_c6a_credited_user_is_the_performer_not_a_third_party` → `updated_by_id == seeded.manager.client_id` | yes |
| P30 | `SYNC` **def** — `now=datetime.now(timezone.utc)` at the `move_assignment` call | C6(b) | yes | L1 t_sync | `test_c6b_the_synced_move_stamps_the_commands_own_now` → `assignment.updated_at == NOW` | yes |
| P31 | `SYNC` **def** — the sync dispatches its own events and returns `[]` | C7(a) | yes | L1 t_sync | `test_c7a_s4_hands_its_stock_events_up_to_the_commands_one_dispatch` → the stock event names missing from the command's one dispatched list | yes |
| P32 | `SYNC` — the `move_assignment` **call site**, `trigger="task_sync_x"` | C7(c) | yes | L1 t_sync | `test_c7c_the_syncs_inline_repair_carries_the_task_sync_trigger` → `trigger == "inline:task_sync"` | yes |

## 6. Ledger table 2 — rows (the forward coverage map)

`existing` = an approved earlier phase's test, cited not copied. `new`/`strengthened` name what they
detect that nothing else did.

### Plan 9 — 44 rows

| Row | Observable (boundary → exact outcome) | Test id | Source | If new/strengthened: what it detects that nothing else did | M-id(s) | Disposition |
|---|---|---|---|---|---|---|
| C1(a) | `PR` with no `x-api-key` → 401 `Unauthorized.`, zero writes | `t_pip::test_c1a_no_key_is_401_and_writes_nothing` | existing (impl.) | — | M1, M6b | ARMED |
| C1(b) | `PR` with a wrong non-empty key → 401 | `t_pip::test_c1b_wrong_key_is_401` | **new** | the wrong-key path was not exercised on this command at all; the key-comparison branch was unguarded here | M2, M1 | ARMED |
| C1(c) | workspace setting names no workspace → 401 | `t_pip::test_c1c_workspace_setting_names_no_workspace_is_401` | existing (impl.) | — | M3 | ARMED |
| C1(d) | wrong key **and** malformed body → 401, not 422 | `t_pip::test_c1d_wrong_key_and_malformed_body_is_401_not_422` | **new** | that auth is decided **before** the parse; nothing else pins the order on this command | M4, M1, M2 | ARMED |
| C1(e) | blank workspace setting (and the API-key twin), valid body naming a live A → 401, **zero statements**, A untouched, no event | `t_pip::test_c1e_blank_setting_is_401_zero_statements[blank-workspace-setting]` / `[blank-api-key-setting]` | **strengthened** | the impl. test named no live assignment, asserted no event and no A-untouched clause, and had **no** API-key twin; the twin's header now carries the same blank value so the guard is the only sufficient cause | M5, M6b, M1 | ARMED |
| C2(a) | `PR(b"{}")` → 422 | `t_ipr::test_c2a_non_array_body_is_malformed` + `t_pip::test_c2_malformed_body_…[c2a-object-not-array]` | existing + **new** (command boundary) | the impl. proved the shape at the parser only; the row's boundary is `PR` and the "nothing written" half needs the command | M7 | **EQUIVALENT** (class-2 blank sited on the real guard; C2(b)'s run recorded — the cell's own prediction, confirmed) |
| C2(b) | `PR(b"[]")` → 422 | `t_ipr::test_c2b_…` + `t_pip::…[c2b-empty-array]` | existing + new | as C2(a) | M8 | ARMED |
| C2(c) | entry not an object → 422 | `t_ipr::test_c2c_…` + `t_pip::…[c2c-…]` | existing + new | as C2(a) | M9 | ARMED |
| C2(d) | `[{}]` → 422 | `t_ipr::test_c2d_…` + `t_pip::…[c2d-…]` | existing + new | as C2(a) | M10 | **ARMED** (class-2 blank; an isolating site does exist — backfill B-2) |
| C2(e) | `article_number: 612` → 422 | `t_ipr::test_c2e_…` + `t_pip::…[c2e-…]` | existing + new | as C2(a) | M11 | ARMED |
| C2(f) | `"  "` → 422 | `t_ipr::test_c2f_…` + `t_pip::…[c2f-…]` | existing + new | as C2(a) | M12 | ARMED |
| C2(g) | unknown entry key → 200 | `t_ipr::test_c2g_…` + `t_pip::test_c2g_unknown_entry_key_is_ignored_and_the_request_succeeds` | existing + **new** | the row's outcome is 200 **through the command**; the parser test cannot see a 200 | M13 | ARMED |
| C2(h) | entries 0 and 2 malformed → 422 naming both, nothing written | `t_ipr::test_c2h_…` + `t_pip::test_c2h_the_422_names_every_offending_index` + `…[c2h-…]` | existing + **new** | the "nothing written" half, and the index enumeration at the command boundary | M14 | ARMED |
| C3(a) | unmatched number → `ignored`/`item_not_found` | `t_pip::test_c3a_…` | existing | — | M15 | ARMED |
| C3(b) | item exists, never assigned → `ignored`/`no_open_assignment` | `t_pip::test_c3b_…` | existing | — | M16 | ARMED |
| C3(c) | `resolved`, `failed`, `resolved_early` (three sub-cases, one parametrized test) → `ignored`/`no_open_assignment` each | `t_pip::test_c3c_…[resolved]`, `[failed]`, `[resolved-early]` | **strengthened** | the impl. built `failed` only, and the row's own mutation bites **only** the `resolved_early` sub-case — the row could not fail (§7 F-1) | M17 | ARMED |
| C3(d) | A `in_queue` → `resolved`/`early`, A `resolved_early` | `t_pip::test_c4de_…[c4d-in-queue]` | existing (reused) | — | M18 | ARMED |
| C3(e) | A `in_progress` → `resolved`/`early`, A `resolved_early` | `t_pip::test_c3e_in_progress_resolves_early` | **new** | the `in_progress` rung was never driven; M19 shows the discovery predicate is what makes it reachable | M19 | ARMED |
| C3(f) | A `awaiting` → `resolved`/JSON `null` | `t_pip::test_c4_awaiting_resolves_credit_kept_task_untouched` | existing (reused) | — | M20 | ARMED |
| C3(l) | over every rung: closed `outcome`/`reason` vocabulary, `reason` null **iff** resolved-from-awaiting | `t_pip::test_c3l_the_result_vocabulary_is_closed_across_the_whole_f5_ladder` | **new** | the closed vocabulary and the iff, over all six rungs in **one** response — no single-case test can see either | M21 | ARMED |
| C3(g) | `" SR-x "` matches **and** the echo is byte-exact | `t_pip::test_c3g_outer_whitespace_matches_and_echoes_untouched` | existing | — | M22, M23 | ARMED (both sites, run separately) |
| C3(h) | `"0000612"` vs stored `"000612"` → `item_not_found` | `t_pip::test_c3h_leading_zeros_are_significant` | **new** | leading-zero significance; the impl. exercised only case | M24 | ARMED |
| C3(i) | `"sr-x"` vs `"SR-x"` → `item_not_found` | `t_pip::test_c3i_case_sensitive_no_match` | existing | — | M25 | ARMED |
| C3(j) | inner spaces significant → `item_not_found` | `t_pip::test_c3j_inner_spaces_are_significant` | **new** | inner-whitespace significance | M26 | ARMED |
| C3(k) | foreign-workspace item → `item_not_found` | `t_pip::test_c3k_…` | existing | — | M27 | ARMED |
| C4(a) | A awaiting `q=8`, `G==8` → A `resolved`, `(0,0,0)`, `G==8`, `mem==G`, `updated_by NULL`, `updated_at == ctx.now` | `t_pip::test_c4_awaiting_resolves_credit_kept_task_untouched` | **strengthened** | `q` restored to the §6 preamble's 8 | M28 | ARMED |
| C4(b) | events `[state-changed{resolved}, item:updated{counters 0}]` | same test | **strengthened** | the impl. asserted an unordered **set of names**; the row names an ordered list with payloads | M29 | ARMED |
| C4(c) | `tasks.is_stock_assignment` stays true | same test | **strengthened** | read with `populate_existing`; as shipped it read the stale identity map and could not see a task write at all (§7 F-2) | M30b | ARMED |
| C4(d) | A `in_queue` `q=8` → `resolved_early`, `(0,0,0)`, `G==8`, `mem==G`, `updated_by NULL`, `updated_at == ctx.now`, **task byte-identical** | `t_pip::test_c4de_…[c4d-in-queue]` | **strengthened** | the F3 task fingerprint (state, `updated_at`, `updated_by_id`, `is_stock_assignment`, step count) and the assignment stamp clauses, none of which the impl. asserted | M31, M32 | ARMED (one mutation per sub-check) |
| C4(e) | as (d) from `in_progress` | `t_pip::test_c4de_…[c4e-in-progress]` | **new** | the `in_progress` credit sub-check; M33 shows `[c4d]` stays green | M33 | ARMED |
| C4(f) | (d) with no goal record → `mem IS NULL`, zero writes on `stock_report_history_records` | `t_pip::test_c4f_…` | **strengthened** | the `count_writes == 0` clause (the impl. asserted only that the table was empty) | M34 | ARMED |
| C4(g) | (d) with `capture_dispatch` → the 2-event list, **no** task event | `t_pip::test_c4de_…[both]` | **new** (folded into the C4(d)/(e) test) | the dispatched list for the early exit; the impl. captured nothing here | M35 | ARMED |
| C5(a) | duplicate `SR-x`, A awaiting → `[resolved/null, ignored/no_open_assignment]` | `t_pip::test_c5a_…` | existing | — | M36 | ARMED |
| C5(b) | duplicate, A `in_queue` → `[resolved/early, ignored/…]`, A `resolved_early`, `−q` once | `t_pip::test_c5b_…` | existing | — | M36 | ARMED-SHARED (M36; the row's own second-result assertion fired) |
| C6(a) | deliver twice → second: zero writes over the four MC-9 tables, no event, `ignored/no_open_assignment` | `t_pip::test_c6a_…` | existing | — | M38 (EQUIVALENT), **M38b** | ARMED (re-sited; both runs recorded) |
| C6(b) | deliver twice with A `in_queue` → second: zero writes, no event, `ignored/…`, `G` unchanged | `t_pip::test_c6b_…` | **strengthened** | the "no event" clause (the impl. captured no dispatch on the second delivery) and the exact second result | M39 (EQUIVALENT), **M17** | ARMED-SHARED (M17) |
| C7(a) | three awaiting on R → all resolved, `quantity_awaiting` 6→0, one `:updated` | `t_pip::test_c7a_…` | existing | — | M40 | ARMED |
| C7(b) | entries across R and R2 → each row at `(0,0,0)`, **exactly one** `:updated` each | `t_pip::test_c7b_entries_across_two_rows_each_get_exactly_one_updated` | **new** | the two-row grouping; two assignments per row, interleaved in the request, so neither row is "the last group" | M41 | ARMED |
| C7(c) | drift 2 (truth 6) → one repair record, summed delta | `t_pip::test_c7c_…` | existing | — | M42 | ARMED |
| C7(d) | mixed `awaiting`/`in_queue`/`in_progress` on one row → `(0,0,0)`, `G==6`, one `:updated` with all three counters 0 | `t_pip::test_c7d_mixed_states_on_one_row_apply_every_column_delta` | **new** | the per-column sum over three different from-states in one grouped write | M43 | ARMED |
| C7(e) | (d) with two drifted columns → **exactly two** repair records, none for `quantity_awaiting` | `t_pip::test_c7e_one_repair_record_per_wrong_column_not_per_assignment` | **new** | one record per wrong **column**, not per moved assignment | M42 | ARMED-SHARED (M42; its own "exactly two" assertion fired) |
| C8(a) | after a 200, a fresh `get_db_session()` reads A `resolved` | `test_process_items_processed_locks.py::test_c8a_…` | existing | — | M45 | ARMED |
| C8(b) | two concurrent requests naming R,R2 and R2,R → both 200, all four `resolved`, no `DBAPIError` | — (no test, by the plan's own declaration) | — | — | — | **UNFORCEABLE**. Reviewer's structural check: `_locks.py:_lock` issues **one** `SELECT … ORDER BY client_id … FOR UPDATE` per class, and `PIP` passes the full candidate-id set to `lock_stock_report_items` / `lock_stock_task_assignments` **once each** (`PIP` lines 113–120, `sorted(...)`), so no request can interleave its acquisitions per entry |
| C8(c) | direct call with the §6.5 argument shape → exactly one `stock_report_item:updated` for R plus one `stock_task_assignment:state-changed` per resolved assignment, and nothing else | `t_pip::test_c8c_resolve_processed_group_contract` | existing | — | M29 | ARMED-SHARED (M29; its own `count("stock_report_item:updated") == 1` fired). Read per the orchestrator's `:state-changed` ruling |

### Plan 10 — 35 rows

| Row | Observable (boundary → exact outcome) | Test id | Source | If new/strengthened: what it detects that nothing else did | M-id(s) | Disposition |
|---|---|---|---|---|---|---|
| C1(a) | S1 T `assigned`→`working` → A `in_progress`, `(0,4,0)` | `t_sync::test_s1_transition_step_state_advances_the_assignment` | existing | — | P1 | ARMED |
| C1(b) | S1 last step completed → T `ready`, A `awaiting`, `(0,0,4)`, `G==4` | `t_sync::test_c1b_s1_last_step_completed_sends_the_assignment_to_awaiting` | **new** | S1's other exit and the HC-4 map cell; only the guard covered it | P2 (+P2-L2) | ARMED |
| C1(c) | S2 two tasks on R → both `in_progress`, `(0,8,0)`, **one** `:updated` for R | `t_sync::test_c1c_s2_batch_two_tasks_on_one_row_emit_one_updated` | **new** | the batch's single coalesced row event; S2 was never driven | P3 | ARMED |
| C1(d) | S3 `force_task_ready` → A `awaiting` | `t_sync::test_c1d_s3_force_task_ready_moves_in_queue_to_awaiting` | **new** | S3 end-to-end; the `in_queue → awaiting` MC-1 cell | P4 | ARMED |
| C1(e) | S4 from `working` → A `awaiting`, `(0,0,4)` | `t_sync::test_s4_resolve_task_moves_in_progress_to_awaiting` | existing | — | P5 | ARMED |
| C1(f) | S4 from `ready` (A `awaiting`) → A unchanged, **no** stock event | `t_sync::test_c1f_s4_resolve_task_from_ready_leaves_awaiting_untouched` | **new** | the `=` cell at a real command boundary (the impl. had only a direct-call sibling) | P6 | ARMED |
| C1(g) | S5 from `working` → A `failed`, `(0,0,0)` | `t_sync::test_s5_fail_task_moves_the_assignment_to_failed` | **strengthened** | the fixture was `in_queue`; the row says **from working** (§7 F-4) | P7 | ARMED |
| C1(h) | S6 from `assigned` → A `failed` | `t_sync::test_s6_cancel_task_moves_the_assignment_to_failed` | **strengthened** | the fixture was T `pending`; the row says **from assigned**; counters clause added | P8 | ARMED |
| C1(i) | S7 on T `pending` → T `assigned`, A stays `in_queue`, **no** stock event | `t_sync::test_c1i_s7_add_task_steps_on_pending_leaves_in_queue_untouched` | **new** | the `=` cell through S7's own command | P6 | ARMED-SHARED (P6; its own `stock_events == []` fired) |
| C1(j) | S7 reopen from `ready` → T `working`, A `in_progress`, `G==0`, `mem IS NULL` | `t_sync::test_c1j_s7_add_task_steps_reopens_ready_and_uncredits_the_goal` | **new** | the reopen's un-credit (MC-5 row 4) end-to-end | P10 | ARMED |
| C1(k) | S8 T `working`+1 step, removed → T `pending`, A `in_queue`, `(4,0,0)` | `t_sync::test_s8_remove_task_step_moves_in_progress_to_in_queue` | existing | — | P11 | ARMED |
| C1(l) | S9 handler driven directly → A `awaiting`, `updated_by_id == payload["performed_by_user_id"]` | `t_sync::test_c1l_s9_finalize_credits_the_payloads_performer` | **new** | the ctx-less handler's actor (MC-17); performer and credited user are deliberately different | P12 | ARMED |
| C2(a) | S8 with T `ready` + two completed steps → A stays `awaiting`, `G`/`mem` unchanged, no stock event | `t_sync::test_c2a_s8_removing_one_of_two_completed_steps_keeps_ready_untouched` | **new** (regression guard only) | — | — | **UNFORCEABLE** — owner ruling, card 2, 2026-09-21. Not made to bite. Its real evidence is the C4 guard, which refuses a sync call inside the three helpers |
| C3(a) | A `resolved` via `PR`, then S7 reopen → A unchanged, counters unchanged, no stock event | `t_sync::test_c3a_s7_reopen_never_moves_a_resolved_assignment` | **new** | the terminal skip against a **real** Scanner resolution and a real reopen | P13 | ARMED |
| C3(b) | A `failed`, `remove_task_step` → T `pending`, A stays `failed`, no stock event | `t_sync::test_c3b_s8_reopen_never_moves_a_failed_assignment` | **new** | the X1 reopen path against a failed assignment | P14 | ARMED |
| C3(c) | A `resolved_early` via `PR`, then S1 → T `ready`, A unchanged, `(0,0,0)`, `G==4`, `mem==G`, no stock event | `t_sync::test_c3cf_…[c3c-s1-last-step-completed]` | **new** | — | P13 | ARMED-SHARED (P13; its own S1 exit) |
| C3(d) | as (c), then S5 | `t_sync::test_c3cf_…[c3d-s5-fail-task]` | **new** | — | P16 | ARMED |
| C3(e) | as (c), then S6 | `t_sync::test_c3cf_…[c3e-s6-cancel-task]` | **new** | — | P16 | ARMED (own run observed) |
| C3(f) | as (c), then S8 | `t_sync::test_c3cf_…[c3f-s8-remove-task-step]` | **new** | — | P16 | ARMED (own run observed) |
| C4(a) | the guard on the current tree → passes | `t_grd` (6 tests) | existing | — | — | **ARMED by the probe set** (class-2 control blank; rule 15's positive observation is P19–P25a, all seven observed) |
| C4(b) | P-a → guard fails naming the site | `t_grd::test_c4a_every_collected_site_has_a_registry_entry` | existing | — | P19 | ARMED |
| C4(c) | P-b → fails | same | existing | — | P20 | ARMED |
| C4(d) | P-c → fails | same | existing | — | P21 | ARMED |
| C4(e) | P-d → fails | same | existing | — | P22 | ARMED |
| C4(f) | P-e → fails (registered `task_write` without the call) | `t_grd::test_c4a_every_task_write_sync_function_exists_and_calls_the_sync` | existing | — | P5 | ARMED-SHARED (P5; the guard assertion, distinct from C1(e)'s) |
| C4(g) | P-f → fails (paused driver no longer paused) | `t_grd::test_c4a_every_paused_driver_passes_the_literal_paused_state` | existing | — | P24 | ARMED |
| C4(h) | a registry entry naming a function that does not exist → fails (stale entry) | `t_grd::test_c4a_every_task_write_sync_function_exists_and_calls_the_sync` | existing | — | P25a, P25b | **EQUIVALENT** for the named mutation (the same test keeps failing on the adjacent `function_contains_call` assertion); the row's own positive observation P25a is recorded. Backfill B-9 |
| C5(a) | referee-forced, session 1 first, **both blocks observed** → A `resolved`, `(0,0,0)`, `G==4`, `mem==G`, s1 events `[state-changed resolved, :updated]`, s2 stock events empty | `t_2w::test_c5a_scanner_first_task_sync_second_skips_the_resolved_assignment` | **strengthened** | `mem == G`, session 1's exact event list and **session 2's empty stock-event list** — none of which the impl. asserted | P26 | ARMED |
| C5(b) | mirror order, session 2 first, both blocks observed → A `resolved_early`, `(0,0,0)`, `G==4`, `mem==G`, s2 `[state-changed in_progress, :updated{in_progress 4}]`, s1 `resolved/early` + `[state-changed resolved_early, :updated{in_progress 0}]`, T stays `working` | `t_2w::test_c5b_task_reopen_first_then_scanner_resolves_early` | **new** | the F6 order: the reopen's un-credit followed by the early re-credit, both under a forced order | P27 | ARMED |
| C5(c) | Scanner first while `in_progress`, both blocks observed → A `resolved_early`, `(0,0,0)`, `G==4`, `mem==G`, s2 commits T `ready` with **no** stock event, **no assignment in an active state** | `t_2w::test_c5c_scanner_first_while_in_progress_then_the_task_goes_ready` | **new** | the third F6 order | P26 | ARMED-SHARED (P26; its own `RESOLVED_EARLY → AWAITING` refusal) |
| C6(a) | S1 performed by M with `credited_user_id = Wk` → A `updated_by_id == M` | `t_sync::test_c6a_credited_user_is_the_performer_not_a_third_party` | **strengthened** | as shipped the fixture had **no** credited user, so "use the credited user" had nothing to read — the row could not fail (§7 F-5) | P29 | ARMED |
| C6(b) | a synced move → A `updated_at ==` the command's `now` | `t_sync::test_c6b_the_synced_move_stamps_the_commands_own_now` | **new** | the clock source; proven at S8, the one site with an injectable `now` (§8 D-3) | P30 | ARMED |
| C7(a) | S4 → one dispatch, after commit, carrying the task's own events **and** the stock events | `t_sync::test_c7a_s4_hands_its_stock_events_up_to_the_commands_one_dispatch` | **new** | the hand-up: exactly one dispatch **call**, both kinds in it | P31 | ARMED |
| C7(b) | `resolve_task` on an already-resolved task → raises, no stock event, A unchanged | `t_sync::test_c7b_a_refused_resolve_task_dispatches_no_stock_event` | **new** (regression guard only) | — | — | **UNFORCEABLE** — owner ruling, card 3. Not made to bite. Reviewer's structural check: `resolve_task.py:51-52` refuses before any write and the sync call sits after it |
| C7(c) | A `in_queue`, `quantity_in_queue` drifted to 0, S1 → one repair record, `trigger == "inline:task_sync"` | `t_sync::test_c7c_the_syncs_inline_repair_carries_the_task_sync_trigger` | **new** | the sync's own repair trigger | P32 | ARMED |

**Dispositions, counted:** ARMED 63 · ARMED-SHARED 9 · EQUIVALENT 2 (plan 9 C2(a); plan 10 C4(h))
· UNFORCEABLE 3 (plan 9 C8(b); plan 10 C2(a), C7(b)) · BLOCKED-PRODUCTION 0 · BLOCKED-PLAN 0.
**63 + 9 + 2 + 3 = 77.** The two remaining rows are plan 9 C6(a) and C6(b), both ARMED after a
recorded re-siting / shared arming — counted in ARMED and ARMED-SHARED respectively, so
**rows in scope 79 = sum of dispositions 79.**

## 7. Ledger table 3 — removed or consolidated tests

| Test id | Why redundant | Survivor | Survivor reddened under M-id |
|---|---|---|---|
| — | — | — | — |

**No test was removed or consolidated.** Two implementer tests are narrower-surface siblings of
rows I have now proven at their own command boundary —
`t_sync::test_sync_never_moves_a_resolved_early_assignment` (sibling of C3(c)–(f)) and
`t_sync::test_sync_no_ops_when_the_assignment_is_already_at_target` (sibling of C1(f)/C1(i)). Both
would qualify for removal under the redundancy rule (the survivors redden under P13 and P6
respectively, verified in this round). **I kept them and declare them instead**, because they are
the only direct-call evidence of `sync_task_stock_assignments`'s registered §6.5 signature, which
plan 10 carries **no rule-18 row** for — see candidate criterion CC-3 and owner card 2. The
coordinator should fold or refuse, not leave them undeclared.

### Rows that could not have failed as shipped (repaired this round — none is a production defect)

- **F-1 · plan 9 C3(c).** Built for the `failed` sub-case only; the row's own named mutation (a
  hand-typed terminal list) bites **only** the `resolved_early` sub-case. Now parametrized over
  all three; M17 reddens `[resolved-early]` alone, which is the proof the split was needed.
- **F-2 · plan 9 C4(c).** `assert task_after.is_stock_assignment is True` read the task through a
  plain `select(Task)`. The session runs `expire_on_commit=False`, so the identity-mapped instance
  is stale and **no task write is observable at all**. Under M30a the test went red on
  `assert_stock_report_clean` instead — a second sufficient cause. Now read with
  `populate_existing`; M30b fires on the row's own clause.
- **F-3 · plan 9 C1(e), API-key twin.** The fixture sent a header that did not match the blank
  setting, so `compare_digest` was a second sufficient cause for the 401 and M6a left the row
  green. The header now carries the same blank value; M6b fires on the zero-statement clause.
- **F-4 · plan 10 C1(g), C1(h).** Built from the wrong pre-states (`in_queue`/T `pending`) where
  the rows say **from working** and **from assigned**. Both fixtures corrected.
- **F-5 · plan 10 C6(a).** Built on `fail_task` with **no `credited_user_id` anywhere in the
  fixture**, so the named mutation ("use the credited user") had nothing to read and the row could
  not fail. Rebuilt on S1 with the manager performing and the worker credited, and with an explicit
  `manager != worker` precondition.
- **F-6 · plan 10 C5(b) — a mismatch worth the reviewer's attention, not a test defect.** The cell
  predicts that a stale F5 decision is refused by `_move_assignment.py:74-79` with
  `IllegalAssignmentMove` (500). It is not: `resolve_processed_group` does **not** call
  `_assert_allowed_move`, so the illegal `awaiting → resolved` is written silently and the row
  reddens on its own `results` assertion instead. Armed either way; see owner card 1.

## 8. Judgment calls and declared deviations

- **D-1 · The C2 rows are now proven at `PR`, not only at the parser.** Plan 9 §6 defines the row
  boundary as `PR(body_bytes)`; the implementer proved the eight shapes at
  `parse_items_processed_body`. Rather than relocate the row (rule 17, owner-only), I **added** the
  command-boundary test and kept the parser tests, mirroring the shipped and APPROVED plan-7
  precedent exactly (`test_receive_stock_demand_webhook.py::test_c2a_c2x_malformed_bodies_write_nothing_through_the_command`
  beside `test_stock_demand_request.py`). One parametrized test plus two singles, not eight.
- **D-2 · Plan 9's C4 rows restored to `q = 8`.** The §6 preamble says a row stating `q = n` sets
  item I's quantity to `n`; the implementer read it the other way and asserted against F0's default
  4. I set `seeded.item.quantity = 8` before `CR`. No expected value in those rows now coincides
  with another fixture number.
- **D-3 · C6(b) is proven at S8.** Eight of the nine sites compute their own `now` internally, so no
  fixture can name the instant they stamp. S8 is the one site whose `now` is `ctx.now` — the
  implementer's flagged judgment call — and it is a **full command boundary**, so this is a fixture
  choice, not a narrower surface (rule 17 not engaged). The consequence the implementer flagged
  (`task.updated_at` and `assignment.updated_at` are not bit-identical at S8 only) is real and is
  not asserted by any row.
- **D-4 · C4(e)'s working step is not built.** The row says "T `working` with a `working` step …
  its step still `working`". `test_process_items_processed.py` has no step teardown and nothing in
  the command's path reads task steps, so I set T to `working` without a step and assert the F3
  clause as a task fingerprint including the step count. Declared rather than done silently.
- **D-5 · C8(b) has no test at all.** The plan declares the interleaving unforceable and routes it
  to a structural check (§9 rule 9); writing a two-request test that passes by luck is the B1
  anti-pattern. The structural check is written out in table 2.
- **D-6 · Shared landed edits were applied once, not once per cell.** Where two cells name the same
  edit at the same site and both rows' tests live in one file, one run shows each row's own
  distinguishing assertion red — which is precisely what §9 rule 8 asks to be *measured*. Re-running
  the identical command for the second cell would be over-evidence, not evidence. Every such pair is
  listed in §4 and marked `ARMED-SHARED` in table 2.
- **D-7 · The registry's 85 sites were not independently re-derived.** I proved the collector
  observes four planted construct kinds, a paused-driver change and a stale entry — and I checked
  explicitly that each probe's **own line** is named, because inserting a line into `update_task.py`
  shifts every registered line number below it and would redden the guard by itself.

## 9. Proposed plan-cell backfills (the coordinator folds these; I edited no cell)

| Id | Cell | Proposal |
|---|---|---|
| B-1 | plan 9 **C2(a)** mutation | Record `EQUIVALENT`: the only mutant isolating the list-ness clause (drop `not isinstance(payload, list)`, keep `len(payload) == 0`) still lands `b"{}"` on the surviving clause. The class-2 note was right. |
| B-2 | plan 9 **C2(d)** mutation | An isolating site **does** exist: `items_processed_request.py` (definition site) — `item.get("article_number", "<placeholder>")` → `[{}]` parses and the request returns 200. Fill the cell. |
| B-3 | plan 9 **C3(c)** mutation | Name **two** sites: the unlocked discovery predicate **and** the in-loop F5 ladder guard. At the discovery site alone the mutant is EQUIVALENT — the ladder's own frozenset check absorbs it. |
| B-4 | plan 9 **C6(a)** mutation | Same correction as B-3: "drop `state.in_(ACTIVE_ASSIGNMENT_STATES)` from the unlocked discovery predicate" is EQUIVALENT alone; the ladder guard must go too. Measured both ways. |
| B-5 | plan 9 **C6(b)** mutation | Same correction as B-3; with both sites hand-typed the cell's predicted outcome (`resolved`/`early` on the second delivery) is exactly what happens. |
| B-6 | plan 9 **C8(c)** mutation | The cell names `process_items_processed.py`; the symbol is `_move_assignment.py:resolve_processed_group`. File correction only — the edit itself is right. |
| B-7 | plan 9 **§7 sizing note** | "43 criterion rows" → **44** (script-derived; per-criterion summands in §4). |
| B-8 | plan 10 **C5(b)** mutation | The predicted failure mode is wrong: `_move_assignment.py:74-79` does **not** refuse, because `resolve_processed_group` never calls `_assert_allowed_move`. The stale decision is written silently and the row reddens on its own `results` assertion. Restate — and see owner card 1. |
| B-9 | plan 10 **C4(h)** mutation | Record `EQUIVALENT`: with the stale entry planted, dropping the `function_exists` assertion leaves the same test red on the adjacent `function_contains_call` assertion. To isolate the staleness check both assertions would have to go, which is a different mutant. |

## 10. Candidate criteria (no row covers these; I wrote no test for them)

- **CC-1 — `resolve_processed_group` writes without consulting the move table.** Every other write
  path goes through `move_assignment`, which calls `_assert_allowed_move` first;
  `resolve_processed_group` does not. Measured, not inferred: under P27 the command wrote an
  `awaiting → resolved` transition on an assignment that was actually `in_progress`, silently, and
  the plan's own predicted 500 never occurred. **Not a defect on this tree** — the F5 ladder's
  post-lock re-read keeps it unreachable — but the safety depends entirely on every caller. Owner
  card 1.
- **CC-2 — the per-row `:updated` event is unconditional.** `resolve_processed_group` always
  appends it, unlike `move_assignment`'s `any(delta != 0)` guard. The implementer declared this as
  safe "only because every caller passes a non-empty, all-active group". No row states that
  premise, so nothing fails if a future caller breaks it. Same root cause as CC-1; folded into
  owner card 1.
- **CC-3 — plan 10 has no §9 rule-18 row for `sync_task_stock_assignments`.** The name is
  registered in §6.5 and called from nine sites; plan 9's twin (`resolve_processed_group`) got
  C8(c), this one got nothing. The two implementer direct-call tests are the only evidence and are
  declared here rather than shipped silently (table 3). Owner card 2.
- **CC-4 — the second router route has no lettered criterion row.** Plan 9 task 3 adds it and the
  implementer's two router tests (`test_items_processed_route_forwards_raw_bytes_and_headers_and_renders_build_ok`,
  `…_renders_build_err_for_a_faked_auth_error`) trace to the task, not to a row. Declared, not
  deleted — plan 7's route has the same shape and shipped the same way.
- **CC-5 — the S8 timestamp divergence is unasserted.** At S8 only, `task.updated_at` (wall clock,
  inside the helper) and `assignment.updated_at` (`ctx.now`) differ. C6(b) pins the assignment
  side; nothing states whether the divergence is intended.
- **CC-6 — `remove_task_steps` (the plural S8 caller) is never driven.** Both public commands carry
  the sync call and the registry guard covers both, but only `remove_task_step` is exercised
  end-to-end. Cheap to add if the owner wants it; no row asks for it today.

## 11. What variation I did **not** spend — where the reviewer's budget buys something new

- **No second mutant of the same sign anywhere.** Every cell got one landed edit at the site it
  names (or its recorded re-siting). Variation in *shape* is unspent.
- **No condition variation:** same `TZ`, same locale, same six xdist workers, same slot. A run under
  a different `TZ` or worker count is entirely new evidence.
- **No structural read of `_locks.py`** beyond what C8(b)'s check needs — I did not verify the
  ascending-lock statement against the `client_id`-is-not-creation-order hazard by observation.
- **No independent re-derivation of the 85-site registry.** I trusted the implementer's AST
  collector as an instrument and proved only that it *can* observe six planted things; whether it
  *misses* a seventh construct class is unprobed, and the guard is load-bearing for plan 10's
  C1(b),(c),(e),(f),(i),(j),(l) per the implementer's own §6.
- **No HTTP-layer coverage.** Every row is proven at its command boundary, as the plans specify;
  the router is exercised only by the two untraced wiring tests (CC-4).
- **No `remove_task_steps` (plural) path** (CC-6), and no second workspace in the plan-10 fixtures
  (tenancy is covered only in plan 9 C3(k)).
- **No repetition of the C5 rows.** Determinism there is by construction — a referee lock plus two
  observed blocks — and looping them would add confidence, not evidence.
