---
plan: 8A
role: fix
round: 2
state: CHECKPOINT_NOT_APPROVED
date: 2026-09-21
actor: Claude (Sonnet)
---

# Phase 8A fix 2 — the supplied `item_category_id` now takes effect

Closes the round-2 defect: the request's `item_category_id` was inert on both branches of
`preview_stock_task_assignment_match`. Full read order followed: doctrine
(`implementation-executor.md` + `pipeline-charter.md`), gate check (intention §14G RATIFIED;
master plan tracker shows 8A REOPENED, round 2 in flight), the round-2 prompt, plan 8A §7's round-2
note, C3(e) corrected, C3(g), and intention §14G in full.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. See "Judgment call" below for the one point the plan/prompt left open —
it had a single forced answer, not a split worth a card.

## The fix

In `app/beyo_manager/services/queries/stock_report/preview_stock_task_assignment_match.py`:

1. `evaluate_assignment_checks`'s `item=` argument is now `candidate` (was `matched_item`).
2. The no-item `assumed` NOT_EVALUATED set is now exactly four: `item_not_found`,
   `item_not_task_primary`, `already_processed_by_scanner`, `item_already_assigned`.
   `item_has_no_category` and `category_mismatch` were removed from it.
3. `item_id` stays `None` when nothing resolved (unchanged).
4. The stored-item branch is unaffected in effect: `candidate is matched_item` whenever an item
   resolves, so `item=candidate` on that path is exactly `item=matched_item` as before — C3(f)'s
   "stored wins" guarantee is untouched.

