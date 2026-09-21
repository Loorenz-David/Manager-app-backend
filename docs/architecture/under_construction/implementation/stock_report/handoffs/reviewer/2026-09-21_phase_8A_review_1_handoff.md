---
plan: 8A
role: review
round: 1
verdict: CHANGES_REQUESTED
date: 2026-09-21
actor: Codex
---

# Phase 8A review 1 — match preview and MC-21 extraction

## Verdict

**CHANGES_REQUESTED.** The Phase 8A implementation and all 20 active criterion rows are
independently green at their prescribed targeted boundaries, and all nine active named
mutations were observed red and reverted. The required L4 run cannot meet its own acceptance
condition, however: in the required `BEYO_TEST_SLOT=a8`, it has the published 21 failures plus
two `test_database_isolation` failures that are hard-coded for the forbidden `main` slot. Until
the verification environment is made self-consistent, the phase cannot receive the required
clean baseline stamp.

Checkpoint reviewed: `9105f718324b7bc2eda6f0aa555465e9f7fd8030` (`CHECKPOINT (not approved):
phase 8A match preview`). HEAD after it was documentation-only; separately, the starting
worktree carried concurrent batch-C2 changes outside this phase.

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — pending Architecture Graph observations

**Question:** Authorize promotion of the inferred match-preview endpoint, shared acceptability
evaluator, and their `depends_on` relationship?

**Story:** A future engineer opening the architecture map needs to see that the preview and create
paths share one acceptance decision, rather than assuming they are parallel implementations. The
three pending records describe exactly that boundary and point to the new route, evaluator, and
preview service. If left pending, the code works but the graph cannot be treated as settled
documentation.

**Branches:** authorize promotion — the reviewed map becomes human-confirmed · decline or defer —
the records remain pending and no architecture claim is promoted.

**Recommendation:** authorize promotion; each source symbol was re-read and supports its claim.

**On silence:** the graph review gate holds; no Architecture Graph mutation is made.

**Trace:** pending items `node:endpoint-stock-assignment-match-preview`,
`node:domain-assignment-acceptability-evaluator`, and
`edge:endpoint-stock-assignment-match-preview--depends_on-->domain-assignment-acceptability-evaluator`.

## Perimeter and baseline commands

| Command | Observed output |
|---|---|
| `git status --porcelain` | Concurrent, out-of-phase modifications were present at review start: batch-C2 files, including `enums.py`, location-tracker webhook files, and item-processed files. The required clean-tree precondition was not true. |
| `git log --oneline -5` | HEAD was `1803232`; checkpoint `9105f71` exists and is the Phase 8A checkpoint. |
| `git diff 798fc69..HEAD --stat` | 27 files / 3,628 insertions / 162 deletions; this includes later documentation and concurrent work, so it is not a Phase-8A-only diff. |
| `git diff 9105f71..HEAD --stat` | Seven documentation files only; no `app/` or `.archgraph/` production delta after the checkpoint. |
| `git diff --quiet` after each probe | `revert_exit=0` for `assignment_checks.py`, `preview_stock_task_assignment_match.py`, and `stock_report.py`. |

## Execution evidence

```text
cd app && BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest \
  tests/integration/services/commands/stock_report/test_create_stock_task_assignments.py
42 passed in 7.78s

cd app && BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest \
  tests/integration/services/commands/stock_report/test_delete_stock_task_assignments.py
12 passed in 2.87s

cd app && BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest \
  tests/unit/domain/stock_report/test_stock_report_assignment_checks.py \
  tests/integration/services/queries/stock_report/test_preview_stock_task_assignment_match.py \
  tests/unit/routers/api_v1/test_stock_report_router.py
49 passed in 4.03s
```

The pre-extraction command at `798fc69` was compared against
`evaluate_assignment_checks`: both retain the exact MC-13 sequence
`stock_report_item_not_found`, `task_not_found`, `item_not_found`,
`item_not_task_primary`, `already_processed_by_scanner`,
`task_failed_or_cancelled`, `item_already_assigned`, `item_has_no_category`,
`category_mismatch`. In particular the deliberately non-intuitive last-three ordering is intact.

## Criterion dispositions (20 active rows)

All entries below are backed by the 49-pass targeted command above, plus the named mutation
evidence where the row has an active mutation cell.

