---
plan: 3 (owner-authorized amendment) + 12 (unblocked)
batch: D1
role: fix
route: production
round: 1
state: IMPLEMENTED
verdict: n/a (implementer)
date: 2026-09-22
actor: Opus implementer (orchestrated mode), slot `dp`
checkpoint: 2fb7acb
---

# Batch D1 — production fix 1. One defect, one predicate.

**Summary.** The `goal_total` reconciliation in APPROVED phase 3's consistency check now runs over
`quantity_requested_change` records only, per the owner's 2026-09-22 authorization
(*"yes i approve the fix ( only assignment reconciliation against goal records )"*). Plan 12's
witness `test_the_priority_record_snapshots_the_live_awaiting_counter` is green **without being
edited**; no test file in the repository was touched. L4 at `2fb7acb`:
**23 failed / 3740 passed / 1 skipped**, both ID diffs empty.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. The one thing that would have needed a decision — whether the
reconciliation should also skip *soft-deleted* goal records — was **not** decided and **not**
implemented; it is left as candidate criterion CC-2 in plan 3's Review log, unreached by any
shipped code path, for the coordinator to route if it ever becomes reachable. Raising it as a
card now would be asking the owner to rule on a behaviour nothing in the repository can produce.

## 1. Write perimeter — cycle-scoped, declared in full

**Production (1 file, committed at `2fb7acb`):**

| File | Change |
|---|---|
| `app/beyo_manager/services/queries/stock_report/consistency.py` | 2 hunks, **+8 / −1**: the `histories` selection in `compute_stock_report_divergences` gains the type predicate; the `enums` import gains `StockReportHistoryRecordTypeEnum` |

**Documents (2 files, committed in the commit immediately following `2fb7acb` on `main` — docs
only, no `app/` path; its SHA is deliberately not quoted here because it does not exist at the
moment this sentence is written, and a placeholder SHA has already cost this batch once):**

| File | Change |
|---|---|
| `…/stock_report/plans/plan_3.md` | one appended Review-log section (owner-authorized amendment, judgment calls, candidate criteria CC-1/CC-2). **No criteria table touched.** |
| `…/stock_report/plans/plan_12.md` | one appended Review-log section (blocker cleared, nothing in plan 12 changed). **No criteria table touched.** |

**Handoff:** this file.

**Tool-recorded state: NONE.** No archgraph write was made — see §7.

**Test files touched: NONE.** (Tester: nothing to re-arm.)

**Files touched by a mutation probe and reverted (listed separately, per doctrine):**
`app/beyo_manager/services/queries/stock_report/consistency.py` — twice (M1, M2 below). Both
reverted with `git checkout --`; `git diff --quiet` exit **0** and `git status --porcelain` empty
after each.

**Not touched, deliberately:** `repair_stock_report.py`, `master_plan.md`, the intention, every
test file, every criteria table.

## 2. The diff

```diff
-from beyo_manager.domain.stock_report.enums import ACTIVE_ASSIGNMENT_STATES
+from beyo_manager.domain.stock_report.enums import (
+    ACTIVE_ASSIGNMENT_STATES,
+    StockReportHistoryRecordTypeEnum,
+)
@@ compute_stock_report_divergences — the `histories` selection @@
                 select(StockReportHistoryRecord)
-                .where(StockReportHistoryRecord.workspace_id == workspace_id)
+                .where(
+                    StockReportHistoryRecord.workspace_id == workspace_id,
+                    StockReportHistoryRecord.type
+                    == StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
+                )
                 .execution_options(populate_existing=True)
```

Enum member, never a spelled string (§9 rule 16). The model attribute is `type`, not
`record_type` (`models/tables/stock_report/stock_report_history_record.py:39`) — my first draft
wrote `record_type` and would not have resolved; caught before any run.

## 3. The repair mirror — checked independently, and NOT added

The prompt instructed me not to mirror the filter into `repair_stock_report.py` and to stop and
report if my reading disagreed. **It does not disagree.** Verified by grep over `app/`:

- production consumers of `compute_stock_report_divergences` are exactly
  `repair_stock_report.py` (`:170`, `:217`, `:294`) and `get_stock_report_consistency.py:10`;
  the third consumer is the test helper `tests/helpers/stock_report.py:143`;
- `repair_stock_report.py` constructs no divergence of its own — its `goal_total` UPDATE branch
  (`:248-255`) consumes only entries from that list.