**Judgment call, not spelled out in the round-2 prompt, forced by C3(g) case (iii):**
`item_category_id` was `str` (required, non-nullable) in both `PreviewStockTaskAssignmentRequest`
(the service model) and the router's `_PreviewStockTaskAssignmentBody`. C3(g) case (iii) sends
`item_category_id: null` and expects the request to parse, with `item_has_no_category` then
evaluated as `fail`. Verified by hand that this is impossible under a required `str` field —
`model_validate` raises a `string_type` error before any check runs. Widened both models to
`str | None = None`. Also updated the router's copy, not just the service's: C3(g) is proven at
the service boundary (per plan §7's boundary declarations) so the service-only change would have
passed the row, but a real HTTP client would still be unable to express "no category yet" through
the router's stricter model — the same defect class (a field that reaches no decision) one layer
up. `Item.item_category_id` is already nullable at the model layer
(`app/beyo_manager/models/tables/items/item.py:31`), so a transient candidate with no category is
not a new domain concept, just a previously-unreachable one. This was not a two-way split needing
an owner card: C3(g)(iii)'s existence and the domain column's nullability together force the one
answer.

## Task 0 — coverage for this round's touched rows

No tester role this phase (master plan §3B; plan 8A's own header: "no tester session"), so this
map is mine, scoped to the rows this round could move (all other 8A rows are frozen per the "do
not revisit" instruction and were spot-checked only where the fix's mechanics could plausibly
reach them — C3(f), C5(a), phase 8's `create` suite).

| Row | Test id | Assertion shape matches row? |
|---|---|---|
| C3(e) (corrected) | `test_preview_unresolved_item_marks_item_checks_not_evaluated` | Yes — asserts the corrected four as `not_evaluated`, and now also asserts `item_has_no_category`/`category_mismatch` read `pass` for the fixture's matching category/criteria (the row's "must be evaluated" clause, previously unassert­ed) |
| C3(g)(i) | `test_preview_supplied_category_takes_effect_with_no_item[own_category]` | Yes — `category_mismatch`/`item_has_no_category` both `pass`, `can_proceed True`, `matched_item_client_id None`, `values_source "supplied"` |
| C3(g)(ii) | `test_preview_supplied_category_takes_effect_with_no_item[different_category]` | Yes — `category_mismatch fail`, `can_proceed False`, `refusal_reason == "category_mismatch"` |
| C3(g)(iii) | `test_preview_supplied_category_takes_effect_with_no_item[null_category]` | Yes — `item_has_no_category fail`, `refusal_reason == "item_has_no_category"` |
| C3(f) (not re-authored, re-verified) | `test_preview_uses_stored_values_when_identifier_resolves` | Yes, unedited and still green — confirms the stored branch is unaffected |
| C5(a) (not re-authored, re-verified) | `test_preview_with_no_task_reports_construction_results` | Yes, unedited and still green — confirms the null-`task_id` overwrite still wins for the two overlapping checks |
| gate obligation (§3) | `test_create_stock_task_assignments.py` (42 tests) | Yes, unedited and still green — `create` completely unaffected |

Reverse direction: every test added or edited this round is in the table above — none is an orphan.

## Verification

### Targeted: the preview test file (includes the mutation run below)

```text
cd app && BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest \
  tests/integration/services/queries/stock_report/test_preview_stock_task_assignment_match.py
```

Result before the mutation: `25 passed` (22 pre-existing + 3 new C3(g) cases).

### C3(g) named mutation, run and reverted

Mutation: `preview_stock_task_assignment_match.py`, `evaluate_assignment_checks` call site — revert
`item=candidate` back to `item=matched_item` (the pre-fix line).

Command: same as above (whole file, never `-k`).

Observed red — 2 of 3 new cases:

```text
FAILED …test_preview_supplied_category_takes_effect_with_no_item[different_category]
  test_preview_stock_task_assignment_match.py:372: AssertionError: assert 'pass' == 'fail'
    (category_mismatch expected fail, got pass)
FAILED …test_preview_supplied_category_takes_effect_with_no_item[null_category]
  test_preview_stock_task_assignment_match.py:373: AssertionError: assert 'pass' == 'fail'
    (item_has_no_category expected fail, got pass)
2 failed, 23 passed
```

`[own_category]` stayed green, as it must — its expected `pass` is invariant to this mutation
(both `item=candidate` and `item=matched_item=None` route it to the "not_evaluated → skip" path
differently, but the fixture's own predicate never needs the category check to fail either way).
This is not a weak row: cases (ii) and (iii) are the discriminating ones and both bit.

Reverted. Proof:

```text
git diff -- app/beyo_manager/services/queries/stock_report/preview_stock_task_assignment_match.py
```

shows only the three intended fix hunks (the `item_category_id` type widening, the narrowed
`assumed` tuple, and `item=candidate`) — no mutation residue. Re-ran the file after revert:
`25 passed`.

Mutation-probe file, applied and reverted: `preview_stock_task_assignment_match.py` (same file as
the production perimeter — no separate file was touched for the probe).

### Domain-scoped: assignment-checks unit test and router tests

```text
cd app && BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest \
  tests/unit/domain/stock_report/test_stock_report_assignment_checks.py \
  tests/unit/routers/api_v1/test_stock_report_router.py
```

Result: `27 passed`. Neither file was edited this round; run to confirm the router's widened
`item_category_id` type did not disturb its existing fixed-body tests.

### Gate obligation: phase 8's `create` suite unaffected

```text
cd app && BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest \
  tests/integration/services/commands/stock_report/test_create_stock_task_assignments.py
```

Result: `42 passed` — identical to before this round. `create_stock_task_assignments.py` was not
touched.

### Lint

```text
cd app && ruff check \
  beyo_manager/services/queries/stock_report/preview_stock_task_assignment_match.py \
  beyo_manager/routers/api_v1/stock_report.py \
  tests/integration/services/queries/stock_report/test_preview_stock_task_assignment_match.py
```

Result: `All checks passed!`

### One authoritative L4

Command: `cd app && BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest -m 'not e2e'`

**First run** (tree: commit `74e3830`, dirty with this round's 3 files plus the concurrent batch-C2
round's 7 files mid-edit): `24 failed, 3667 passed, 1 skipped`. The 24th failure beyond the 23-gate
was `tests/integration/services/commands/stock_report/test_task_state_sync.py::test_c1m_sync_selects_the_active_assignment_over_a_terminal_one`
— a file this round does not own or touch. Re-ran that single test in isolation immediately after:
`1 passed`. `git diff --stat` on that file showed +94 uncommitted lines from the concurrent
batch-C2 round at that moment, confirming the failure was a transient artifact of reading that
file mid-edit in the shared tree, not a regression from this round's changes (which never import
or touch anything in `task_state_sync.py`, `sync_task_stock_assignments.py`, `_move_assignment.py`,
or the scanner-write-site files).

**Second run**, same tree state otherwise (still dirty elsewhere, per the environment's stated
concurrency — batch C2 continues on slot `c2` in different files): `23 failed, 3668 passed,
1 skipped`. Failure-ID comparison against the published 21-ID set plus the two known slot IDs
(`test_worker_name_resolution[None-None-beyo_test_main_main]`,
`test_worker_name_resolution_uses_xdist_worker`) — both directions empty (`comm` diff run over
both ID lists produced no lines either way). **Citing this second run as the round's one
authoritative L4 stamp**; the first is recorded per the flaky-capture rule (capture the ID set
before repeating an anomalous run) rather than silently dropped, and is not this round's defect.

Pass arithmetic: this round adds exactly 3 new test ids (C3(g)'s three parametrized cases). The
last recorded baseline was `3661` (fix round 1's stamp at `4581209`), so this round's own
contribution is `3661 + 3 = 3664`. The observed `3668` is `4` higher, all attributable to the
concurrent batch-C2 round's own in-flight, uncommitted test additions in files this round does not
own (`git diff --stat` confirms uncommitted additions: `test_process_items_processed.py` +93,
`test_task_state_sync.py` +94, `test_task_state_write_sites_are_registered.py` +28 lines) — not
this round's arithmetic to claim or explain further.

Tree identity for this stamp: commit `74e3830`, `git status --porcelain` non-empty (dirty — by
design, concurrent batch C2 in flight on other files), digest of the full `git diff` at stamp time:
`a4319f2d6a71bb6593c16589fd261c32785335f3e7bff4c55b1c8beaacb1e38b` (sha256). This digest mixes this
round's diff with batch C2's in-flight diff and is not reusable once either round's files change
further; it is recorded only to make this specific run's tree identifiable, per the charter's
dirty-tree rule.

## Architecture graph

Checked both nodes this phase owns: `endpoint-stock-assignment-match-preview` and
`domain-assignment-acceptability-evaluator` (both `human_confirmed`, `reviewed`). Neither's
description nor its recorded evidence makes any claim this fix contradicts — both are written at
architectural granularity (a shared pure decision boundary; a read-only endpoint reporting every
check), not at the level of the specific call-site wiring the defect was in. No stale claim found.
No delta applied — same conclusion, and same reasoning, as fix round 1 for a comparably-sized
call-site correction inside an already-recorded boundary.

## Perimeter (cycle-scoped — this round only)

Production:
- `app/beyo_manager/services/queries/stock_report/preview_stock_task_assignment_match.py`
- `app/beyo_manager/routers/api_v1/stock_report.py`

Test:
- `app/tests/integration/services/queries/stock_report/test_preview_stock_task_assignment_match.py`

Docs:
- `docs/architecture/under_construction/implementation/stock_report/plans/plan_8A.md`
  (Review log entry only — no criterion cell edited)
- this handoff

Mutation-probe file, applied and reverted (same file as the production perimeter, confirmed by
`git diff` showing no residue): `preview_stock_task_assignment_match.py`.

**Explicitly not touched** (batch-C2's concurrent perimeter on slot `c2`, left exactly as found,
confirmed present in `git status --porcelain` before and after this round with no edits from this
session): `app/beyo_manager/services/commands/stock_report/_move_assignment.py`,
`app/beyo_manager/services/commands/stock_report/sync_task_stock_assignments.py`,
`app/tests/integration/services/commands/stock_report/test_process_items_processed.py`,
`app/tests/integration/services/commands/stock_report/test_task_state_sync.py`,
`app/tests/unit/services/commands/stock_report/_task_state_write_scanner.py`,
`app/tests/unit/services/commands/stock_report/task_state_write_site_registry.py`,
`app/tests/unit/services/commands/stock_report/test_task_state_write_sites_are_registered.py`.
`master_plan.md`, the intention, and every plan_8A.md criterion cell were left untouched per the
round-2 prompt's explicit instruction.

Checkpoint subject: `CHECKPOINT (not approved): phase 8A round 2`.