| Row | Disposition | Command/output |
|---|---|---|
| C1(a) | PASS | targeted command: `49 passed`; the three create/preview refusal comparisons passed. |
| C1(b) | FAIL (verification) | Its early-return mutation reddened correctly, but the criterion requires transient production instances and the test supplies `SimpleNamespace` stand-ins. |
| C2(a) | PASS, authority controls | targeted command: `49 passed`; response has the seven §14G table fields. See P8A-R1-02 for the plan's erroneous count of eight. |
| C2(b) | PASS | planted insert mutant red: `test_preview_does_not_write_or_change_counters`, `assert ... is None` received a `StockTaskAssignment`; reverted. |
| C3(a) | PASS | `ADVISORY_CHECKS` removal red: advisory became `False`, and `can_proceed` became `False`; reverted. |
| C3(b) | PASS | targeted command: `49 passed`; advisory refusal reason is `item_already_assigned`. |
| C3(c) | PASS | targeted command: `49 passed`; both unresolved identifier cases are normal results with supplied matcher values. |
| C3(d) | PASS | targeted command: `49 passed`; quantity 4 matches and 7 yields `value_not_accepted`. |
| C3(e) | PASS | targeted command: `49 passed`; unresolved item checks report `not_evaluated`, no refusal, `can_proceed true`. |
| C3(f) | PASS | targeted command: `49 passed`; conflicting request values leave stored values decisive and `values_source == "stored"`. |
| C4(a) | PASS | targeted command: `49 passed`; absent, deleted, and foreign row paths raise `NotFound`. |
| C4(b) | PASS | targeted command: `49 passed`; omitted quantity and both identifiers raise `ValidationError`. |
| C4(c) | PASS | targeted command: `49 passed`; deleted and foreign candidate items do not resolve. |
| C5(a) | PASS | construction-set removal red: `test_preview_with_no_task_reports_construction_results`, `fail != pass_by_construction`; reverted. |
| C5(b) | PASS | targeted command: `49 passed`; supplied task reports all three real failures in precedence order. |
| C6(a) | PASS | ADMIN removal red: allowed-role test expected 200, received 403; reverted. |
| C6(b) | PASS | MANAGER removal red: allowed-role manager expected 200, received 403; reverted. |
| C6(c) | PASS | WORKER removal red: allowed-role worker expected 200, received 403; reverted. |
| C6(d) | PASS | SELLER addition red: seller test expected 403, received 200; reverted. |
| C6(e) | PASS | removing `extra="forbid"` red: unknown-field test expected 422, received 200; reverted. |

`C6(f)` is withdrawn in plan §7 and therefore is not one of the 20 active rows. It was not
counted as a named mutation or a criterion disposition.

## Mutation table

| Row/site | Whole-file command | Observed red | Reverted |
|---|---|---|---|
| C1(b), `evaluate_assignment_checks` early return | `pytest tests/unit/domain/stock_report/test_stock_report_assignment_checks.py` | `test_assignment_checks_returns_all_results_in_precedence_order`: expected nine check names, got only the prefix through `item_not_found`. | yes (`revert_exit=0`) |
| C2(b), preview service planted assignment insert/flush | `pytest tests/integration/services/queries/stock_report/test_preview_stock_task_assignment_match.py --show-capture=no --tb=short -q` | `test_preview_does_not_write_or_change_counters`: expected no assignment, found `StockTaskAssignment`. | yes |
| C3(a), remove `ADVISORY_CHECKS` entry | same preview file | `test_preview_reports_advisory_active_assignment_without_blocking`: `advisory False != True`; `test_preview_refusal_reason_includes_advisory_failure`: `can_proceed False != True`. | yes |
| C5(a), remove `item_not_task_primary` from construction set | same preview file | `test_preview_with_no_task_reports_construction_results`: `fail != pass_by_construction`. | yes |
| C6(a), remove ADMIN | `pytest tests/unit/routers/api_v1/test_stock_report_router.py --show-capture=no -q` | allowed ADMIN route: `403 != 200`. | yes |
| C6(b), remove MANAGER | same router file | allowed MANAGER route: `403 != 200`. | yes |
| C6(c), remove WORKER | same router file | allowed WORKER route: `403 != 200`. | yes |
| C6(d), add SELLER | same router file | seller rejection: `200 != 403`. | yes |
| C6(e), remove preview body `extra="forbid"` | same router file | unknown-field rejection: `200 != 422`. | yes |