A type guard on that UPDATE would therefore be unreachable and unarmable (**L-37**). Not added.

**One consequence worth the reviewer's eye, which nobody asked me to check:** the repair's
history-record lock set (`:207-213`) is also derived from the divergence list, so it now locks
goal records only. Correct — a non-goal record can no longer be a repair target — but it *is* a
behavioural change beyond the emitted-divergence set, and it is the only second-order effect the
one-predicate framing hides. Stated here rather than left for the re-review to find.

## 4. Evidence ledger

Baseline comparator: the checked-in 23-ID set at
`handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt` (21 published IDs + the two
slot-sensitive `test_database_isolation` IDs, master plan §10 ruling). Slot `BEYO_TEST_SLOT=dp`
on every command. Commands run from `backend/app/` with `PYTHONPATH=. .venv/bin/pytest`.

### 4.1 Red baseline, before the first production edit

| | |
|---|---|
| Hypothesis | the witness is red on the unmutated tree, for the stated cause |
| Scope | L1 (whole file, never `-k`) |
| Command | `BEYO_TEST_SLOT=dp PYTHONPATH=. .venv/bin/pytest tests/integration/services/commands/stock_report/test_stock_report_priority_and_ordering.py -q` |
| Tree | `5d27ef0`, `git status --porcelain` empty |
| Result | **1 failed / 15 passed** — failing id `::test_the_priority_record_snapshots_the_live_awaiting_counter` |

### 4.2 The witness, after the fix, unedited

| | |
|---|---|
| Scope | L1, same command as 4.1 |
| Tree | `2fb7acb` content (measured on the dirty tree that became that commit) |
| Result | **16 passed** — witness green; the other 15 tests of the file unchanged |

The test file's mtime and content are untouched: `git status --porcelain` listed only
`consistency.py` at that moment, and no test path appears in either commit of this session.

### 4.3 L2 — the whole stock_report surface

| | |
|---|---|
| Hypothesis | the amendment is inert for everything that was already correct |
| Scope | L2 — every stock_report test tree plus every file importing the changed module |
| Command | `BEYO_TEST_SLOT=dp PYTHONPATH=. .venv/bin/pytest tests/integration/services/commands/stock_report/ tests/integration/services/queries/stock_report/ tests/integration/models/stock_report/ tests/integration/helpers/test_stock_report_helper.py tests/integration/services/commands/reset/test_stock_report_reset.py tests/unit/domain/stock_report/ tests/unit/services/commands/stock_report/ tests/unit/routers/api_v1/test_stock_report_router.py tests/unit/routers/api_v1/test_location_tracker_webhooks_router.py -q --tb=line` |
| Tree | `2fb7acb` content |
| Result | **638 passed / 0 failed / 0 errors** |

Phase 3's own files inside that run, collected counts, all green:

| File | Tests |
|---|---|
| `tests/integration/services/queries/stock_report/test_consistency_check.py` | 16 |
| `tests/integration/services/commands/stock_report/test_repair_stock_report.py` | 17 |
| `tests/integration/services/commands/stock_report/test_goal_credit.py` | 23 |
| `tests/integration/services/commands/stock_report/test_move_assignment.py` | 59 |
| `tests/integration/services/commands/stock_report/test_remove_assignment.py` | 4 |
| `tests/integration/helpers/test_stock_report_helper.py` (`assert_stock_report_clean`) | 1 |
| `tests/unit/routers/api_v1/test_stock_report_router.py` (consistency + repair endpoints) | 53 |
| `tests/integration/services/commands/stock_report/test_stock_report_priority_and_ordering.py` (plan 12) | 16 |

### 4.4 Named mutation M1 — revert the filter (the prompt's one mutation)

| | |
|---|---|
| Hypothesis | the witness is red without the type predicate — i.e. the predicate is what makes it green |
| Site | `consistency.py`, **call site**: the `where(...)` of the `histories` selection inside `compute_stock_report_divergences` (not the enum definition). Siting asserted by printing lines 200-216 after applying the probe — the predicate was gone from that selection and from nowhere else (`git diff --stat`: 1 file, −4/+1). |
| Scope | L1 |
| Command | as 4.1 |
| Tree | `2fb7acb` + probe |
| Result | **RED — 1 failed / 15 passed**; observed failing id `::test_the_priority_record_snapshots_the_live_awaiting_counter`, observed assertion `tests/helpers/stock_report.py:143` (`assert_stock_report_clean`) — the §9-rule-2 clause the test's own docstring names, not one of the record-value clauses |
| Revert | `git checkout --` → `git diff --quiet` exit **0**, `git status --porcelain` empty |

