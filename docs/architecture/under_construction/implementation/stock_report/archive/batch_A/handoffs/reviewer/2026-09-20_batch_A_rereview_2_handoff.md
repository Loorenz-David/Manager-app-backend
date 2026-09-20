---
plan: batch A (1, 2, 3)
role: review
round: batch_A-rereview-2
state: APPROVED
date: 2026-09-20
actor: Claude Opus 5 (plan-reviewer)
tree: f2157bd
---

# Batch A re-review 2 — after fix round 2

**Tree identity.** Session HEAD is `a18d2b3`; `git status --porcelain` empty at entry and at close.
`git diff --stat f2157bd..a18d2b3 -- app/` is **empty** — the orchestrator's commit touches only
`master_plan.md` and this round's prompt — so the L4 stamp on `f2157bd` (**21 failed / 3264 passed /
2 skipped**, failure IDs identical to the 21-ID baseline in both directions) is tree-valid for this
review and is **consumed by citation, not re-run** (charter test-evidence section; the prompt also
forbids it). Corroborating the citation structurally: exactly **one** test function was deleted from
the batch and **none** added (`grep -c '^async def test_'` on both touched files across
`983d774..f2157bd`: 16 → 15 and 16 → 16), which is exactly the −1 against the previous 3265.

**Perimeter (verified, not reconstructed).** The fix cycle is `5dbb9eb` + `f2157bd`. Its union of
changed paths is: `consistency.py`, `_task_flag.py`, `test_consistency_check.py`,
`test_repair_stock_report.py` (app, **+261/−31**, derived by `--numstat`), three plan files, and the
fix handoff. **No escape, no master-plan edit, no tracker edit, no graph write.** The three plan
diffs are pure appends at end-of-file (`grep -c '^-[^-]'` over them = **0**) — Review-log entries
only; no criteria table, task list or §4 list touched. `docs/archgraph-anchor-observations.md` and
the reviewer handoff in the wider `983d774..f2157bd` range belong to the orchestrator's own commits
(`056287e`, `02745bb`), not to this cycle.

