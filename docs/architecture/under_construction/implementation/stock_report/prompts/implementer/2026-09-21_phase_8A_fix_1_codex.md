---
phase: 8A
role: fix
round: 1
state: PROMPT_READY
date: 2026-09-21
actor: orchestrator
agent: Codex (terra)
---

# Phase 8A — fix round 1. **One finding. Nothing else.**

You are a **Codex** session. Skills are not auto-loaded, so **read these by absolute path first**
and follow them as session doctrine:

1. `/Users/davidloorenz/agent-skills/implementation-executor.md`
2. `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)

Plan: `SR/plans/plan_8A.md`. Authority: `SR/planning/intention.md` **§14G** and **MC-21**.
Review being answered: `SR/handoffs/reviewer/2026-09-21_phase_8A_review_1_handoff.md`.

## Your scope is one finding: P8A-R1-04

The review raised four. **Three are already closed and are not yours** — read this so you do not
spend a minute on them:

| Finding | Route | Status |
|---|---|---|
| **P8A-R1-01** — L4 shows 23 failures, not 21 | verification | **DISCHARGED by orchestrator ruling.** Not a defect. See the box below. |
| **P8A-R1-02** — C2(a) says "eight" response keys | plan | **Already fixed** by the orchestrator in `plan_8A.md`. It is seven. |
| **P8A-R1-03** — §7 says 19 rows / 10 mutations | plan | **Already fixed.** It is 20 rows / 9 active named mutations. |
| **P8A-R1-04** — C1(b) uses `SimpleNamespace` | verification | **YOURS. The whole job.** |

> **⚠ The 23-failure L4 is a PASS. Do not try to make it 21.** Two tests in
> `tests/integration/infrastructure/test_database_isolation.py` assert that the *ambient* test
> slot is `main`, so they go red under **any** named slot — including your mandatory `a8`. This
> was the orchestrator's error (mandating slots without checking that the isolation suite asserts
> its own default), it is confirmed on three independent runs, and master plan §10 now rules that
> **the gate condition under a non-`main` slot is 23 = the published 21-ID set plus exactly**
> `test_database_isolation.py::test_worker_name_resolution_uses_xdist_worker` **and**
> `::test_worker_name_resolution[None-None-beyo_test_main_main]`.
>
> **Do not "fix" those two tests.** They belong to the APPROVED `test_isolation_and_xdist`
> project; changing them is an owner decision that has not been made. A 24th ID, or either of
> those two missing while the slot is set, *is* a real finding — report it, do not chase it.

**`plan_8A.md` has changed since your checkpoint** (the two count corrections above, plus a §7
correction note). Re-read it; do not restore the old numbers.

## The fix

`app/tests/unit/domain/stock_report/test_stock_report_assignment_checks.py` builds the
evaluator's three entities as `SimpleNamespace` stand-ins:

```python
row=SimpleNamespace(is_deleted=False, item_category_id="category-1"),
task=SimpleNamespace(is_deleted=False, state=TaskStateEnum.FAILED),
item=SimpleNamespace(is_deleted=False, item_category_id="category-2"),
```

Plan 8A **C1(b)** specifies *"Unit, transient production instances (charter rule 3)"*, and charter
rule 3 requires the test to hold the same object type production holds. A duck-typed stand-in
proves the evaluator works on *something shaped like* the entities, not on the entities.

**Replace them with transient (un-persisted, never added to a session) instances of the real
models:**

- `StockReportItem` — `app/beyo_manager/models/tables/stock_report/stock_report_item.py`
- `Task` — `app/beyo_manager/models/tables/tasks/task.py`
- `Item` — `app/beyo_manager/models/tables/items/item.py`

Constructing them needs no database: set only the attributes the evaluator actually reads
(`is_deleted`, `item_category_id`, `state`), and let the rest default. **Keep the row's existing
result/order assertions exactly as they are** — the nine check names in MC-13 precedence order,
and the same expected results. This is a fixture change, not a criterion change.

If a model cannot be constructed transiently without touching a database — a `__init__` that
requires a session, a server-side default the evaluator reads — **stop and report it as a card**
rather than inventing a hybrid. That is a real finding about the criterion, and the honest
outcome.

## Prove the row still bites — this is the part that is easy to get wrong

Swapping a fixture can silently make a mutation inert, which would leave C1(b) green, "fixed",
and worthless. So:

1. Run the whole file (never `-k`) and show it green.
2. **Re-run C1(b)'s named mutation** — the early return in `evaluate_assignment_checks`
   (`app/beyo_manager/domain/stock_report/assignment_checks.py`) — against the **rebuilt** test.
   It must still redden on the *same assertion* (the review recorded: *"expected nine check
   names, got only the prefix through `item_not_found`"*).
3. Revert it and prove the revert: `git diff --quiet <file>`, exit 0.

A fix round that reports the test green without re-reddening its mutation has not discharged this
finding.

## Everything else is out of scope

**Do not** touch production code — this finding is entirely in a test. **Do not** add tests for
the extraction half (plan 8A deliberately has none; adding them is over-specification and was
already a stated risk for this phase). **Do not** re-run the other eight named mutations — the
review executed all nine and reverted them; that evidence stands and re-running it is
over-verification.

> **⚠ A second workstream is live in this repository right now.** Batch C2's tester is working in
> `app/tests/integration/services/commands/stock_report/` (`test_process_items_processed.py`,
> `test_task_state_sync.py`, `test_two_writers_on_one_assignment.py`) and may commit while you
> run. Those files are **not yours**; leave them alone, do not revert them, and do not report
> their movement as a defect.
>
> **Set `BEYO_TEST_SLOT=a8` on every pytest command**, not just the L4 — `pytest.ini` carries
> `-n 6 --dist loadfile`, so even a single-file run claims six worker databases:
>
> ```
> cd app && BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest tests/unit/domain/stock_report/test_stock_report_assignment_checks.py
> cd app && BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest -m 'not e2e'
> ```
>
> **Commit with explicit paths, never `git add -A`** — `git add -A` would sweep the other
> workstream's in-flight edits into your commit.

## Environment

Baseline on your slot: **23 failed / 1 skipped**, the 21 published IDs plus the two named above.
The pass count has moved since your checkpoint because batch C2 landed 46 tests; reconcile
against what you observe and **state the arithmetic you used** rather than against a remembered
number. The invariant is the failure-ID set, not the pass count — diff it both directions against
`docs/architecture/archives/test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md` §3
and print both.

**Budget:** the one test file's L1, the C1(b) mutation re-run, and **exactly one L4**.

## Your handoff

`SR/handoffs/implementer/2026-09-21_phase_8A_fix_1_handoff.md`:

1. The fixture diff, and confirmation the row's assertions are unchanged.
2. **The C1(b) mutation re-run**: command, the test id and assertion that reddened, and the
   `git diff --quiet` proving the revert.
3. The one L4 with both ID diffs and your pass-count arithmetic.
4. Anything you found wrong, and owner questions under `⚠ OWNER DECISIONS REQUIRED (n)`.

Checkpoint `CHECKPOINT (not approved): phase 8A fix 1`, explicit paths. **Never push.**
Do not edit `master_plan.md`, the intention, or any criterion cell — plan Review log entries only.

## Stop conditions

C1(b) rebuilt on transient production instances · its file green · its named mutation observed
red on the rebuilt test and reverted · one L4 reconciled at 23 · lint clean · Review log written ·
handoff complete · checkpoint committed.

**Not reasons to continue:** the other three findings; the two isolation-test failures; a mutation
you thought of; tidying. If you believe something else is broken, **report it — do not fix it.**