### 4.5 Probe M2 — proof item 4: does a goal record's own reconciliation still bite?

**Yes, and it was measured, not asserted.** Two independent pieces:

*(a) an existing test already plants a goal-record drift and it passes* —
`test_consistency_check.py::test_goal_signature_and_density_divergences_are_reported` seeds a
`QUANTITY_REQUESTED_CHANGE` record with `quantity_awaiting = 5` against a credited assignment of
4, and asserts the exact `goal_total` entry `{stored: 5, expected: 4}`. Green in 4.3. So the rule
still fires on goal records after the narrowing.

*(b) the guard proof — plant the defect the narrowing could have introduced and watch it redden:*

| | |
|---|---|
| Hypothesis | I narrowed the rule without disabling it; if the predicate selected the wrong type the goal side would go unchecked and the suite would say so |
| Site | `consistency.py`, same call site: `QUANTITY_REQUESTED_CHANGE` → `PRIORITY_CHANGE` |
| Scope | L1 over the two goal-side files |
| Command | `BEYO_TEST_SLOT=dp PYTHONPATH=. .venv/bin/pytest tests/integration/services/queries/stock_report/test_consistency_check.py tests/integration/services/commands/stock_report/test_repair_stock_report.py -q --tb=line` |
| Tree | `2fb7acb` + probe |
| Result | **RED — 2 failed / 31 passed.** `test_consistency_check.py::test_goal_signature_and_density_divergences_are_reported` (observed assertion at `:449`, the kind-list equality — the `goal_total` entry is missing) and `test_repair_stock_report.py::test_manual_repair_fixes_goal_total_and_writes_history_record` (observed `assert 5 == 4` at `:668` — the repair no longer heals the goal record) |
| Revert | `git checkout --` → `git diff --quiet` exit **0**, `git status --porcelain` empty |

This is declared as a **second** probe, distinct from the prompt's one named mutation: its
hypothesis is proof item 4's, not M1's, and M1 cannot answer it (removing the predicate widens
the rule, so the goal side stays covered either way).

### 4.6 Lint

`.venv/bin/ruff check` and `.venv/bin/ruff format --check` on the changed file: **All checks
passed / 1 file already formatted.**

### 4.7 The one L4 stamp

| | |
|---|---|
| Scope | L4 — the cycle's one authoritative stamp |
| Command | `BEYO_TEST_SLOT=dp PYTHONPATH=. .venv/bin/pytest -m 'not e2e' -q --tb=no` |
| Tree | **`2fb7acb`**, `git status --porcelain` **empty** (asserted before and after) |
| Result | **23 failed / 3740 passed / 1 skipped**, 72.0 s |
| IDs observed but not in the 23-ID baseline | **∅** |
| IDs in the baseline but not observed | **∅** |

The docs commit lands after this stamp and touches only `plans/*.md` and this handoff — no `app/`
path — so the stamp still covers the shipped code tree.

## 5. The one number in the prompt I did not reproduce, and why mine is right

The prompt set the expected L4 at **23 failed / 3739 passed / 1 skipped** and warned that the pass
count must not move. I measured **23 / 3740 / 1**.

The prompt's figure is off by one, arithmetically: the pre-fix run was 24 failed / 3739 passed / 1
skipped, total 3764. Fixing the witness moves **one test from the failed column to the passed
column** — it does not vanish. 23 + 3740 + 1 = 3764, the identical collection. A 3739 would have
meant a test disappeared. So the gate condition the prompt was reaching for (the 23-ID set, both
diffs empty, no test added) is **met**, and the pass count is exactly the one the arithmetic
predicts. Flagging it because a re-reviewer comparing against the prompt's literal will otherwise
open a finding on a non-defect.

## 6. What I could have hidden and am reporting

1. **I ran the L2 twice.** The first attempt carried `-p no:logging`, which disables the plugin
   that provides the `caplog` fixture, so two tests ERRORed at setup
   (`test_goal_credit.py::test_c2_a_downward_drift_self_heals_with_one_repair_record`,
   `test_move_assignment.py::test_c5_a_downward_drift_self_heals_with_one_repair_record`) —
   **636 passed / 2 errors**. Those errors were my flag, not the fix: I confirmed the cause by
   re-running one file alone with the flag and reading the fixture error, then re-ran the L2
   clean (638 passed). The second run is a correction of an invalid measurement, not a second
   helping of the same evidence, but it is a run I did not have to disclose and the budget said
   "one L2".