## Findings

### P8A-R1-01 — blocking — route: verification

The mandatory L4 command required by this prompt cannot produce its required 21-failure baseline
when also run in the mandatory `BEYO_TEST_SLOT=a8`. Actual output was:

```text
23 failed, 3604 passed, 1 skipped, 2 warnings in 70.44s
```

Current-minus-published baseline is exactly:

```text
tests/integration/infrastructure/test_database_isolation.py::test_worker_name_resolution[None-None-beyo_test_main_main]
tests/integration/infrastructure/test_database_isolation.py::test_worker_name_resolution_uses_xdist_worker
```

Published-baseline-minus-current is empty. Both extra tests assert names beginning
`beyo_test_main_*`; with the mandatory `a8` slot the production resolver correctly returns
`beyo_test_a8_*`. Correct the isolation tests or define a slot-aware L4 comparator, then repeat
the one L4 on a tree whose unrelated concurrent changes are not present.

### P8A-R1-02 — should-fix — route: plan

Plan 8A C2(a) says the response has "exactly eight" keys, but authority §14G's response table
lists seven: `can_proceed`, `override_required`, `refusal_reason`, `property_failures`,
`matched_item_client_id`, `values_source`, and `checks`. The implementation and test correctly
return seven. Amend the plan wording/count; do not add a spurious eighth API field.

### P8A-R1-03 — should-fix — route: plan

Plan §7's derived count claims 19 active criterion rows and 10 active named mutations, while the
review prompt correctly asks for 20 active rows. Counting C6(a)–C6(d) separately yields 20. The
tenth named mutation is the withdrawn C6(f), whose table cell has no active mutation site.
Restate the count as 20 rows and nine active named mutations (plus the class-2 set if retained),
or explicitly restore C6(f); this prevents a future verification ledger from asserting the wrong
closed set.

### P8A-R1-04 — should-fix — route: verification

C1(b)'s exact fixture requires transient production instances (and charter rule 3 requires the
same object type production holds), but
`test_stock_report_assignment_checks.py` constructs `row`, `task`, and `item` with
`SimpleNamespace`. The command below is the direct evidence:

```text
from types import SimpleNamespace
row=SimpleNamespace(is_deleted=False, item_category_id="category-1")
task=SimpleNamespace(is_deleted=False, state=TaskStateEnum.FAILED)
item=SimpleNamespace(is_deleted=False, item_category_id="category-2")
```

Replace those stand-ins with transient `StockReportItem`, `Task`, and `Item` instances while
retaining the same one-row result/order assertions and the existing early-return mutant. The
current integration tests exercise real entities, but they do not repair this criterion's specified
pure-function proof boundary.

## Architecture Graph review

Graph status: valid, 230 nodes, 358 edges, no diagnostics, revision
`6df549d436ade66e8a2fb254455953f4b9161342b73b14054bd0d822f82155ed`, review permission.
I re-read the three cited symbols in source. The route is an independently named endpoint with
the stated roles and path injection; the evaluator is pure and returns the ordered results; the
preview invokes that evaluator. All three pending items are supported, have no reported
contradiction, and are **recommended for promotion**. No review preview, approval, or mutation was
attempted because that requires explicit human authorization.

## What I did not check

- I did not execute the plan's 16 class-2 mutations; this review prompt only required every named
  mutation, and all nine active named sites were executed.
- I did not run withdrawn C6(f) as a criterion mutation.
- I did not make, promote, reject, edit, or otherwise mutate Architecture Graph records.
- The L4 pass count cannot be reconciled to Phase 8A alone because the workspace was concurrently
  dirty and later batch-C2 tests were present; the failure-set discrepancy is nevertheless fully
  identified above.

## Mutation-probe declaration and write perimeter

Probe-touched files were `app/beyo_manager/domain/stock_report/assignment_checks.py`,
`app/beyo_manager/services/queries/stock_report/preview_stock_task_assignment_match.py`, and
`app/beyo_manager/routers/api_v1/stock_report.py`. Every probe was applied and reverted; each
file's `git diff --quiet` exit was 0. Test transactions rolled back their state. This review writes
only this handoff file; no production, plan, master-plan, checkpoint, or Architecture Graph data
was changed.
