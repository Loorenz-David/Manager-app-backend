---
plan: batch A — plans/plan_1.md, plans/plan_2.md, plans/plan_3.md (master_plan.md §3A)
role: reviewer (Claude Opus, skill `plan-reviewer`) — re-review 2 after fix round 2
round: batch_A-rereview-2
date: 2026-09-20
tree: f2157bd
scope: narrow — three findings and a regression check. Nothing else.
---

# Batch A re-review 2 — the last three findings

Batch A stands at **168 PASS / 2 FAIL / 0 NOT_VERIFIED** of 170 rows after re-review 1
(`SR/handoffs/reviewer/2026-09-20_batch_A_rereview_1_handoff.md`, tree `983d774`). Fix round 2
addressed its three findings. **This re-review decides whether batch A is APPROVED.**

This one is genuinely narrow: the fix perimeter is **four files**, the foundations did not move, and
168 rows are already armed and measured. Do not re-open them. If you find yourself re-verdicting a
row outside the list below, stop — that is scope creep, and the charter's over-evidence rule names
it.

Paths are relative to the repo root `backend/`. `SR/` =
`docs/architecture/under_construction/implementation/stock_report/`. Run tests from `app/`.

## What changed

`git diff 983d774..f2157bd -- app/` is four files, +261/−31:

| File | Change |
|---|---|
| `bm/services/queries/stock_report/consistency.py` | `expected_task_flag` regains its `workspace_id` parameter and predicate; its caller threads it |
| `bm/services/commands/stock_report/_task_flag.py` | `recompute_task_stock_flag(session, workspace_id, task_id)` threads it through |
| `tests/integration/services/queries/stock_report/test_consistency_check.py` | C1(k) rebuilt; the duplicated schema test deleted |
| `tests/integration/services/commands/stock_report/test_repair_stock_report.py` | C3(d)'s record assertions |

Implementer handoff: `SR/handoffs/implementer/2026-09-20_batch_A_fix_2_handoff.md` (state
`IMPLEMENTED`, ledger `declared = executed = 7`).

## What I verified (consume by citation, do not re-run)

- **L4 on this tree**, my own run: **21 failed / 3264 passed / 2 skipped in 69.19s**, failure IDs
  identical to the 21-ID baseline **in both directions**. The −1 against the previous 3265 is
  exactly the deleted duplicate test, and nothing else moved. **Do not run L4.**
- **Perimeter:** the four files above, plus three plan Review-log entries and the handoff. No
  escape, no master-plan edit.
- The production diff matches the owner ruling literally: `StockTaskAssignment.workspace_id ==
  workspace_id` restored in the `WHERE`, threaded through `compute_stock_report_divergences` and
  `recompute_task_stock_flag`.
- `test_consistency_matches_migrated_worker_schema` is gone from the plan 3 file.

## Your three questions

**1. F-R1 (was blocking) — is the workspace guard now real?**

The production half is easy to confirm by reading. The half that matters is the coverage: at
re-review 1 you measured that **four of the five workspace filters survived plan 3 C1(k)'s own named
mutation**. The fix claims all five now redden. **Re-run that measurement yourself** — apply the
row's named mutation to each of the five filters in turn and record each result independently:

| Filter | Kinds it protects | At re-review 1 |
|---|---|---|
| `stock_report_items` select | counter ×3, signature, nullness, order_density | RED |
| `stock_report_history_records` select | goal_total | GREEN |
| `tasks` select | task_flag | GREEN |
| `_recompute_row_counters_for_workspace` | counter ×3 | GREEN |
| `_recompute_goal_totals_for_workspace` | goal_total | GREEN |

Add the sixth site the fix round introduced: removing the predicate from `expected_task_flag`
itself. That one is the production defect your card 1 named, so it must redden.

Then judge the fixture on the plan's terms. C1(k) says clean F0 plus **every** C1(a)–(j) drift
planted in the **foreign** workspace → the check for W returns `[]`. The rebuilt test plants
cross-workspace assignment rows (foreign `workspace_id`, own `stock_report_item_id` / `task_id`)
to make the counter, goal and task filters observable. Decide whether that is a faithful reading of
the row or a fixture shaped to the implementation — in particular, whether the own-workspace
assertion is still exactly `[]` for the right reason.

**2. F-R2 — is C3(d)'s record armed?** Plan 3 C3(d) wants the full record for a flag wrongly set
true: `{target_kind: task, target_client_id: T, field: is_stock_assignment, stored_value: "true",
recomputed_value: "false", trigger: manual}` plus a clean post-repair check. Confirm the assertion,
then run the mutation you used to expose it (hard-code `recomputed_value` to `"true"`) and confirm
it now reddens. Check that C3(e), the opposite direction, is undamaged.

**3. F-R3 — was the right copy deleted?** Plan 1 C2(a) must still be discharged by
`test_stock_report_migration_matches_runtime_metadata` in `test_stock_report_schema.py`, and
nothing else should have gone with it.

## Regression check (the only widening)

The `expected_task_flag` signature change reaches plan 3 **C1(d)** and **C1(e)** (the task_flag
rows) and `recompute_task_stock_flag`'s callers. Confirm those two rows are still armed — the
task-flag-kind mutation reddened them at re-review 1. C1(k)'s rebuilt fixture is large; confirm it
did not swallow a kind that another row relies on.

Beyond that, my L4 is the regression evidence for the other 166 rows. Do not re-verdict them.

## Verdict

State it plainly: **APPROVED** or **CHANGES_REQUESTED** with the row totals of 170.

If you approve, say so without hedging — the batch does not need a fourth round to feel safe, and
168 rows were already measured armed under 54 mutations. If something still fails, remember the
**owner stop**: work halts and the owner rules per finding before any third fix round, so be
explicit about whether a finding genuinely blocks or belongs in the backlog with the nine notes
already routed forward.

Notes N-R1…N-R9 and review 1's N-1, N-2, N-3, N-6, N-8, N-9 are **out of scope and stay open** —
they are routed to later phases. Lessons L-10…L-15 are mine to fold. Do not restate any of them.

## Do not touch

The intention; the Scanner repository; the plan files except one appended Review-log entry each; the
master plan (§6.5 is already amended with your `lock_stock_report_history_records` signature and the
owner's `expected_task_flag` ruling); other roles' prompts or handoffs;
`docs/archgraph-anchor-observations.md`. Do not modify source or tests. Revert every probe and prove
it byte-identical. No commits, no graph write.

## Handoff

`SR/handoffs/reviewer/2026-09-20_batch_A_rereview_2_handoff.md`. Frontmatter: `plan: batch A (1, 2,
3)`, `role: review`, `round: batch_A-rereview-2`, `state: APPROVED | CHANGES_REQUESTED`, `date`,
`actor`, `tree: f2157bd`. Structure:

1. **Verdict** and the row totals (of 170).
2. **The six filter mutations**, one line each with the result.
3. **F-R1, F-R2, F-R3** — CONFIRMED / PARTIAL / NOT_DONE, with the evidence.
4. **Regression check** on C1(d), C1(e) and the threaded callers.
5. **Findings**, if any, blocking first.
6. **What you ran.**
7. **Mutation-probe declaration.**
8. `⚠ OWNER DECISIONS REQUIRED (n)`, or `(0)`.

Your final message's first line is the `HANDOFF: … | STATE: … | OWNER_CARDS: n` line, followed by
the owner layer.