2. **My first draft of the predicate used a column that does not exist** (`record_type`; the
   model's attribute is `type`). It was never run — I checked the model before executing anything
   — but a session that only reported the final diff would look like it got it right first time.
3. **The narrowing changes the repair's lock set**, not just the divergence list (§3). Nobody
   asked about locks, and the prompt's "one filter is the whole fix" framing would have carried a
   silent omission comfortably.
4. **I did not add the `is_deleted` predicate** that MC-5's wording ("non-deleted
   `quantity_requested_change` record") implies. That is a real, if currently unreachable, gap
   between the contract and the check, and it is outside both the owner's authorization and this
   perimeter. Recorded as candidate CC-2 rather than quietly implemented — and rather than
   quietly forgotten.
5. **No archgraph delta was recorded** (§7), which means a reviewer reading "tool-recorded state:
   none" is reading a deliberate omission, not an absence of anything to say.

## 7. Architecture graph — no write, and one observation

`.archgraph/architecture.yml` is present. I recorded **no delta**, because the prompt's perimeter
is explicit ("one production file plus two plan Review logs. Nothing else") and a graph write is
tool-recorded state outside it. No symbol was deleted, renamed or moved, so the symbol-grep drift
check (doctrine step 4) returns nothing.

**The observation the coordinator may want to act on:** the graph already describes the
**fixed** behaviour. The `query-stock-report-consistency → table-stock-report-history-record`
`reads_from` edge (line ~14585) carries the evidence summary *"Sums workspace-scoped **goal
records** to recompute the goal total"*, with `inferenceReason` *"The goal_total divergence kind
is derived entirely from these rows."* That was **false of the code as written on 2026-09-20** —
it summed every history record — and is **true as of `2fb7acb`**. So this fix closes a graph/code
discrepancy rather than creating one, and no node or edge needs amending. The
`query-stock-report-consistency` node description ("Recomputes … the goal total …") is likewise
still accurate, though a future maintenance pass could sharpen it to name the goal-record scope.
Evidence summaries are immutable in this graph, so any sharpening is a reject-and-re-record, not
an edit — another reason not to improvise it inside a one-predicate fix round.

## 8. Tester contract (master plan §3B — this round is `production` route only)

- **Checkpoint SHA on a clean tree:** `2fb7acb` (`git status --porcelain` empty).
- **L4 stamp:** 23 / 3740 / 1, both ID diffs ∅ — §4.7.
- **Tests I wrote → the row each aimed at:** **none.** I authored, edited, renamed and deleted
  zero tests. The proof of this fix is an existing red test going green untouched.
- **Load-bearing pointer:** the behaviour is made true at
  `app/beyo_manager/services/queries/stock_report/consistency.py:compute_stock_report_divergences`,
  in the `histories` selection's `where(...)`. No lock is taken or released by this change; the
  lock the repair takes over history records (`repair_stock_report.py:207-213`) is unmodified
  code whose *input set* narrows as a consequence (§3).
- **Rows I know I did not exercise:** no criterion row anywhere asserts that the repair leaves a
  `priority_change` snapshot **untouched** — the destructive half of the defect. Plan 12 C3(d)
  covers only the read half, via `assert_stock_report_clean`. That is candidate CC-1 in plan 3's
  Review log; until the coordinator or owner authors it, the write half of this defect has no row.
- **A seam the production code does not offer:** none encountered.
- **Test files touched:** none — nothing to re-arm.

## 9. For the coordinator

1. Plan 3's tracker row and plan 12's tracker row were **not** written by me (orchestrator-only
   per master plan §4). Phase 12 remains `IMPLEMENTED`; the D1 blocker described in its Review
   log is cleared.
2. Two candidate criteria await routing: **CC-1** (the health check ignores non-goal records; the
   repair's non-write on them is unasserted anywhere) and **CC-2** (soft-deleted goal records vs
   MC-5). Both are in plan 3's Review log, authored as candidates only — no criteria table was
   edited.
3. The prompt's expected pass count (3739) should be corrected to **3740** wherever it is carried
   forward, or the next agent will read a non-defect as a regression (§5).
4. Consider whether the master plan's D1 baseline note should record that this session's L4 was
   taken at `2fb7acb` on slot `dp` with both diffs empty.