**Review history.** Review 1 (`0d5d31d`): 125/30/15 of 170, CHANGES_REQUESTED. Re-review 1
(`983d774`): **168/2/0**, CHANGES_REQUESTED on plan 3 alone — F-R1 (blocking), F-R2, F-R3. Owner
ruled card 1 (restore `expected_task_flag`'s workspace filter; §6.5 amended). One fix round ran.
This re-review is scoped to those three findings plus the signature-change regression. The other
166 rows are not re-verdicted and were not re-run.

---

## 1. Verdict

**APPROVED.**

| Phase | Rows | PASS | FAIL | NOT_VERIFIED |
|---|---|---|---|---|
| 1 | 53 | 53 | 0 | 0 |
| 2 | 75 | 75 | 0 | 0 |
| 3 | 42 | 42 | 0 | 0 |
| **Total** | **170** | **170** | **0** | **0** |

All three findings are CONFIRMED by measurement, not by diff. The blocking one is closed on both of
its halves: the production predicate is restored, **and** the guard that could not observe it now
reddens at every one of the six tenancy sites — including the site the plan never named. Zero
blocking, zero should-fix, four new notes, three lessons. Batch A is done; no fourth round.

## 2. ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. Card 1 from re-review 1 was ruled, implemented verbatim, and is now
measured closed.

## 3. The six filter mutations

Each applied alone to `consistency.py`, asserted present on disk, `__pycache__` cleared, run at L1
on `test_consistency_check.py` (16 tests), reverted and checksum-verified. The "re-review 1" column
is the same row's named mutation measured on the previous tree.

| # | Site | Re-review 1 | **Now** | The divergence that reddened C1(k) |
|---|---|---|---|---|
| M1 | `stock_report_items` select (`:125`) | RED | **RED** | `signature` on the foreign stale-signature row (+ 8 more) |
| M2 | `stock_report_history_records` select (`:204`) | GREEN | **RED** | `goal_total` on the foreign history record |
| M3 | `tasks` select (`:227`) | GREEN | **RED** | 10 foreign tasks, first `tsk_counter0_ws_sr_consistency-foreign`, stored `true` expected `false` |
| M4 | `_recompute_row_counters_for_workspace` (`:60`) | GREEN | **RED** | `counter_in_queue` on an **own** row — foreign assignment quantity leaks into W's counter |
| M5 | `_recompute_goal_totals_for_workspace` (`:93`) | GREEN | **RED** | `goal_total` on **own** `srh_…` — foreign credit leaks into W's goal |
| M6 | `expected_task_flag` (`:105`) — the production defect card 1 named | *(the shipped code)* | **RED** | `{'client_id': 'tsk_sr_consistency-own', 'kind': 'task_flag', 'expected': 'true'}` |

**Four green → red, and M6 reproduces card 1's story exactly**: with the predicate gone, W's own task
`tsk_sr_consistency-own` is reported as needing its stock flag set `true` on the strength of a row
that belongs to workspace F. That is the sentence the owner ruled on, now a red test.

M3 and M6 are independently armed and do not mask each other: M3's red is a set of **foreign** task
client_ids reported into W's result, M6's red is W's **own** task mis-derived. Two different filters,
two different failure shapes, one assertion.

## 4. F-R1 / F-R2 / F-R3

### F-R1 — CONFIRMED (both halves)

*Production half.* `expected_task_flag(session, workspace_id: str, task_id: str)` carries
`StockTaskAssignment.workspace_id == workspace_id` as the first clause of its `WHERE`
(`consistency.py:101-111`); `compute_stock_report_divergences` threads `workspace_id` at `:235`;
`recompute_task_stock_flag(session, workspace_id, task_id)` threads it at `_task_flag.py:18-19`.
A repo-wide `grep -rn --include="*.py"` (outside `.venv`) returns **five** hits and no unthreaded
call site anywhere — production, tests or `scripts/`. This is literally the owner's ruling and
literally master plan §6.5 as amended.

*Coverage half — the part that matters.* §3's table is the measurement. All six sites redden; the
four that were inert are armed. Beyond the row's named mutation I ran the absence row's
charter-rule-15 presence probe (**M10**): point C1(k)'s own final assertion at the **foreign**
workspace instead of the own one. It reddens with **nine divergences spanning all eight MC-20
kinds** — `counter_in_queue/in_progress/awaiting`, `goal_total`, `order_density`,
`priority_order_nullness`, `signature`, `task_flag` ×2. So the instrument demonstrably *can* observe
the presence it is asserting the absence of, which is the one thing an absence row cannot prove by
passing.

*Is the fixture faithful, or shaped to the implementation?* **Faithful, and necessarily stronger
than the row's literal text.** A drift planted *entirely inside* workspace F cannot arm four of the
six filters, by construction: `_recompute_row_counters_for_workspace` and
`_recompute_goal_totals_for_workspace` are consumed by `counters.get(own_row.client_id)` /
`goals.get(own_history.client_id)`, and `expected_task_flag` is called once per **own** task — so a
purely-foreign row never appears under any key the own-workspace pass looks up. The only fixture
that can observe those three boundaries is one carrying **cross-workspace reference rows**: an
assignment with `workspace_id = F` and `stock_report_item_id` / `credited_history_record_id` /
`task_id` in W. `StockTaskAssignment` permits exactly that (independent FKs, no composite
constraint), it is the hazard card 1's story described, and it is what the round built. That is the
row's *purpose* implemented, and it is why I am recording the row's text as a plan defect
(lesson L-16) rather than the test as a fixture defect.

*And the own-workspace `[]` is exact for the right reason.* Every own-workspace entity the fixture
plants is proven to be under the check's eye by a red that names it: M4 reports an **own** row's
counter, M5 an **own** history record's goal, M6 the **own** task. None of the `[]` is vacuous, in
any of its parts.

*Residual, recorded as a note, not a finding.* The lettered clause is 8/10, not 10/10 — see N-S1.

### F-R2 — CONFIRMED

`test_manual_repair_clears_false_positive_task_flag` (`test_repair_stock_report.py:117-165`) now
asserts the complete record tuple as a set equality —
`("task", T, "is_stock_assignment", "true", "false", "manual", U, ctx.now)` — and then
`compute_stock_report_divergences(...) == []`. **Measured (M7):** the row's named mutation
(hard-code the task record's `recomputed_value` to `"true"`) reddens **exactly this test**
(`1 failed, 16 passed`), where at re-review 1 it left the whole file green. C3(d)'s missing half is
closed.

**C3(e) is undamaged, and proven independently armed (M9, my variation):** hard-coding the same
field to `"false"` instead reddens `test_manual_repair_fixes_counter_and_task_flag_and_records_each_change`
and **not** C3(d)'s test. The two directions of the one write now bite on opposite mutants, which is
precisely what lesson L-13 asked for.

### F-R3 — CONFIRMED

`test_consistency_matches_migrated_worker_schema` is gone from
`test_consistency_check.py`. Plan 1 C2(a)'s owner,
`test_stock_report_schema.py::test_stock_report_migration_matches_runtime_metadata` (`:264-279`), is
intact and byte-for-byte what re-review 1 verified. A function-name diff of both touched test files
across the cycle shows **exactly one** deletion and **zero** additions, so nothing else went with
it and no new orphan arrived. The one new module-level symbol, `_foreign_task_item`, has six call
sites inside C1(k) (charter rule 4 satisfied) and is not collected as a test.

## 5. Regression check

- **C1(d) and C1(e) still armed.** M8 (drop the `task_flag` kind from
  `compute_stock_report_divergences`) reddens **4 tests** at L1, including
  `test_task_flag_divergence_is_reported_when_assignment_is_missing` (C1(d), expected
  `{stored: 'true', expected: 'false'}` missing from the result) and
  `test_counter_and_signature_divergences_are_reported` (C1(e), `expected: 'true'` missing). The
  `expected_task_flag` signature change did not weaken either.
- **The threaded callers.** `recompute_task_stock_flag` is the only caller of `expected_task_flag`
  besides the check itself, and it has **zero callers anywhere in the repository** — unchanged from
  re-review 1's N-R3, so the signature change reaches no live call path and cannot regress one. It
  does now diverge from §6.5's `_task_flag.py` row: see **N-S2**.
- **C1(k)'s large fixture swallowed nothing.** It is a self-contained test function: it seeds its
  own two workspaces, shares no fixture with any other row, commits nothing (flush-only under
  `db_session`, which rolls back — charter rule 11½), and its helper is private to it. The other 15
  tests in the file passed in every one of my ten probe runs, and the whole file passes with all
  probes reverted (file hash restored to `453def0c…`; `repair_stock_report.py` is still
  `e9b2ae0d…`, the value re-review 1 recorded, confirming the cycle never touched it).
- The 166 rows outside the fix perimeter are covered by the cited L4 and were not re-verdicted.

## 6. Findings

**None.** Zero blocking, zero should-fix. The notes below are debt with named destinations and do
not gate the batch.

### Notes (new this round)

- **N-S1 — C1(k)'s lettered clause is 8/10 while its kind coverage is 8/8.** The row says "every
  C1(a)–(j) drift planted in the foreign workspace". Measured by M10, the foreign workspace carries
  all eight MC-20 kinds, but two *directions* are absent: **(e)** a task that has an assignment and
  a `false` flag (only the `true`-with-no-assignment direction is planted) and **(h)** a row with
  `priority = NULL` and `priority_order` set (only the inverse is planted). Both are the same kind
  through the same filter as their planted twin, so **no discrimination is lost** — which is why
  C1(k) is PASS, not a partial. The fix handoff §2's phrase "all ten drift kinds are planted" is
  loose (ten letters, eight kinds); by kind it is accurate. Destination: coordinator, at the next
  plan-3 fold — either plant the two twins or restate the clause per kind.
- **N-S2 — §6.5 still registers `recompute_task_stock_flag(session, task_id)`** (master plan line
  376) while the owner's card-1 ruling forces `(session, workspace_id, task_id)`, which is what
  shipped. The round could not fix this — its prompt forbade master-plan edits — and it declared the
  threading in its handoff §3 and in plan 3's Review log, so this is documentation drift, not an
  undeclared deviation. Destination: orchestrator, same act as the `lock_stock_report_history_records`
  addition. See lesson L-18.
- **N-S3 — `set_task_stock_flag`'s UPDATE has no workspace predicate.** `_task_flag.py:8-12` keys on
  `Task.client_id` alone. This is contract-faithful: MC-15's statement as quoted in plan 3 task 3
  and registered in §6.5 line 376 has no workspace clause, and it is unreachable today because the
  only caller derives its task ids from the now workspace-scoped scan. But it is the **write** half
  of the boundary the owner just closed on the **read** half: a future caller that hands it a task
  id it did not derive from a workspace-scoped query writes across the tenancy line, with no
  predicate to stop it. Destination: **phase 4**, which is where inline self-heal starts calling
  `recompute_task_stock_flag` — the phase that makes it reachable is the phase to decide it.
- **N-S4 — plan 3 C1(l)'s stated outcome is not achievable with its own fixture** (seen in passing,
  via M8). The row says the check returns `[]`; the shipped test asserts the (kind, field) list
  equals `[("task_flag", "is_stock_assignment")]`, because the fixture's `resolved_early` assignment
  makes the seeded task's expected flag `true` while the seed leaves it `false`. The row's
  discriminating content — no `counter_*` kind counts a terminal state, and the `goal_total` Σ
  includes the `resolved_early` credit — is fully asserted and in one respect stronger (exact list
  equality pins that the task flag is the *only* divergence). The row was re-confirmed armed at
  re-review 1 and is **not** re-verdicted here. Deviation undeclared (charter rule 14).
  Destination: coordinator fold, with N-R5 / N-R7. See lesson L-17.

Re-review 1's **N-R1…N-R9** and review 1's **N-1, N-2, N-3, N-6, N-8, N-9** remain open and out of
scope, as the prompt directs; they are carried unchanged in §7.

## 7. Carry-forward dispositions

| Item | Destination |
|---|---|
| N-S1 C1(k)'s two unplanted drift directions | coordinator, next plan-3 fold |
| N-S2 §6.5's `_task_flag.py` registry row | orchestrator, with the §6.5 housekeeping |
| N-S3 `set_task_stock_flag` has no workspace predicate | **phase 4** (inline self-heal, first real caller) |
| N-S4 C1(l)'s outcome cell vs its fixture | coordinator fold (with N-R5 / N-R7) |
| N-R1 unlocked post-read goal-total row | phase 5 (inline goal credit) |
| N-R2 C5(c) payload enumeration | phase 13A |
| N-R3 three uncalled registry helpers | phases 4 / 5 / 11, at first call |
| N-R4 two leaked kit users | phase 13A (isolation pass) |
| N-R5 / N-R7 fixture deviations | coordinator fold into plans 2 and 3 |
| N-R6 sequential asserts | plan 2, next fold |
| N-R8 / N-R9 | housekeeping backlog |
| N-1 implementation-coupled assertions | backlog (owner rule 2026-09-19: never a fix-round item) |
| N-2 `expected_task_flag` N+1 per task | phase 11 (or wherever the check's cost is measured) |
| N-3 the task scan includes soft-deleted tasks | coordinator fold into plan 3 / phase 4 |
| N-6, N-8, N-9 | as routed at review 1 |
| Deleted `Settings` coverage (3 settings) | phase 6 |
| Graph delta for batch A | orchestrator's approval gate |
| Tracker row → APPROVED, and §6.5 line 376 | orchestrator (this prompt forbids me the master plan) |

## 8. Lessons for the plans (coordinator folds upstream)

- **L-16 — a tenancy row whose fixture lives only in the foreign workspace is inert by
  construction, and C1(k) says exactly that.** This is one level below L-12. Four of the six
  workspace filters here are *lookup-key* filters, not *scan* filters: their output is consumed as
  `counters.get(own_row_id)` / `goals.get(own_history_id)`, or called once per own task. A row that
  exists only in F never appears under any key the own-workspace pass reads, so deleting the filter
  changes nothing observable. Only a **cross-workspace reference row** — foreign `workspace_id`,
  own `stock_report_item_id` / `task_id` / `credited_history_record_id` — can observe those
  boundaries. A plan that writes "plant the drift in the foreign workspace" has specified the inert
  version, and an implementer who follows it literally ships a guard that cannot fail. Any future
  isolation criterion must name the cross-reference shape in its fixture cell.
- **L-17 — a row's "exact outcome" must be computed from its own fixture, including the side
  effects the fixture cannot avoid.** C1(l) asks for `[]` while planting a `resolved_early`
  assignment on the seeded task — which, by MC-20's own task-flag rule, *is* a divergence. The
  honest outcome is one `task_flag` entry. Writing `[]` forces the implementer to either deviate
  silently or damage the fixture.
- **L-18 — a ruling that amends one registry row amends its callers in the same act.** Card 1
  changed `expected_task_flag`; §6.5's `_task_flag.py` row, which describes the only function that
  calls it, still carries the old shape. The fix round was forbidden the master plan and declared
  the divergence correctly, so nothing was hidden — but the registry is the artifact the *next*
  phase reads, and phase 4 reads that exact row.

## 9. What I ran

| # | Hypothesis | Scope | Command / action | Result |
|---|---|---|---|---|
| — | tree identity | — | `git status --porcelain`; `git diff --stat f2157bd..a18d2b3 -- app/` | clean; **empty** → the cited L4 is tree-valid, **not re-run** |
| — | cycle perimeter | — | `git diff --name-only` per commit `5dbb9eb`, `f2157bd`; `--numstat` over `app/` | 4 app files +261/−31, 3 plan files, 1 handoff. No escape |
| — | plan-file perimeter | — | `git diff … plans/ \| grep -c '^-[^-]'` | **0** deletions; appends only |
| — | the −1 in the L4 count | — | `grep -c '^async def test_'` on both files at `983d774` vs `f2157bd`; name diff | one deletion, zero additions → 3265 − 1 |
| — | threaded call sites | — | `grep -rn --include="*.py"` repo-wide (minus `.venv`) for both symbols | 5 hits, none unthreaded |
| — | F-R3 survivor | — | read `test_stock_report_schema.py:264-279` | intact |
| M1–M6 | each workspace filter reddens C1(k) | L1 | probe harness on `test_consistency_check.py` | **RED ×6** (§3) |
| M7 | F-R2's named mutation reddens C3(d) | L1 | probe harness on `test_repair_stock_report.py` | **RED**, 1 failed / 16 passed |
| M8 | C1(d)/C1(e) still armed after the signature change | L1 | drop the `task_flag` kind | **RED ×4**, both rows' tests among them |
| M9 | *(variation)* C3(e) is armed independently of C3(d) | L1 | hard-code `recomputed_value` to `"false"` | **RED** on C3(e)'s test only |
| M10 | *(variation, charter rule 15)* C1(k)'s instrument can observe presence | L1 | point its assertion at the foreign workspace | **RED**, 9 divergences, **all 8 kinds** |
| — | lint | — | `ruff check` over the four perimeter files | All checks passed |
| — | closing cleanliness | — | `git status --porcelain`; `shasum -a 256` on every probed file | empty; all byte-identical |

**No L4 was run** (charter test-evidence section; the prompt also forbids it). My `app/` is
byte-identical to the stamped `f2157bd` and no hypothesis in this re-review was repository-wide. No
clean-control L1 run was taken either: M1 reddened on the first attempt with the other 15 tests
green, which establishes harness liveness more strongly than a green control would, and every later
probe reported the same 15 passes.

## 10. Mutation-probe declaration

Ten probes, each: back up the file and record its SHA-256 → apply exactly one edit → **assert the
mutated text is present on disk and the original absent** → clear every `__pycache__` under `app/`
→ run pytest → restore from backup in a `finally` → **assert the SHA-256 equals the pre-probe
value**. Any anchor matching ≠ 1 time aborts the probe before an edit is written.

**Files mutated and restored (3):**

```
1bc30f3849fd871e49a43151e7f376aacade70947a01c36490d379de1304b5b7  beyo_manager/services/queries/stock_report/consistency.py          (M1–M6, M8)
e9b2ae0d59b3f984be7be98006db86a7bf5244c9de48bca8a04738b0f21b4a04  beyo_manager/services/commands/stock_report/repair_stock_report.py (M7, M9)
453def0cbe1c433fa954574a6deb46d15b63987b32f5f71dae285f09d47d552c  tests/integration/services/queries/stock_report/test_consistency_check.py (M10)
```

`repair_stock_report.py`'s hash is the same value re-review 1 recorded on `983d774` —
independent evidence that fix round 2 never touched it and that my probes reverted exactly.

**Files created: none.** No probe file was added to the tree; the harness and its backups live
outside the repository (session scratchpad). `git status --porcelain` is **empty** at close;
`git stash list` is empty; HEAD is `a18d2b3`, unmoved.

**Database/state side effects: none.** Every probe ran under the `db_session` fixture, which rolls
back; C1(k) and the repair tests flush only, never commit. The xdist worker databases are cloned
and dropped per run by `tests/database_isolation.py`. The configured development database was never
connected to.

**No anomalous readings.** All ten probes reddened on their first run, each on the test its
hypothesis named, and no probe required repetition.

**No commit, no graph write, no master-plan edit, no tracker edit.** The approval-gate commit,
the tracker row, §6.5 line 376, and the batch A graph delta are the orchestrator's.
